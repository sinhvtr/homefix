"""Thông báo (SPEC 11): bản ghi trong ứng dụng, gửi sau commit, kênh Console/WebPush/Telegram, PWA."""

import json
from types import SimpleNamespace

import pytest
from django.db import transaction

from apps.tai_khoan.models import VaiTro
from apps.thong_bao import adapters
from apps.thong_bao.adapters import SmsKenh, WebPushKenh, ZaloZnsKenh, cac_kenh_theo_thu_tu
from apps.thong_bao.dich_vu import DichVuThongBao
from apps.thong_bao.models import DangKyPush, ThongBao
from apps.thong_bao.tac_vu import gui_qua_kenh
from apps.thong_bao.telegram import doc_token, tao_token, xu_ly_cap_nhat
from tests.conftest import NguoiDungFactory, ThoFactory

pytestmark = pytest.mark.django_db


def test_luon_tao_ban_ghi_va_chi_gui_kenh_ngoai_sau_commit(
    settings, monkeypatch, django_capture_on_commit_callbacks
):
    nguoi = NguoiDungFactory()
    da_gui = []
    monkeypatch.setattr("apps.thong_bao.tac_vu.gui_qua_kenh", lambda tb_id: da_gui.append(tb_id))
    with django_capture_on_commit_callbacks(execute=False) as cho_commit:
        with transaction.atomic():
            tb = DichVuThongBao.gui(nguoi, "Việc mới", "Nội dung", "/tho/")
            assert ThongBao.objects.filter(pk=tb.pk).exists()
        assert da_gui == []  # chưa commit → chưa gọi mạng
    for ham in cho_commit:
        ham()
    assert da_gui == [tb.pk]


def test_xep_hang_django_q_khi_khong_dong_bo(settings, monkeypatch, django_capture_on_commit_callbacks):
    settings.THONG_BAO_DONG_BO = False
    goi = []
    monkeypatch.setattr("django_q.tasks.async_task", lambda *a, **k: goi.append(a))
    with django_capture_on_commit_callbacks(execute=True):
        tb = DichVuThongBao.gui(NguoiDungFactory(), "A")
    assert goi == [("apps.thong_bao.tac_vu.gui_qua_kenh", tb.pk)]


def test_console_kenh_khi_phat_trien(caplog):
    tb = DichVuThongBao.gui(NguoiDungFactory(), "Xin chào")
    with caplog.at_level("INFO"):
        assert gui_qua_kenh(tb.pk) == "CONSOLE"
    assert "Xin chào" in caplog.text


def test_thu_tu_kenh_theo_lua_chon_cua_tho(settings):
    settings.THONG_BAO_CHI_CONSOLE = False
    tho = ThoFactory(kenh_thong_bao="TELEGRAM")
    assert [k.ten for k in cac_kenh_theo_thu_tu(tho.nguoi_dung)] == ["TELEGRAM", "WEB_PUSH"]
    tho2 = ThoFactory(kenh_thong_bao="WEB_PUSH")
    assert [k.ten for k in cac_kenh_theo_thu_tu(tho2.nguoi_dung)] == ["WEB_PUSH", "TELEGRAM"]


def test_kenh_chinh_that_bai_thu_kenh_con_lai(settings, monkeypatch):
    settings.THONG_BAO_CHI_CONSOLE = False
    settings.TELEGRAM_BOT_TOKEN = "123:abc"
    tho = ThoFactory(kenh_thong_bao="WEB_PUSH", telegram_chat_id="999")
    tin = []
    monkeypatch.setattr(
        adapters.httpx,
        "post",
        lambda url, json, timeout: tin.append(json) or SimpleNamespace(status_code=200),
    )
    tb = DichVuThongBao.gui(tho.nguoi_dung, "Việc mới HF", "Chi tiết", "/tho/de-nghi/1/")
    assert gui_qua_kenh(tb.pk) == "TELEGRAM"  # chưa đăng ký push → Web Push thất bại → Telegram
    assert (
        tin[0]["chat_id"] == "999" and "Việc mới HF" in tin[0]["text"] and "/tho/de-nghi/1/" in tin[0]["text"]
    )


def test_web_push_gui_va_xoa_dang_ky_het_han(settings, monkeypatch):
    from pywebpush import WebPushException

    settings.VAPID_PRIVATE_KEY, settings.VAPID_EMAIL = "khoa", "a@b.vn"
    nguoi = NguoiDungFactory()
    con_song = DangKyPush.objects.create(
        nguoi_dung=nguoi, endpoint="https://push.vd/song", p256dh="p", auth="a"
    )
    DangKyPush.objects.create(nguoi_dung=nguoi, endpoint="https://push.vd/chet", p256dh="p", auth="a")
    da_gui = []

    def gia_webpush(subscription_info, data, **kw):
        if subscription_info["endpoint"].endswith("chet"):
            raise WebPushException("Gone", response=SimpleNamespace(status_code=410))
        da_gui.append(json.loads(data))

    monkeypatch.setattr("pywebpush.webpush", gia_webpush)
    assert WebPushKenh().gui(nguoi, "Tiêu đề", "Nội dung", "/tho/") is True
    assert da_gui == [{"tieu_de": "Tiêu đề", "noi_dung": "Nội dung", "duong_dan": "/tho/"}]
    assert list(DangKyPush.objects.values_list("pk", flat=True)) == [con_song.pk]


def test_kenh_co_phi_de_rong_cho_v2():
    for kenh in (ZaloZnsKenh(), SmsKenh()):
        with pytest.raises(NotImplementedError, match="v2 — có phí"):
            kenh.gui(None, "", "", "")


# ------------------------------------------------------------ Web Push đăng ký, danh sách thông báo


def test_dang_ky_push(client):
    nguoi = NguoiDungFactory()
    client.force_login(nguoi)
    du_lieu = {"endpoint": "https://fcm.googleapis.com/x", "keys": {"p256dh": "P", "auth": "A"}}
    assert client.post("/push/dang-ky/", du_lieu, content_type="application/json").status_code == 200
    assert client.post("/push/dang-ky/", du_lieu, content_type="application/json").status_code == 200
    assert DangKyPush.objects.get().nguoi_dung == nguoi
    assert (
        client.post("/push/dang-ky/", {"endpoint": "http://x"}, content_type="application/json").status_code
        == 400
    )


def test_danh_sach_thong_bao_chi_cua_minh_va_danh_dau_da_doc(client):
    toi, nguoi_khac = NguoiDungFactory(), NguoiDungFactory()
    DichVuThongBao.gui(toi, "Của tôi", duong_dan="/tho/")
    khac = DichVuThongBao.gui(nguoi_khac, "Của người khác")
    client.force_login(toi)
    noi_dung = client.get("/thong-bao/").content.decode()
    assert "Của tôi" in noi_dung and "Của người khác" not in noi_dung
    assert not ThongBao.objects.filter(nguoi_nhan=toi, da_doc=False).exists()
    assert client.post(f"/thong-bao/{khac.pk}/mo/").status_code == 404


def test_chuong_dem_thong_bao_chua_doc(client_vai_tro):
    c = client_vai_tro(VaiTro.TONG_DAI)
    DichVuThongBao.gui(c.nguoi_dung, "A")
    DichVuThongBao.gui(c.nguoi_dung, "B")
    assert "Thông báo (2 chưa đọc)" in c.get("/tong-dai/").content.decode()


# ------------------------------------------------------------ Telegram


def test_token_telegram_ky_va_het_han():
    token = tao_token(42, luc=1_000_000)
    assert len(token) <= 64 and all(ch.isalnum() or ch in "_-" for ch in token)
    assert doc_token(token, luc=1_000_000 + 3600) == 42
    assert doc_token(token, luc=1_000_000 + 25 * 3600) is None
    assert doc_token(token.replace(token[-1], "x" if token[-1] != "x" else "y"), luc=1_000_000) is None
    assert doc_token("rác") is None


def test_webhook_telegram_gan_chat_id(settings, client, monkeypatch):
    settings.TELEGRAM_WEBHOOK_SECRET = "bi-mat"
    monkeypatch.setattr("apps.thong_bao.telegram.gui_tin_telegram", lambda *a: True)
    tho = ThoFactory()
    cap_nhat = {"message": {"text": f"/start {tao_token(tho.nguoi_dung.pk)}", "chat": {"id": 777}}}
    assert client.post("/telegram/webhook/sai/", cap_nhat, content_type="application/json").status_code == 404
    assert (
        client.post("/telegram/webhook/bi-mat/", cap_nhat, content_type="application/json").status_code == 200
    )
    tho.refresh_from_db()
    assert tho.telegram_chat_id == "777"


def test_telegram_token_cua_nguoi_khong_phai_tho_bi_bo_qua(monkeypatch):
    monkeypatch.setattr("apps.thong_bao.telegram.gui_tin_telegram", lambda *a: True)
    nguoi = NguoiDungFactory()
    assert xu_ly_cap_nhat({"message": {"text": f"/start {tao_token(nguoi.pk)}", "chat": {"id": 1}}}) is False


def test_webhook_tat_khi_chua_cau_hinh(settings, client):
    settings.TELEGRAM_WEBHOOK_SECRET = ""
    assert client.post("/telegram/webhook/x/", {}, content_type="application/json").status_code == 404


# ------------------------------------------------------------ PWA, lịch tác vụ


def test_manifest_pwa(client):
    du_lieu = client.get("/manifest.webmanifest").json()
    assert (
        du_lieu["name"] == "HomeFix Thợ"
        and du_lieu["start_url"] == "/tho/"
        and du_lieu["display"] == "standalone"
    )
    from django.contrib.staticfiles import finders

    for bt in du_lieu["icons"]:
        assert finders.find(bt["src"].removeprefix("/static/")), bt["src"]


def test_service_worker_push_va_khong_cache_du_lieu(client):
    phan_hoi = client.get("/service-worker.js")
    noi_dung = phan_hoi.content.decode()
    assert phan_hoi["Content-Type"].startswith("application/javascript")
    assert phan_hoi["Service-Worker-Allowed"] == "/"
    assert 'addEventListener("push"' in noi_dung and 'addEventListener("notificationclick"' in noi_dung
    assert 'startsWith("/static/")' in noi_dung  # chỉ cache tệp tĩnh
    assert '["/static/css/tailwind.css"]' in noi_dung


def test_lich_tac_vu_qua_han_moi_phut():
    from django_q.models import Schedule

    lich = Schedule.objects.get(name="kiem_tra_qua_han_phan_cong")
    assert lich.func == "apps.tiep_nhan_dieu_phoi.tac_vu.kiem_tra_qua_han_phan_cong"
    assert (lich.schedule_type, lich.minutes) == (Schedule.MINUTES, 1)
    assert Schedule.objects.filter(name="don_dep_thong_bao", schedule_type=Schedule.WEEKLY).exists()


def test_don_dep_thong_bao_da_doc_qua_90_ngay():
    from datetime import timedelta

    from django.utils import timezone

    from apps.thong_bao.tac_vu import don_dep_thong_bao

    nguoi = NguoiDungFactory()
    cu = DichVuThongBao.gui(nguoi, "Cũ")
    chua_doc = DichVuThongBao.gui(nguoi, "Cũ chưa đọc")
    ThongBao.objects.filter(pk__in=[cu.pk, chua_doc.pk]).update(tao_luc=timezone.now() - timedelta(days=91))
    ThongBao.objects.filter(pk=cu.pk).update(da_doc=True)
    assert don_dep_thong_bao() == 1
    assert ThongBao.objects.filter(pk=chua_doc.pk).exists()

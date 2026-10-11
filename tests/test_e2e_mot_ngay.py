"""Nghiệm thu P6 — chạy thử toàn trình một ngày làm việc trên dữ liệu mẫu, chỉ bằng Django test client (qua màn hình,
đúng vai trò): tạo đơn → cử thợ → nhận → báo giá → hoàn thành → bảo hành → đối soát → báo cáo."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.bao_cao.dao import BaoCaoDAO, chon_ky
from apps.danh_muc.models import DichVu, KhuVuc
from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.models import NhatKyThaoTac
from apps.tai_chinh.models import PhieuDoiSoat, ThanhToan
from apps.tai_khoan.models import NguoiDung, VaiTro
from apps.tiep_nhan_dieu_phoi.dao import ThoDAO
from apps.tiep_nhan_dieu_phoi.models import PhanCong
from tests.conftest import anh_thu

pytestmark = pytest.mark.django_db


def _dang_nhap(vai_tro) -> tuple[Client, NguoiDung]:
    nguoi = NguoiDung.objects.filter(
        vai_tro=vai_tro, is_active=True, so_dien_thoai__startswith="0900"
    ).first()
    c = Client()
    c.force_login(nguoi)
    return c, nguoi


def _ok(phan_hoi, *, chuyen_den: str | None = None):
    """POST thành công = chuyển hướng (không render lại form lỗi)."""
    assert phan_hoi.status_code == 302, phan_hoi.content.decode()[:600]
    if chuyen_den:
        assert phan_hoi.url == chuyen_den
    return phan_hoi


def test_e2e_mot_ngay_lam_viec(capsys):
    call_command("nap_du_lieu_mau")
    capsys.readouterr()  # không để mật khẩu mẫu lọt vào log kiểm thử
    tong_dai, nd_td = _dang_nhap(VaiTro.TONG_DAI)
    ke_toan, _ = _dang_nhap(VaiTro.KE_TOAN)
    giam_doc, nd_gd = _dang_nhap(VaiTro.GIAM_DOC)
    hom_nay = chon_ky("hom_nay")
    truoc = BaoCaoDAO.lap(nd_gd, hom_nay)

    # 1) Tổng đài tiếp nhận cuộc gọi khách mới, chốt lịch ngày mai 08:00–10:00 (UC02, UC03 — T2)
    dv = DichVu.objects.get(ma="SC-DH-GAS")
    ngay_hen = timezone.localdate() + timedelta(days=1)
    _ok(
        tong_dai.post(
            "/don/moi/",
            {
                "so_dien_thoai": "0911 222 333",
                "ho_ten": "Chị Hạnh",
                "dia_chi_chi_tiet": "Số 5 ngõ 12 Láng Hạ",
                "khu_vuc": KhuVuc.objects.get(ma="DONG_DA").pk,
                "dich_vu_yeu_cau": dv.pk,
                "mo_ta_su_co": "Điều hòa không mát",
                "kenh_tiep_nhan": "DIEN_THOAI",
                "ngay_hen": ngay_hen.isoformat(),
                "khung_gio": "08:00-10:00",
            },
        )
    )
    don = DonSuaChua.objects.get(khach_hang__so_dien_thoai="0911222333")
    assert don.trang_thai == "CHO_CU_THO" and don.ma_don.startswith(f"HF{timezone.localdate():%y%m%d}-")

    # 2) Cử thợ: mở gợi ý (UC05), gửi đề nghị cho thợ đứng đầu danh sách phù hợp (UC04)
    assert tong_dai.get(f"/don/{don.ma_don}/cu-tho/").status_code == 200
    tho = next(g.tho for g in ThoDAO.goi_y_tho(don) if g.phu_hop)
    _ok(tong_dai.post(f"/don/{don.ma_don}/cu-tho/", {"hanh_dong": "gui", "tho": [tho.pk]}))
    pc = PhanCong.objects.get(don=don, tho=tho)
    assert pc.trang_thai == "CHO_PHAN_HOI"

    # 3) Thợ nhận việc trên điện thoại (UC07) — ≤ 3 chạm: mở đề nghị → NHẬN VIỆC
    tho_c = Client()
    tho_c.force_login(tho.nguoi_dung)
    assert tho_c.get(f"/tho/de-nghi/{pc.pk}/").status_code == 200
    _ok(tho_c.post(f"/tho/de-nghi/{pc.pk}/nhan/"), chuyen_den=f"/tho/don/{don.ma_don}/")

    # 4) Đến nơi → báo giá (UC08): tiền công theo bảng giá + vật tư thợ ứng; khách đồng ý (T9, T11)
    _ok(tho_c.post(f"/tho/don/{don.ma_don}/den-noi/"), chuyen_den=f"/tho/don/{don.ma_don}/bao-gia/")
    bao_gia = f"/tho/don/{don.ma_don}/bao-gia/"
    _ok(tho_c.post(bao_gia, {"hanh_dong": "them_dich_vu", "dich_vu": dv.pk, "so_luong": "1", "don_gia": ""}))
    _ok(
        tho_c.post(
            bao_gia,
            {
                "hanh_dong": "them_vat_tu",
                "mo_ta": "Gas R32",
                "so_luong": "1",
                "don_gia": "450000",
                "gia_mua": "280000",
                "nguoi_ung": "THO",
            },
        )
    )
    _ok(
        tho_c.post(bao_gia, {"hanh_dong": "dong_y", "nguoi_xac_nhan": "Chị Hạnh"}),
        chuyen_den=f"/tho/don/{don.ma_don}/hoan-thanh/",
    )
    tong = DonSuaChua.objects.get(pk=don.pk).tong_tien
    assert tong == 350_000 + 450_000

    # 5) Hoàn thành (UC09): ảnh hiện trường + tiền mặt đúng tổng (T15) → ThanhToan, phiếu bảo hành 90 ngày
    hoan_thanh = f"/tho/don/{don.ma_don}/hoan-thanh/"
    _ok(tho_c.post(hoan_thanh, {"hanh_dong": "tai_anh", "anh": anh_thu(800, 600)}))
    _ok(
        tho_c.post(hoan_thanh, {"hanh_dong": "hoan_thanh", "so_tien": str(tong), "hinh_thuc": "TIEN_MAT"}),
        chuyen_den=f"/tho/don/{don.ma_don}/da-xong/",
    )
    don.refresh_from_db()
    assert (don.trang_thai, don.tong_tien_phai_thu) == ("HOAN_THANH", tong)
    assert don.phieu_bao_hanh.ngay_het_han == timezone.localdate() + timedelta(days=90)
    assert ThanhToan.objects.get(don=don).trang_thai == "CHUA_NOP"

    # 6) Khách gọi lại: tổng đài tạo đơn bảo hành từ chi tiết đơn (UC11 — T16)
    assert f"/bao-hanh/moi/?don_goc={don.ma_don}" in tong_dai.get(f"/don/{don.ma_don}/").content.decode()
    _ok(
        tong_dai.post(
            f"/bao-hanh/moi/?don_goc={don.ma_don}",
            {"mo_ta_su_co": "Lại không mát", "kenh_tiep_nhan": "DIEN_THOAI"},
        )
    )
    don.refresh_from_db()
    bh = DonSuaChua.objects.get(don_goc=don)
    assert (don.trang_thai, bh.loai_don, bh.trang_thai) == ("DANG_BAO_HANH", "BAO_HANH", "CHO_XAC_NHAN_LICH")

    # 7) Cuối ngày kế toán đối soát thợ (UC12): lập phiếu → chốt → xác nhận đã nộp
    # khoản chưa nộp chưa nằm trong phiếu nào (thợ mẫu có thể đang có phiếu nháp/đã chốt từ trước)
    no_cua_tho = sum(
        ThanhToan.objects.filter(tho=tho, trang_thai="CHUA_NOP", phieu_doi_soat=None).values_list(
            "so_tien", flat=True
        )
    )
    _ok(ke_toan.post("/ke-toan/doi-soat/lap/", {"tho": tho.pk}))
    phieu = PhieuDoiSoat.objects.filter(tho=tho).latest("tao_luc")
    tt_don = ThanhToan.objects.get(don=don)
    assert tt_don.phieu_doi_soat == phieu
    dong_chon = list(phieu.ds_thanh_toan.values_list("pk", flat=True))
    _ok(ke_toan.post(f"/ke-toan/doi-soat/{phieu.ma}/", {"hanh_dong": "chot", "thanh_toan": dong_chon}))
    _ok(ke_toan.post(f"/ke-toan/doi-soat/{phieu.ma}/", {"hanh_dong": "da_nop"}))
    phieu.refresh_from_db()
    assert phieu.trang_thai == "DA_NOP" and phieu.tong_tien_thu == no_cua_tho
    assert phieu.tong_vat_tu_ung >= 280_000  # vật tư thợ ứng của đơn này được hoàn (UC10 → UC12)
    tt_don.refresh_from_db()
    assert tt_don.trang_thai == "DA_NOP"

    # 8) Giám đốc xem báo cáo hôm nay (UC14): số liệu tăng đúng phần vừa làm
    trang = giam_doc.get("/bao-cao/", {"ky": "hom_nay"})
    assert trang.status_code == 200
    sau = BaoCaoDAO.lap(nd_gd, hom_nay)
    assert sau.so_tiep_nhan == truoc.so_tiep_nhan + 2  # đơn mới + đơn bảo hành
    assert sau.so_hoan_thanh == truoc.so_hoan_thanh + 1
    assert sau.doanh_thu == truoc.doanh_thu + tong
    assert sau.lam_lai.tu_so == truoc.lam_lai.tu_so + 1
    assert sau.cong_no_hien_tai == truoc.cong_no_hien_tai - (
        no_cua_tho - tong
    )  # nộp cả khoản cũ chưa đối soát
    assert f"{sau.doanh_thu:,} đ".replace(",", ".") in trang.content.decode()

    # Nhật ký đơn đủ dấu vết từng bước (NFR06), xem được ở /quan-tri/nhat-ky/
    hanh_dong = set(
        NhatKyThaoTac.objects.filter(doi_tuong=f"DonSuaChua:{don.ma_don}").values_list("hanh_dong", flat=True)
    )
    assert {
        "TAO_DON",
        "CU_THO",
        "THO_DEN_NOI",
        "KHACH_DUYET_GIA",
        "GHI_TIEN",
        "HOAN_THANH",
        "TAO_DON_BAO_HANH",
    } <= hanh_dong
    chuyen = set(
        NhatKyThaoTac.objects.filter(
            doi_tuong=f"DonSuaChua:{don.ma_don}", hanh_dong="DOI_TRANG_THAI"
        ).values_list("du_lieu_sau__chuyen", flat=True)
    )
    assert {"T2", "T7", "T9", "T11", "T15", "T16"} <= chuyen
    nk = giam_doc.get("/quan-tri/nhat-ky/", {"doi_tuong": don.ma_don}).content.decode()
    assert "TAO_DON_BAO_HANH" in nk and "GHI_TIEN" in nk

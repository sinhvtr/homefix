"""UC04 — Điều phối, cử thợ; UC05 — gợi ý thợ; BR01, BR02, BR04; NFR01; luồng 2a, 3a, 4a."""

import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from freezegun import freeze_time

from apps.danh_muc.models import Tho
from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.models import NhatKyThaoTac
from apps.tai_khoan.models import VaiTro
from apps.thong_bao.models import ThongBao
from apps.tiep_nhan_dieu_phoi.dao import PhanCongDAO, ThoDAO
from apps.tiep_nhan_dieu_phoi.models import LichHen, PhanCong
from tests.conftest import (
    DiaChiFactory,
    DichVuFactory,
    KhuVucFactory,
    NguoiDungFactory,
    ThietBiFactory,
    don_cho_cu_tho,
    tao_don,
    tao_lich,
    tao_tho_phu_hop,
)

pytestmark = pytest.mark.django_db
VN = ZoneInfo("Asia/Ho_Chi_Minh")
HEN = datetime(2099, 6, 1, 8, 0, tzinfo=VN)  # khung 08:00-10:00


@pytest.fixture
def tong_dai():
    return NguoiDungFactory(vai_tro=VaiTro.TONG_DAI)


@pytest.fixture
def kv():
    return KhuVucFactory(ten="Cầu Giấy")


@pytest.fixture
def dv():
    return DichVuFactory(ten_dich_vu="Vệ sinh điều hòa", loai_thiet_bi="DIEU_HOA", don_gia_tham_khao=150_000)


@pytest.fixture
def don(kv, dv):
    return don_cho_cu_tho(ngay_gio=HEN, dia_chi=DiaChiFactory(khu_vuc=kv), dich_vu=dv)


def _ten_phu_hop(don):
    return [g.tho.ho_ten for g in ThoDAO.goi_y_tho(don) if g.phu_hop]


def _loai(don):
    return {g.tho.ho_ten: g.ly_do_loai for g in ThoDAO.goi_y_tho(don) if not g.phu_hop}


def _don_ban(tho, bat_dau, trang_thai="DA_CO_THO"):
    d = tao_don(trang_thai, tho=tho)
    tao_lich(d, ngay_gio=bat_dau)
    return d


# ============================================================== BR04 — chỉ gợi ý thợ đúng nghề, không trùng lịch


def test_br04_tho_sai_nghe_trung_lich_dang_nghi_tat_nhan_viec_bi_loai(don, dv, kv):
    tao_tho_phu_hop(dv, kv, ho_ten="A Hợp lệ")
    ThoFactory_sai = tao_tho_phu_hop(DichVuFactory(loai_thiet_bi="MAY_GIAT"), kv, ho_ten="B Sai nghề")
    trung = tao_tho_phu_hop(dv, kv, ho_ten="C Trùng lịch")
    don_trung = _don_ban(trung, HEN + timedelta(minutes=30))
    tao_tho_phu_hop(dv, kv, ho_ten="D Đang nghỉ", nghi_den=HEN + timedelta(days=1))
    tao_tho_phu_hop(dv, kv, ho_ten="E Tắt nhận việc", dang_nhan_viec=False)
    khoa = tao_tho_phu_hop(dv, kv, ho_ten="F Bị khóa")
    khoa.nguoi_dung.is_active = False
    khoa.nguoi_dung.save()

    assert _ten_phu_hop(don) == ["A Hợp lệ"]
    loai = _loai(don)
    assert loai[ThoFactory_sai.ho_ten] == ["Sai nghề"]
    assert loai["C Trùng lịch"] == [f"Trùng lịch {don_trung.ma_don}"]
    assert loai["D Đang nghỉ"][0].startswith("Đang nghỉ đến")
    assert loai["E Tắt nhận việc"] == ["Tắt nhận việc"]
    assert "F Bị khóa" not in loai  # tài khoản khóa: không hiện


def test_br04_ky_nang_cung_loai_thiet_bi_van_phu_hop(don):
    """[ĐX] A-14: thợ có dịch vụ khác nhưng cùng loại thiết bị (điều hòa) vẫn được gợi ý."""
    tao_tho_phu_hop(DichVuFactory(loai_thiet_bi="DIEU_HOA", ten_dich_vu="Nạp gas"), ho_ten="Thợ điều hòa")
    assert _ten_phu_hop(don) == ["Thợ điều hòa"]


@pytest.mark.parametrize(
    ("lech_phut", "phu_hop"),
    [(-150, True), (-149, False), (-120, False), (149, False), (150, True)],
)
def test_br04_dem_di_chuyen_30_phut(don, dv, lech_phut, phu_hop):
    """Hẹn 08:00-10:00, lịch khác dài 2 giờ, đệm 30 phút: lịch khác phải kết thúc muộn nhất 07:30
    hoặc bắt đầu sớm nhất 10:30 mới không trùng."""
    tho = tao_tho_phu_hop(dv, ho_ten="Thợ X")
    _don_ban(tho, HEN + timedelta(minutes=lech_phut))
    assert (_ten_phu_hop(don) == ["Thợ X"]) is phu_hop


def test_br04_don_da_xong_hoac_huy_khong_chiem_lich(don, dv):
    tho = tao_tho_phu_hop(dv, ho_ten="Thợ X")
    _don_ban(tho, HEN, trang_thai="HOAN_THANH")
    _don_ban(tho, HEN, trang_thai="DA_HUY")
    assert _ten_phu_hop(don) == ["Thợ X"]


def test_br04_nghi_den_truoc_gio_hen_van_phu_hop(don, dv):
    tao_tho_phu_hop(dv, ho_ten="Thợ X", nghi_den=HEN - timedelta(hours=1))
    assert _ten_phu_hop(don) == ["Thợ X"]


# ============================================================== UC05 — thứ tự xếp hạng


def test_uc05_thu_tu_xep_hang_bo_du_lieu_co_dinh(don, dv, kv, tong_dai):
    khac_kv = KhuVucFactory(ten="Hà Đông")
    # (a) đúng khu vực trước
    tao_tho_phu_hop(dv, khac_kv, ho_ten="Z Khác khu vực", hinh_thuc="CHINH_THUC")
    # (b) ít việc trong ngày trước
    ban_1 = tao_tho_phu_hop(dv, kv, ho_ten="Y Một việc hôm đó", hinh_thuc="CHINH_THUC")
    _don_ban(ban_1, HEN + timedelta(hours=6))
    # (c) lâu chưa được giao trước; (d) chính thức trước cộng tác viên
    moi_giao = tao_tho_phu_hop(dv, kv, ho_ten="X Mới được giao", hinh_thuc="CHINH_THUC")
    PhanCong.objects.create(
        don=tao_don(),
        tho=moi_giao,
        nguoi_giao=tong_dai,
        thoi_diem_giao=timezone.now() - timedelta(hours=1),
        han_phan_hoi=timezone.now(),
        trang_thai="TU_CHOI",
        tien_cong_du_kien=0,
    )
    tao_tho_phu_hop(dv, kv, ho_ten="W Cộng tác viên", hinh_thuc="CONG_TAC_VIEN")
    tao_tho_phu_hop(dv, kv, ho_ten="V Chính thức", hinh_thuc="CHINH_THUC")
    assert _ten_phu_hop(don) == [
        "V Chính thức",
        "W Cộng tác viên",
        "X Mới được giao",
        "Y Một việc hôm đó",
        "Z Khác khu vực",
    ]


def test_uc05_thong_tin_tren_tung_dong(don, dv, kv, tong_dai):
    tho = tao_tho_phu_hop(dv, kv, ho_ten="Thợ A")
    _don_ban(tho, HEN + timedelta(hours=5))  # 13:00-15:00
    for tt in ("DA_NHAN", "TU_CHOI", "QUA_HAN", "DA_NHAN"):
        PhanCong.objects.create(
            don=tao_don(),
            tho=tho,
            nguoi_giao=tong_dai,
            thoi_diem_giao=timezone.now(),
            han_phan_hoi=timezone.now(),
            trang_thai=tt,
            tien_cong_du_kien=0,
        )
    g = ThoDAO.goi_y_tho(don)[0]
    assert g.phu_trach_khu_vuc and g.khu_vuc == ["Cầu Giấy"]
    assert g.so_viec_trong_ngay == 1
    assert g.khung_gio_ban[0].startswith("13:00-15:00 HF")
    assert timezone.localtime(g.du_kien_ranh_luc).strftime("%H:%M") == "15:30"
    assert g.ty_le_nhan_30_ngay == 0.5


def test_uc05_danh_dau_da_tu_choi_qua_han_don_nay(don, dv, tong_dai):
    a = tao_tho_phu_hop(dv, ho_ten="A")
    b = tao_tho_phu_hop(dv, ho_ten="B")
    for tho, tt in ((a, "TU_CHOI"), (b, "QUA_HAN")):
        PhanCong.objects.create(
            don=don,
            tho=tho,
            nguoi_giao=tong_dai,
            thoi_diem_giao=timezone.now(),
            han_phan_hoi=timezone.now(),
            trang_thai=tt,
            tien_cong_du_kien=0,
        )
    g = {x.tho.ho_ten: x for x in ThoDAO.goi_y_tho(don)}
    assert g["A"].da_tu_choi and not g["A"].da_qua_han
    assert g["B"].da_qua_han


def test_uc05_ly_do_loai_hien_tren_man_hinh(client_vai_tro, don, dv):
    tao_tho_phu_hop(DichVuFactory(loai_thiet_bi="TU_LANH"), ho_ten="Thợ tủ lạnh")
    noi_dung = client_vai_tro(VaiTro.TONG_DAI).get(f"/don/{don.ma_don}/cu-tho/").content.decode()
    assert "Không phù hợp (1)" in noi_dung and "Thợ tủ lạnh</strong>: Sai nghề" in noi_dung


# ============================================================== NFR01 — gợi ý ≤ 3 giây, ≤ 5 câu SQL (200 đơn mở, 50 thợ)


def _du_lieu_lon(dv, kv, tong_dai):
    khu = [kv] + [KhuVucFactory() for _ in range(11)]
    tho = [
        tao_tho_phu_hop(dv, khu[i % 12], hinh_thuc="CHINH_THUC" if i % 2 else "CONG_TAC_VIEN")
        for i in range(50)
    ]
    mau = tao_don(dich_vu=dv)
    ds_don = []
    for i in range(200):
        tt = ["CHO_CU_THO", "DA_CO_THO", "DANG_SUA", "CHO_XAC_NHAN_LICH"][i % 4]
        ds_don.append(
            DonSuaChua(
                ma_don=f"HF990601-{i:03d}",
                khach_hang=mau.khach_hang,
                dia_chi=mau.dia_chi,
                dich_vu_yeu_cau=dv,
                kenh_tiep_nhan="DIEN_THOAI",
                trang_thai=tt,  # bulk_create bỏ qua save() — chỉ dùng để dựng dữ liệu hiệu năng
                tho=tho[i % 50] if tt in ("DA_CO_THO", "DANG_SUA") else None,
                nguoi_tao=tong_dai,
            )
        )
    DonSuaChua.objects.bulk_create(ds_don)
    LichHen.objects.bulk_create(
        LichHen(
            don=d,
            bat_dau=HEN + timedelta(hours=i % 10),
            ket_thuc=HEN + timedelta(hours=i % 10 + 2),
            nguoi_tao=tong_dai,
        )
        for i, d in enumerate(DonSuaChua.objects.filter(ma_don__startswith="HF990601"))
    )
    PhanCong.objects.bulk_create(
        PhanCong(
            don=ds_don[i],
            tho=tho[i % 50],
            nguoi_giao=tong_dai,
            thoi_diem_giao=timezone.now() - timedelta(days=i % 40),
            han_phan_hoi=timezone.now(),
            trang_thai=["DA_NHAN", "TU_CHOI", "QUA_HAN"][i % 3],
            tien_cong_du_kien=0,
        )
        for i in range(200)
    )


def test_nfr01_goi_y_tho_nhanh_va_so_cau_sql_co_dinh(don, dv, kv, tong_dai, django_assert_max_num_queries):
    _du_lieu_lon(dv, kv, tong_dai)
    don = DonSuaChua.objects.select_related("dich_vu_yeu_cau", "dia_chi").get(pk=don.pk)
    lich = don.lich_hieu_luc
    ThoDAO.goi_y_tho(don, lich)  # làm ấm bộ đệm cấu hình
    bat_dau = time.perf_counter()
    with django_assert_max_num_queries(5):
        goi_y = ThoDAO.goi_y_tho(don, lich)
    assert time.perf_counter() - bat_dau < 3
    assert len(goi_y) == 50 and any(g.phu_hop for g in goi_y)


def test_nfr01_trang_cu_tho_duoi_3_giay(client_vai_tro, don, dv, kv, tong_dai):
    _du_lieu_lon(dv, kv, tong_dai)
    c = client_vai_tro(VaiTro.TONG_DAI)
    bat_dau = time.perf_counter()
    phan_hoi = c.get(f"/don/{don.ma_don}/cu-tho/")
    assert phan_hoi.status_code == 200 and time.perf_counter() - bat_dau < 3


# ============================================================== UC04 luồng chính + BR01


def test_uc04_gui_3_tho_tho_thu_2_nhan_truoc(don, dv, kv, tong_dai):
    t1, t2, t3 = (tao_tho_phu_hop(dv, kv, ho_ten=f"Thợ {i}") for i in (1, 2, 3))
    da_gui = PhanCongDAO.gui_de_nghi(tong_dai, don, [t1.pk, t2.pk, t3.pk])
    assert set(da_gui) == {t1.pk, t2.pk, t3.pk}
    pc = {p.tho_id: p for p in PhanCong.objects.filter(don=don)}
    assert all(p.trang_thai == "CHO_PHAN_HOI" and p.nguoi_giao == tong_dai for p in pc.values())
    assert all(p.han_phan_hoi - p.thoi_diem_giao == timedelta(minutes=15) for p in pc.values())
    assert pc[t1.pk].tien_cong_du_kien == 150_000
    # mỗi thợ có thông báo đề nghị, không lộ SĐT khách
    for t in (t1, t2, t3):
        tb = ThongBao.objects.get(nguoi_nhan=t.nguoi_dung, tieu_de__startswith="Việc mới")
        assert (
            don.khach_hang.so_dien_thoai not in tb.noi_dung and tb.duong_dan == f"/tho/de-nghi/{pc[t.pk].pk}/"
        )

    ok, _ = PhanCongDAO.nhan_viec(t2.nguoi_dung, pc[t2.pk].pk)
    assert ok
    d = DonSuaChua.objects.get(pk=don.pk)
    assert (d.trang_thai, d.tho_id) == ("DA_CO_THO", t2.pk)
    trang_thai = dict(PhanCong.objects.filter(don=don).values_list("tho_id", "trang_thai"))
    assert trang_thai == {t1.pk: "DA_HUY", t2.pk: "DA_NHAN", t3.pk: "DA_HUY"}
    for t in (t1, t3):
        assert ThongBao.objects.filter(nguoi_nhan=t.nguoi_dung, noi_dung="Đơn đã có thợ nhận").exists()
    assert ThongBao.objects.filter(nguoi_nhan=tong_dai, tieu_de=f"Thợ 2 đã nhận {don.ma_don}").exists()
    # Nhật ký cử thợ: ai, lúc nào, gửi cho những thợ nào (NFR06)
    nk = NhatKyThaoTac.objects.get(hanh_dong="CU_THO", doi_tuong=f"DonSuaChua:{don.ma_don}")
    assert nk.nguoi_dung == tong_dai and set(nk.du_lieu_sau["gui_cho_tho"]) == {t1.pk, t2.pk, t3.pk}
    # Thợ 1 bấm nhận sau → "Đơn đã có thợ nhận"
    assert PhanCongDAO.nhan_viec(t1.nguoi_dung, pc[t1.pk].pk) == (False, "Đơn đã có thợ nhận")


def test_br01_tho_khong_tao_duoc_phan_cong(don, dv):
    tho = tao_tho_phu_hop(dv)
    with pytest.raises(PermissionDenied):
        PhanCongDAO.giao_viec(PhanCong(don=don, tho=tho, nguoi_giao=tho.nguoi_dung))
    with pytest.raises(PermissionDenied):
        PhanCongDAO.gui_de_nghi(tho.nguoi_dung, don, [tho.pk])
    assert not PhanCong.objects.exists()


def test_br01_khong_co_phan_cong_thieu_nguoi_giao(don, dv):
    tho = tao_tho_phu_hop(dv)
    with pytest.raises(IntegrityError), transaction.atomic():
        PhanCong.objects.create(
            don=don,
            tho=tho,
            nguoi_giao=None,
            thoi_diem_giao=timezone.now(),
            han_phan_hoi=timezone.now(),
            tien_cong_du_kien=0,
        )


def test_br01_khong_tu_dong_giao_viec(don, dv):
    """Hệ thống chỉ gợi ý: gọi gợi ý không tạo phân công nào."""
    tao_tho_phu_hop(dv)
    ThoDAO.goi_y_tho(don)
    assert not PhanCong.objects.exists()


def test_br01_ke_toan_khong_cu_tho(client_vai_tro, don, dv):
    tho = tao_tho_phu_hop(dv)
    c = client_vai_tro(VaiTro.KE_TOAN)
    assert c.post(f"/don/{don.ma_don}/cu-tho/", {"hanh_dong": "gui", "tho": [tho.pk]}).status_code == 403
    assert not PhanCong.objects.exists()


def test_khong_gui_cho_tho_khong_phu_hop_hoac_dang_cho(don, dv, tong_dai):
    sai_nghe = tao_tho_phu_hop(DichVuFactory(loai_thiet_bi="TU_LANH"))
    hop = tao_tho_phu_hop(dv)
    assert PhanCongDAO.gui_de_nghi(tong_dai, don, [sai_nghe.pk, hop.pk]) == [hop.pk]
    assert PhanCongDAO.gui_de_nghi(tong_dai, don, [hop.pk]) == []  # đang chờ phản hồi
    assert PhanCong.objects.count() == 1


def test_gui_de_nghi_qua_man_hinh(client_vai_tro, don, dv):
    a, b = tao_tho_phu_hop(dv), tao_tho_phu_hop(dv)
    c = client_vai_tro(VaiTro.TONG_DAI)
    phan_hoi = c.post(f"/don/{don.ma_don}/cu-tho/", {"hanh_dong": "gui", "tho": [a.pk, b.pk]}, follow=True)
    assert "Đã gửi đề nghị cho 2 thợ" in phan_hoi.content.decode()
    assert "data-han=" in phan_hoi.content.decode()  # đồng hồ đếm ngược trên đơn


def test_tien_cong_du_kien_ve_sinh_nhan_so_thiet_bi(kv, dv, tong_dai):
    dc = DiaChiFactory(khu_vuc=kv)
    don = don_cho_cu_tho(ngay_gio=HEN, dia_chi=dc, dich_vu=dv)
    don.thiet_bi.set([ThietBiFactory(dia_chi=dc), ThietBiFactory(dia_chi=dc)])
    tho = tao_tho_phu_hop(dv)
    PhanCongDAO.gui_de_nghi(tong_dai, don, [tho.pk])
    assert PhanCong.objects.get().tien_cong_du_kien == 300_000


# ============================================================== Luồng 2a, 3a, 4a; thu hồi; rút việc


def test_luong_2a_de_nghi_khach_doi_lich(client_vai_tro, don, dv, tong_dai):
    tho = tao_tho_phu_hop(dv)
    PhanCongDAO.gui_de_nghi(tong_dai, don, [tho.pk])
    c = client_vai_tro(VaiTro.TONG_DAI)
    c.post(f"/don/{don.ma_don}/cu-tho/", {"hanh_dong": "doi_lich"})
    d = DonSuaChua.objects.get(pk=don.pk)
    assert d.trang_thai == "CHO_XAC_NHAN_LICH"  # T6
    assert LichHen.objects.get(don=don).trang_thai == "DA_HUY"
    assert PhanCong.objects.get(don=don).trang_thai == "DA_HUY"
    assert ThongBao.objects.filter(nguoi_nhan=tho.nguoi_dung, tieu_de__contains="đã hủy").exists()


def test_luong_2a_danh_dau_chua_cu_duoc_bat_buoc_ly_do(client_vai_tro, don):
    c = client_vai_tro(VaiTro.TONG_DAI)
    c.post(f"/don/{don.ma_don}/cu-tho/", {"hanh_dong": "chua_cu_duoc", "ly_do": ""})
    assert not DonSuaChua.objects.get(pk=don.pk).canh_bao_chua_cu_duoc
    c.post(f"/don/{don.ma_don}/cu-tho/", {"hanh_dong": "chua_cu_duoc", "ly_do": "Hết thợ điều hòa"})
    d = DonSuaChua.objects.get(pk=don.pk)
    assert (
        d.canh_bao_chua_cu_duoc
        and d.ly_do_chua_cu_duoc == "Hết thợ điều hòa"
        and d.trang_thai == "CHO_CU_THO"
    )
    assert "Chưa cử được thợ" in c.get("/tong-dai/").content.decode()


def test_luong_3a_tho_dong_y_qua_dien_thoai(don, dv, tong_dai):
    a, b = tao_tho_phu_hop(dv), tao_tho_phu_hop(dv)
    PhanCongDAO.gui_de_nghi(tong_dai, don, [a.pk])
    with pytest.raises(ValidationError):
        PhanCongDAO.giao_viec(PhanCong(don=don, tho=b, nguoi_giao=tong_dai, giao_qua_dien_thoai=True))
    assert PhanCongDAO.giao_viec(
        PhanCong(don=don, tho=b, nguoi_giao=tong_dai, giao_qua_dien_thoai=True, ghi_chu="Gọi 9h, thợ đồng ý")
    )
    d = DonSuaChua.objects.get(pk=don.pk)
    assert (d.trang_thai, d.tho_id) == ("DA_CO_THO", b.pk)
    assert dict(PhanCong.objects.values_list("tho_id", "trang_thai")) == {a.pk: "DA_HUY", b.pk: "DA_NHAN"}
    assert PhanCong.objects.get(tho=b).giao_qua_dien_thoai
    assert NhatKyThaoTac.objects.filter(hanh_dong="CU_THO_QUA_DIEN_THOAI", nguoi_dung=tong_dai).exists()


def test_br02_qua_15_phut_qua_han_va_thong_bao_can_cu_lai(don, dv, tong_dai):
    tho = tao_tho_phu_hop(dv, ho_ten="Thợ chậm")
    with freeze_time(timezone.now()) as dong_ho:
        PhanCongDAO.gui_de_nghi(tong_dai, don, [tho.pk])
        dong_ho.tick(timedelta(minutes=14))
        assert PhanCongDAO.kiem_tra_qua_han() == {"qua_han": 0, "can_cu_lai": 0}
        assert PhanCong.objects.get().trang_thai == "CHO_PHAN_HOI"
        dong_ho.tick(timedelta(minutes=1, seconds=1))  # +15 phút 1 giây
        assert PhanCongDAO.kiem_tra_qua_han() == {"qua_han": 1, "can_cu_lai": 1}
        assert PhanCong.objects.get().trang_thai == "QUA_HAN"
        assert ThongBao.objects.filter(nguoi_nhan=tong_dai, tieu_de=f"Cần cử lại {don.ma_don}").exists()
        assert ThongBao.objects.filter(nguoi_nhan=tong_dai, tieu_de__contains="quá hạn phản hồi").exists()
        assert PhanCongDAO.kiem_tra_qua_han() == {"qua_han": 0, "can_cu_lai": 0}  # lũy đẳng


def test_br02_con_de_nghi_khac_dang_cho_thi_chua_can_cu_lai(don, dv, tong_dai):
    a, b = tao_tho_phu_hop(dv), tao_tho_phu_hop(dv)
    with freeze_time(timezone.now()) as dong_ho:
        PhanCongDAO.gui_de_nghi(tong_dai, don, [a.pk])
        dong_ho.tick(timedelta(minutes=10))
        PhanCongDAO.gui_de_nghi(tong_dai, don, [b.pk])
        dong_ho.tick(timedelta(minutes=6))
        assert PhanCongDAO.kiem_tra_qua_han() == {"qua_han": 1, "can_cu_lai": 0}


def test_br02_bang_don_the_can_cu_lai_va_goi_y_loai_tho_da_qua_han(client_vai_tro, don, dv, tong_dai):
    tho = tao_tho_phu_hop(dv, ho_ten="Thợ chậm")
    with freeze_time(timezone.now() - timedelta(minutes=20)):
        PhanCongDAO.gui_de_nghi(tong_dai, don, [tho.pk])
    PhanCongDAO.kiem_tra_qua_han()
    noi_dung = client_vai_tro(VaiTro.TONG_DAI).get("/tong-dai/").content.decode()
    assert "Cần cử lại" in noi_dung
    g = ThoDAO.goi_y_tho(don)[0]
    assert g.da_qua_han  # danh sách gợi ý đánh dấu thợ đã quá hạn đơn này


def test_thu_hoi_de_nghi(client_vai_tro, don, dv, tong_dai):
    tho = tao_tho_phu_hop(dv)
    PhanCongDAO.gui_de_nghi(tong_dai, don, [tho.pk])
    pc = PhanCong.objects.get()
    client_vai_tro(VaiTro.TONG_DAI).post(
        f"/don/{don.ma_don}/cu-tho/", {"hanh_dong": "thu_hoi", "phan_cong": pc.pk}
    )
    pc.refresh_from_db()
    assert pc.trang_thai == "DA_HUY"
    assert ThongBao.objects.filter(nguoi_nhan=tho.nguoi_dung, tieu_de__contains="thu hồi").exists()


def test_rut_viec_t8(client_vai_tro, don, dv, tong_dai):
    tho = tao_tho_phu_hop(dv)
    PhanCongDAO.gui_de_nghi(tong_dai, don, [tho.pk])
    PhanCongDAO.nhan_viec(tho.nguoi_dung, PhanCong.objects.get().pk)
    client_vai_tro(VaiTro.TONG_DAI).post(
        f"/don/{don.ma_don}/cu-tho/", {"hanh_dong": "rut_viec", "ly_do": "Khách xin thợ khác"}
    )
    d = DonSuaChua.objects.get(pk=don.pk)
    assert (d.trang_thai, d.tho_id) == ("CHO_CU_THO", None)
    assert PhanCong.objects.get().trang_thai == "DA_HUY"
    assert ThongBao.objects.filter(nguoi_nhan=tho.nguoi_dung, tieu_de__contains="đã bị rút").exists()


def test_huy_don_huy_de_nghi_va_bao_tho(don, dv, tong_dai):
    from apps.don_sua_chua.dao import DonSuaChuaDAO

    tho = tao_tho_phu_hop(dv)
    PhanCongDAO.gui_de_nghi(tong_dai, don, [tho.pk])
    DonSuaChuaDAO.huy(tong_dai, don, "Khách hủy")
    assert PhanCong.objects.get().trang_thai == "DA_HUY"
    assert ThongBao.objects.filter(nguoi_nhan=tho.nguoi_dung, tieu_de=f"Đơn {don.ma_don} đã hủy").exists()


def test_doi_hen_khi_da_co_tho_bao_tho(don, dv, tong_dai):
    from datetime import date

    from apps.tiep_nhan_dieu_phoi.dao import LichHenDAO

    tho = tao_tho_phu_hop(dv)
    PhanCongDAO.gui_de_nghi(tong_dai, don, [tho.pk])
    PhanCongDAO.nhan_viec(tho.nguoi_dung, PhanCong.objects.get().pk)
    LichHenDAO.doi_hen(
        tong_dai, DonSuaChua.objects.get(pk=don.pk), date(2099, 6, 2), "13:00-15:00", "Khách bận"
    )
    assert ThongBao.objects.filter(nguoi_nhan=tho.nguoi_dung, tieu_de=f"Đổi lịch {don.ma_don}").exists()


# ============================================================== UC06 — cảnh báo


def test_uc06_nhan_cho_cu_tho_qua_30_phut(client_vai_tro, kv, dv):
    with freeze_time(timezone.now() - timedelta(minutes=31)):
        cu = don_cho_cu_tho(ngay_gio=HEN, dich_vu=dv)
    moi = don_cho_cu_tho(ngay_gio=HEN, dich_vu=dv)
    bang = client_vai_tro(VaiTro.TONG_DAI).get("/tong-dai/")
    cot = dict(bang.context["bang"].cot)["Chờ cử thợ"]
    assert [d.cho_cu_tho_qua_lau for d in cot] == [True, False] and cot[0].pk == cu.pk and cot[1].pk == moi.pk
    assert "Chờ cử thợ &gt; 30 phút" in bang.content.decode() and "nhap-nhay" in bang.content.decode()


def test_uc06_hen_trong_2_gio_chua_co_tho(client_vai_tro, dv):
    don = don_cho_cu_tho(ngay_gio=timezone.now() + timedelta(minutes=90), dich_vu=dv)
    noi_dung = client_vai_tro(VaiTro.TONG_DAI).get("/tong-dai/").content.decode()
    assert "Hẹn trong 2 giờ, chưa có thợ" in noi_dung and don.ma_don in noi_dung


def test_uc05_lich_tho_theo_ngay(client_vai_tro, dv):
    tho = tao_tho_phu_hop(dv, ho_ten="Thợ Lịch")
    d = _don_ban(tho, HEN)
    phan_hoi = client_vai_tro(VaiTro.TONG_DAI).get("/tho-lich/", {"ngay": "2099-06-01"})
    noi_dung = phan_hoi.content.decode()
    assert "Thợ Lịch" in noi_dung and d.ma_don in noi_dung and "08:00-10:00" in noi_dung
    assert Tho.objects.count() >= 1

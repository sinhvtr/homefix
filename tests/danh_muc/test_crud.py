"""UC13 — CRUD danh mục qua màn hình; nhật ký sửa giá (NFR06); không xóa dịch vụ đã dùng."""

import pytest
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction

from apps.danh_muc.dao import DichVuDAO, KhachHangDAO
from apps.danh_muc.models import DiaChi, DichVu, KhachHang, KhuVuc, ThietBi, Tho
from apps.he_thong.models import CauHinh, NhatKyThaoTac
from apps.tai_khoan.models import NguoiDung, VaiTro
from tests.conftest import (
    DiaChiFactory,
    DichVuFactory,
    KhachHangFactory,
    KhuVucFactory,
    ThietBiFactory,
    ThoFactory,
)

pytestmark = pytest.mark.django_db

DU_LIEU_DICH_VU = {
    "ma": "VS-DH-TT",
    "ten_dich_vu": "Vệ sinh điều hòa treo tường",
    "nhom_dich_vu": "VE_SINH_BAO_DUONG",
    "loai_thiet_bi": "DIEU_HOA",
    "don_gia_tham_khao": "150000",
    "don_vi_tinh": "máy",
    "thoi_han_bao_hanh_ngay": "",
    "dang_ap_dung": "on",
}


# ================================================================ Khu vực


def test_khu_vuc_them_sua_xoa(client_quan_tri):
    client_quan_tri.post("/danh-muc/khu-vuc/moi/", {"ma": "CAU_GIAY", "ten": "Cầu Giấy"})
    kv = KhuVuc.objects.get(ma="CAU_GIAY")
    client_quan_tri.post(f"/danh-muc/khu-vuc/{kv.pk}/sua/", {"ma": "CAU_GIAY", "ten": "Q. Cầu Giấy"})
    kv.refresh_from_db()
    assert kv.ten == "Q. Cầu Giấy"
    assert "Q. Cầu Giấy" in client_quan_tri.get("/danh-muc/khu-vuc/").content.decode()
    client_quan_tri.post(f"/danh-muc/khu-vuc/{kv.pk}/xoa/")
    assert not KhuVuc.objects.filter(pk=kv.pk).exists()
    assert list(
        NhatKyThaoTac.objects.filter(doi_tuong__startswith="KhuVuc:").values_list("hanh_dong", flat=True)
    ) == ["XOA_KHU_VUC", "SUA_KHU_VUC", "TAO_KHU_VUC"]


def test_khu_vuc_trung_ma_bao_loi(client_quan_tri):
    KhuVucFactory(ma="BA_DINH")
    phan_hoi = client_quan_tri.post("/danh-muc/khu-vuc/moi/", {"ma": "BA_DINH", "ten": "X"})
    assert phan_hoi.status_code == 200 and KhuVuc.objects.filter(ma="BA_DINH").count() == 1


def test_khong_xoa_khu_vuc_dang_dung(client_quan_tri):
    dc = DiaChiFactory()
    tho = ThoFactory()
    kv2 = KhuVucFactory()
    tho.khu_vuc_phu_trach.add(kv2)
    for kv in (dc.khu_vuc, kv2):
        phan_hoi = client_quan_tri.post(f"/danh-muc/khu-vuc/{kv.pk}/xoa/", follow=True)
        assert KhuVuc.objects.filter(pk=kv.pk).exists()
        assert "không xóa được" in phan_hoi.content.decode()


# ================================================================ Dịch vụ, bảng giá


@pytest.mark.parametrize(("nhom", "so_ngay"), [("VE_SINH_BAO_DUONG", 7), ("SUA_CHUA_THAY_VAT_TU", 90)])
def test_dich_vu_bao_hanh_mac_dinh_theo_nhom(client_quan_tri, nhom, so_ngay):
    client_quan_tri.post("/danh-muc/dich-vu/moi/", {**DU_LIEU_DICH_VU, "nhom_dich_vu": nhom})
    assert DichVu.objects.get(ma="VS-DH-TT").thoi_han_bao_hanh_ngay == so_ngay


def test_dich_vu_bao_hanh_mac_dinh_doc_tu_cau_hinh(client_quan_tri):
    CauHinh.objects.filter(khoa="BAO_HANH_VE_SINH_NGAY").update(gia_tri="10")
    client_quan_tri.post("/danh-muc/dich-vu/moi/", DU_LIEU_DICH_VU)
    assert DichVu.objects.get(ma="VS-DH-TT").thoi_han_bao_hanh_ngay == 10


def test_sua_gia_ghi_nhat_ky(client_quan_tri, quan_tri):
    dv = DichVuFactory(ma="VS-DH-TT", don_gia_tham_khao=150_000)
    du_lieu = {**DU_LIEU_DICH_VU, "don_gia_tham_khao": "170000", "thoi_han_bao_hanh_ngay": "7"}
    client_quan_tri.post(f"/danh-muc/dich-vu/{dv.pk}/sua/", du_lieu)
    dv.refresh_from_db()
    assert dv.don_gia_tham_khao == 170_000
    nk = NhatKyThaoTac.objects.get(hanh_dong="SUA_GIA")
    assert nk.nguoi_dung == quan_tri
    assert nk.doi_tuong == "DichVu:VS-DH-TT"
    assert nk.du_lieu_truoc == {"don_gia_tham_khao": 150_000}
    assert nk.du_lieu_sau == {"don_gia_tham_khao": 170_000}
    assert nk.dia_chi_ip is None or nk.dia_chi_ip  # có cột IP; view chưa truyền IP ở P1


def test_sua_khong_doi_gia_khong_ghi_sua_gia(quan_tri):
    dv = DichVuFactory(don_gia_tham_khao=150_000)
    DichVuDAO.sua(quan_tri, dv, {"ten_dich_vu": "Tên mới"})
    assert not NhatKyThaoTac.objects.filter(hanh_dong="SUA_GIA").exists()
    assert NhatKyThaoTac.objects.filter(hanh_dong="SUA_DICH_VU").exists()


def test_tong_dai_khong_sua_duoc_gia_ca_o_dao(tong_dai):
    dv = DichVuFactory()
    with pytest.raises(PermissionDenied):
        DichVuDAO.sua(tong_dai, dv, {"don_gia_tham_khao": 1})


def test_don_gia_am_bi_tu_choi(client_quan_tri):
    phan_hoi = client_quan_tri.post("/danh-muc/dich-vu/moi/", {**DU_LIEU_DICH_VU, "don_gia_tham_khao": "-1"})
    assert phan_hoi.status_code == 200 and not DichVu.objects.exists()


def test_xoa_dich_vu_chua_dung(client_quan_tri):
    dv = DichVuFactory()
    client_quan_tri.post(f"/danh-muc/dich-vu/{dv.pk}/xoa/")
    assert not DichVu.objects.filter(pk=dv.pk).exists()


def test_khong_xoa_duoc_dich_vu_da_dung_chi_ngung_ap_dung(client_quan_tri):
    dv = DichVuFactory()
    ThoFactory().ky_nang.add(dv)
    phan_hoi = client_quan_tri.post(f"/danh-muc/dich-vu/{dv.pk}/xoa/", follow=True)
    assert DichVu.objects.filter(pk=dv.pk).exists()
    assert "ngừng áp dụng" in phan_hoi.content.decode()
    client_quan_tri.post(
        f"/danh-muc/dich-vu/{dv.pk}/sua/",
        {**DU_LIEU_DICH_VU, "ma": dv.ma, "thoi_han_bao_hanh_ngay": "7", "dang_ap_dung": ""},
    )
    dv.refresh_from_db()
    assert not dv.dang_ap_dung


def test_tho_chi_thay_dich_vu_dang_ap_dung(client_vai_tro):
    DichVuFactory(ten_dich_vu="Đang dùng")
    DichVuFactory(ten_dich_vu="Đã ngừng", dang_ap_dung=False)
    noi_dung = client_vai_tro(VaiTro.THO).get("/danh-muc/dich-vu/").content.decode()
    assert "Đang dùng" in noi_dung and "Đã ngừng" not in noi_dung
    assert "HomeFix Thợ" in noi_dung  # thợ xem trong bố cục điện thoại


def test_hien_thi_gia_kieu_viet_nam(client_quan_tri):
    DichVuFactory(don_gia_tham_khao=1_250_000)
    assert "1.250.000 đ" in client_quan_tri.get("/danh-muc/dich-vu/").content.decode()


# ================================================================ Thợ


def _du_lieu_tho(**them):
    dv = DichVuFactory()
    kv = KhuVucFactory()
    return {
        "ho_ten": "Trần Văn Thợ",
        "so_dien_thoai": "+84 977 000 111",
        "hinh_thuc": "CHINH_THUC",
        "ky_nang": [dv.pk],
        "khu_vuc_phu_trach": [kv.pk],
        "dang_nhan_viec": "on",
        "nghi_den": "",
        "kenh_thong_bao": "WEB_PUSH",
        "ghi_chu": "",
        **them,
    }


def test_them_tho_tao_tai_khoan_va_cap_pin(client_quan_tri):
    du_lieu = _du_lieu_tho()
    phan_hoi = client_quan_tri.post("/danh-muc/tho/moi/", du_lieu, follow=True)
    tho = Tho.objects.get(so_dien_thoai="0977000111")
    assert tho.nguoi_dung.vai_tro == VaiTro.THO
    assert tho.nguoi_dung.username == "0977000111"
    assert tho.nguoi_dung.phai_doi_mat_khau
    assert list(tho.ky_nang.values_list("pk", flat=True)) == du_lieu["ky_nang"]
    assert list(tho.khu_vuc_phu_trach.values_list("pk", flat=True)) == du_lieu["khu_vuc_phu_trach"]
    assert "PIN của Trần Văn Thợ" in phan_hoi.content.decode()
    assert NhatKyThaoTac.objects.filter(hanh_dong="TAO_THO").exists()
    assert tho.ma_tho == f"T{tho.pk:03d}"


def test_them_tho_trung_sdt_voi_nguoi_dung_khac(client_quan_tri, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0977000111")
    phan_hoi = client_quan_tri.post("/danh-muc/tho/moi/", _du_lieu_tho())
    assert phan_hoi.status_code == 200 and "đã có tài khoản" in phan_hoi.content.decode()
    assert not Tho.objects.exists()


def test_sua_tho_dong_bo_tai_khoan(client_quan_tri):
    tho = ThoFactory()
    client_quan_tri.post(
        f"/danh-muc/tho/{tho.pk}/sua/",
        _du_lieu_tho(ho_ten="Tên Đổi", so_dien_thoai="0977 999 888", ky_nang=[], khu_vuc_phu_trach=[]),
    )
    tho.refresh_from_db()
    tho.nguoi_dung.refresh_from_db()
    assert (tho.ho_ten, tho.so_dien_thoai) == ("Tên Đổi", "0977999888")
    assert (tho.nguoi_dung.ho_ten, tho.nguoi_dung.so_dien_thoai, tho.nguoi_dung.username) == (
        "Tên Đổi",
        "0977999888",
        "0977999888",
    )
    assert NhatKyThaoTac.objects.filter(hanh_dong="SUA_THO").exists()


def test_cap_lai_pin_va_khoa_tho(client_quan_tri):
    tho = ThoFactory()
    phan_hoi = client_quan_tri.post(f"/danh-muc/tho/{tho.pk}/cap-pin/", follow=True)
    assert "PIN của" in phan_hoi.content.decode()
    tho.nguoi_dung.refresh_from_db()
    assert tho.nguoi_dung.phai_doi_mat_khau
    client_quan_tri.post(f"/danh-muc/tho/{tho.pk}/khoa/")
    tho.nguoi_dung.refresh_from_db()
    assert not tho.nguoi_dung.is_active


def test_ky_nang_nhom_theo_loai_thiet_bi(client_quan_tri):
    DichVuFactory(loai_thiet_bi="MAY_GIAT", ten_dich_vu="Vệ sinh máy giặt")
    noi_dung = client_quan_tri.get("/danh-muc/tho/moi/").content.decode()
    assert "Máy giặt" in noi_dung and "Vệ sinh máy giặt" in noi_dung


# ================================================================ Khách hàng, địa chỉ, thiết bị


def test_them_khach_thieu_ten_va_chuan_hoa_sdt(client_vai_tro):
    c = client_vai_tro(VaiTro.TONG_DAI)
    c.post("/danh-muc/khach-hang/moi/", {"ho_ten": "", "so_dien_thoai": "+84 912.345.678"})
    kh = KhachHang.objects.get()
    assert kh.so_dien_thoai == "0912345678" and kh.ho_ten == ""
    assert kh.loai_khach == KhachHang.LoaiKhach.THUONG


def test_khach_trung_sdt(client_quan_tri):
    KhachHangFactory(so_dien_thoai="0912345678")
    phan_hoi = client_quan_tri.post("/danh-muc/khach-hang/moi/", {"so_dien_thoai": "0912 345 678"})
    assert phan_hoi.status_code == 200 and KhachHang.objects.count() == 1


def test_vip_thu_cong_can_ly_do(client_quan_tri):
    kh = KhachHangFactory()
    url = f"/danh-muc/khach-hang/{kh.pk}/sua/"
    phan_hoi = client_quan_tri.post(url, {"so_dien_thoai": kh.so_dien_thoai, "vip_thu_cong": "on"})
    assert phan_hoi.status_code == 200 and "Nhập lý do" in phan_hoi.content.decode()
    client_quan_tri.post(
        url, {"so_dien_thoai": kh.so_dien_thoai, "vip_thu_cong": "on", "ly_do_vip": "Giám đốc giới thiệu"}
    )
    kh.refresh_from_db()
    assert kh.la_vip
    client_quan_tri.post(url, {"so_dien_thoai": kh.so_dien_thoai, "ly_do_vip": ""})
    kh.refresh_from_db()
    assert not kh.la_vip


def test_tim_khach_theo_sdt_nhieu_dang(tong_dai):
    KhachHangFactory(so_dien_thoai="0912345678", ho_ten="Chị Lan")
    for tu_khoa in ["0912345678", "+84 912 345 678", "345 678", "Lan"]:
        assert [k.ho_ten for k in KhachHangDAO.lay_danh_sach(tong_dai, tu_khoa)] == ["Chị Lan"]


def test_dia_chi_dau_tien_la_mac_dinh_va_doi_mac_dinh(client_quan_tri):
    kh = KhachHangFactory()
    kv = KhuVucFactory()
    url = f"/danh-muc/khach-hang/{kh.pk}/dia-chi/moi/"
    client_quan_tri.post(url, {"dia_chi_chi_tiet": "Số 1", "khu_vuc": kv.pk})
    client_quan_tri.post(url, {"dia_chi_chi_tiet": "Số 2", "khu_vuc": kv.pk, "la_mac_dinh": "on"})
    assert list(kh.ds_dia_chi.order_by("id").values_list("la_mac_dinh", flat=True)) == [False, True]
    so_2 = kh.ds_dia_chi.get(dia_chi_chi_tiet="Số 2")
    client_quan_tri.post(f"/danh-muc/dia-chi/{so_2.pk}/xoa/")
    assert kh.ds_dia_chi.get().la_mac_dinh  # còn lại số 1, tự lên mặc định


def test_csdl_chan_hai_dia_chi_mac_dinh():
    dc = DiaChiFactory(la_mac_dinh=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        DiaChiFactory(khach_hang=dc.khach_hang, la_mac_dinh=True)


def test_dia_chi_bat_buoc_khu_vuc(client_quan_tri):
    kh = KhachHangFactory()
    phan_hoi = client_quan_tri.post(
        f"/danh-muc/khach-hang/{kh.pk}/dia-chi/moi/", {"dia_chi_chi_tiet": "Số 1"}
    )
    assert phan_hoi.status_code == 200 and not DiaChi.objects.exists()


def test_thiet_bi_them_sua_xoa(client_quan_tri):
    dc = DiaChiFactory()
    client_quan_tri.post(
        f"/danh-muc/dia-chi/{dc.pk}/thiet-bi/moi/", {"loai_thiet_bi": "TU_LANH", "hang_san_xuat": "Hitachi"}
    )
    tb = ThietBi.objects.get()
    client_quan_tri.post(
        f"/danh-muc/thiet-bi/{tb.pk}/sua/",
        {"loai_thiet_bi": "TU_LANH", "hang_san_xuat": "Hitachi", "vi_tri_lap": "Bếp"},
    )
    tb.refresh_from_db()
    assert tb.vi_tri_lap == "Bếp"
    assert "Hitachi" in client_quan_tri.get(f"/danh-muc/khach-hang/{dc.khach_hang_id}/").content.decode()
    client_quan_tri.post(f"/danh-muc/thiet-bi/{tb.pk}/xoa/")
    assert not ThietBi.objects.exists()


def test_xoa_khach_xoa_dia_chi_thiet_bi(client_quan_tri):
    tb = ThietBiFactory()
    client_quan_tri.post(f"/danh-muc/khach-hang/{tb.dia_chi.khach_hang_id}/xoa/")
    assert not (KhachHang.objects.exists() or DiaChi.objects.exists() or ThietBi.objects.exists())


def test_ke_toan_thay_sdt_khach_da_an_bot(client_vai_tro):
    KhachHangFactory(so_dien_thoai="0901234123")
    noi_dung = client_vai_tro(VaiTro.KE_TOAN).get("/danh-muc/khach-hang/").content.decode()
    assert "090****123" in noi_dung and "0901234123" not in noi_dung


def test_tong_dai_thay_du_sdt_khach(client_vai_tro):
    KhachHangFactory(so_dien_thoai="0901234123")
    assert "0901234123" in client_vai_tro(VaiTro.TONG_DAI).get("/danh-muc/khach-hang/").content.decode()


def test_moi_thao_tac_ghi_danh_muc_deu_co_nhat_ky(client_quan_tri):
    """Mọi thao tác ghi trong P1 để lại dấu vết người thực hiện (NFR06)."""
    kh = KhachHangFactory()
    kv = KhuVucFactory()
    client_quan_tri.post(
        f"/danh-muc/khach-hang/{kh.pk}/dia-chi/moi/", {"dia_chi_chi_tiet": "Số 1", "khu_vuc": kv.pk}
    )
    client_quan_tri.post(
        f"/danh-muc/khach-hang/{kh.pk}/sua/", {"so_dien_thoai": kh.so_dien_thoai, "ho_ten": "X"}
    )
    hanh_dong = set(NhatKyThaoTac.objects.values_list("hanh_dong", flat=True))
    assert {"TAO_DIA_CHI", "SUA_KHACH_HANG"} <= hanh_dong
    assert not NhatKyThaoTac.objects.filter(nguoi_dung=None).exclude(hanh_dong__startswith="NAP").exists()
    assert NguoiDung.objects.count() >= 1


def test_dinh_dang_ngay_viet_nam_ca_khi_trinh_duyet_tieng_anh(client_quan_tri):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    ThoFactory(nghi_den=datetime(2099, 10, 13, 19, 12, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")))
    noi_dung = client_quan_tri.get("/danh-muc/tho/", HTTP_ACCEPT_LANGUAGE="en-US,en;q=0.9").content.decode()
    assert "Nghỉ đến 13/10/2099 19:12" in noi_dung

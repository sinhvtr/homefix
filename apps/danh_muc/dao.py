"""DAO danh mục (UC13). Mọi phương thức ghi: kiểm quyền, transaction.atomic(), ghi nhật ký."""

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Count, ProtectedError, Q, RestrictedError

from apps.he_thong.cau_hinh import cau_hinh
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.he_thong.so_dien_thoai import chuan_hoa_sdt
from apps.tai_khoan.dao import NguoiDungDAO
from apps.tai_khoan.mat_khau import sinh_pin
from apps.tai_khoan.models import VaiTro
from apps.tai_khoan.phan_quyen import CHI_QUAN_TRI, GHI_KHACH_HANG, MOI_VAI_TRO, VAN_PHONG, kiem_tra_vai_tro

from .models import DiaChi, DichVu, KhachHang, KhuVuc, ThietBi, Tho


def _anh_chup(doi_tuong, truong) -> dict:
    du_lieu = {}
    for ten in truong:
        gia_tri = getattr(doi_tuong, ten)
        if hasattr(gia_tri, "all"):  # ManyToMany → danh sách mã/khóa
            gia_tri = sorted(getattr(x, "ma", x.pk) for x in gia_tri.all())
        elif hasattr(gia_tri, "pk"):
            gia_tri = gia_tri.pk
        du_lieu[ten] = gia_tri
    return du_lieu


def _gan(doi_tuong, du_lieu: dict) -> None:
    for ten, gia_tri in du_lieu.items():
        setattr(doi_tuong, ten, gia_tri)


def _xoa(nguoi_dung, doi_tuong, hanh_dong: str, truong, thong_bao_dang_dung: str) -> None:
    truoc = _anh_chup(doi_tuong, truong)
    try:
        with transaction.atomic():
            ten = f"{type(doi_tuong).__name__}:{getattr(doi_tuong, 'ma', None) or doi_tuong.pk}"
            doi_tuong.delete()
            ghi_nhat_ky(nguoi_dung, hanh_dong, ten, du_lieu_truoc=truoc)
    except (ProtectedError, RestrictedError) as loi:
        raise ValidationError(thong_bao_dang_dung, code="dang_duoc_dung") from loi


# ---------------------------------------------------------------- Khu vực

TRUONG_KHU_VUC = ("ma", "ten", "ghi_chu")


class KhuVucDAO:
    @staticmethod
    def lay_danh_sach(nguoi_dung):
        kiem_tra_vai_tro(nguoi_dung, *VAN_PHONG)
        return KhuVuc.objects.annotate(so_tho=Count("ds_tho", distinct=True)).order_by("ten")

    @staticmethod
    def tao(nguoi_dung, du_lieu: dict) -> KhuVuc:
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        with transaction.atomic():
            kv = KhuVuc.objects.create(**du_lieu)
            ghi_nhat_ky(nguoi_dung, "TAO_KHU_VUC", kv, du_lieu_sau=_anh_chup(kv, TRUONG_KHU_VUC))
        return kv

    @staticmethod
    def sua(nguoi_dung, kv: KhuVuc, du_lieu: dict) -> KhuVuc:
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        with transaction.atomic():
            kv = KhuVuc.objects.select_for_update().get(pk=kv.pk)
            truoc = _anh_chup(kv, TRUONG_KHU_VUC)
            _gan(kv, du_lieu)
            kv.save()
            ghi_nhat_ky(nguoi_dung, "SUA_KHU_VUC", kv, truoc, _anh_chup(kv, TRUONG_KHU_VUC))
        return kv

    @staticmethod
    def xoa(nguoi_dung, kv: KhuVuc) -> None:
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        if kv.ds_tho.exists():
            raise ValidationError("Khu vực đang được thợ phụ trách, không xóa được.", code="dang_duoc_dung")
        _xoa(
            nguoi_dung, kv, "XOA_KHU_VUC", TRUONG_KHU_VUC, "Khu vực đã có địa chỉ khách hàng, không xóa được."
        )


# ---------------------------------------------------------------- Dịch vụ, bảng giá

TRUONG_DICH_VU = (
    "ma",
    "ten_dich_vu",
    "nhom_dich_vu",
    "loai_thiet_bi",
    "don_gia_tham_khao",
    "don_vi_tinh",
    "thoi_han_bao_hanh_ngay",
    "dang_ap_dung",
)


def bao_hanh_mac_dinh(nhom_dich_vu: str) -> int:
    """BR05: 7 ngày (vệ sinh) / 90 ngày (sửa chữa) — đọc từ CauHinh."""
    if nhom_dich_vu == DichVu.NhomDichVu.VE_SINH_BAO_DUONG:
        return cau_hinh("BAO_HANH_VE_SINH_NGAY")
    return cau_hinh("BAO_HANH_SUA_CHUA_NGAY")


class DichVuDAO:
    @staticmethod
    def lay_danh_sach(nguoi_dung, tu_khoa: str = "", loai_thiet_bi: str = "", chi_dang_ap_dung=False):
        kiem_tra_vai_tro(nguoi_dung, *MOI_VAI_TRO)
        qs = DichVu.objects.all()
        if nguoi_dung.vai_tro == VaiTro.THO or chi_dang_ap_dung:
            qs = qs.filter(dang_ap_dung=True)
        if tu_khoa:
            qs = qs.filter(Q(ten_dich_vu__icontains=tu_khoa) | Q(ma__icontains=tu_khoa))
        if loai_thiet_bi:
            qs = qs.filter(loai_thiet_bi=loai_thiet_bi)
        return qs

    @staticmethod
    def da_duoc_dung(dv: DichVu) -> bool:
        """Đã dùng = có thợ mang kỹ năng này (từ P2: hoặc có đơn/hạng mục tham chiếu — chặn bằng PROTECT)."""
        return dv.ds_tho.exists()

    @staticmethod
    def tao(nguoi_dung, du_lieu: dict) -> DichVu:
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        du_lieu = dict(du_lieu)
        if du_lieu.get("thoi_han_bao_hanh_ngay") in (None, ""):
            du_lieu["thoi_han_bao_hanh_ngay"] = bao_hanh_mac_dinh(du_lieu["nhom_dich_vu"])
        with transaction.atomic():
            dv = DichVu.objects.create(**du_lieu)
            ghi_nhat_ky(nguoi_dung, "TAO_DICH_VU", dv, du_lieu_sau=_anh_chup(dv, TRUONG_DICH_VU))
        return dv

    @staticmethod
    def sua(nguoi_dung, dv: DichVu, du_lieu: dict) -> DichVu:
        """Sửa dịch vụ. Đổi đơn giá ghi riêng hành động SUA_GIA (NFR06)."""
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        du_lieu = dict(du_lieu)
        if du_lieu.get("thoi_han_bao_hanh_ngay") in (None, ""):
            du_lieu["thoi_han_bao_hanh_ngay"] = bao_hanh_mac_dinh(
                du_lieu.get("nhom_dich_vu", dv.nhom_dich_vu)
            )
        with transaction.atomic():
            dv = DichVu.objects.select_for_update().get(pk=dv.pk)
            truoc = _anh_chup(dv, TRUONG_DICH_VU)
            _gan(dv, du_lieu)
            dv.save()
            sau = _anh_chup(dv, TRUONG_DICH_VU)
            if truoc["don_gia_tham_khao"] != sau["don_gia_tham_khao"]:
                ghi_nhat_ky(
                    nguoi_dung,
                    "SUA_GIA",
                    dv,
                    {"don_gia_tham_khao": truoc["don_gia_tham_khao"]},
                    {"don_gia_tham_khao": sau["don_gia_tham_khao"]},
                )
            if {k: v for k, v in truoc.items() if k != "don_gia_tham_khao"} != {
                k: v for k, v in sau.items() if k != "don_gia_tham_khao"
            }:
                ghi_nhat_ky(nguoi_dung, "SUA_DICH_VU", dv, truoc, sau)
        return dv

    @staticmethod
    def xoa(nguoi_dung, dv: DichVu) -> None:
        """Không xóa dịch vụ đã dùng, chỉ ngừng áp dụng (UC13)."""
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        thong_bao = "Dịch vụ đã được dùng, không xóa được — hãy bỏ chọn “Đang áp dụng” để ngừng áp dụng."
        if DichVuDAO.da_duoc_dung(dv):
            raise ValidationError(thong_bao, code="dang_duoc_dung")
        _xoa(nguoi_dung, dv, "XOA_DICH_VU", TRUONG_DICH_VU, thong_bao)


# ---------------------------------------------------------------- Thợ

TRUONG_THO = (
    "ho_ten",
    "so_dien_thoai",
    "hinh_thuc",
    "ky_nang",
    "khu_vuc_phu_trach",
    "dang_nhan_viec",
    "nghi_den",
    "kenh_thong_bao",
    "ghi_chu",
)


class ThoDAO:
    @staticmethod
    def lay_danh_sach(nguoi_dung, tu_khoa: str = ""):
        kiem_tra_vai_tro(nguoi_dung, *VAN_PHONG)
        qs = Tho.objects.select_related("nguoi_dung").prefetch_related("ky_nang", "khu_vuc_phu_trach")
        if tu_khoa:
            qs = qs.filter(Q(ho_ten__icontains=tu_khoa) | Q(so_dien_thoai__contains=tu_khoa))
        return qs.order_by("ho_ten")

    @staticmethod
    def lay_chi_tiet(nguoi_dung, pk) -> Tho:
        kiem_tra_vai_tro(nguoi_dung, *VAN_PHONG)
        return (
            Tho.objects.select_related("nguoi_dung")
            .prefetch_related("ky_nang", "khu_vuc_phu_trach")
            .get(pk=pk)
        )

    @staticmethod
    def tao(nguoi_dung, du_lieu: dict) -> tuple[Tho, str]:
        """Tạo tài khoản THO + hồ sơ thợ. Trả (thợ, PIN) — PIN chỉ hiện một lần, bắt buộc đổi lần đầu."""
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        du_lieu = dict(du_lieu)
        ky_nang = du_lieu.pop("ky_nang", [])
        khu_vuc = du_lieu.pop("khu_vuc_phu_trach", [])
        pin = sinh_pin()
        with transaction.atomic():
            tai_khoan = NguoiDungDAO._tao(
                du_lieu["ho_ten"], du_lieu["so_dien_thoai"], VaiTro.THO, pin, True, nguoi_dung
            )
            du_lieu["ho_ten"] = tai_khoan.ho_ten
            du_lieu["so_dien_thoai"] = tai_khoan.so_dien_thoai
            tho = Tho.objects.create(nguoi_dung=tai_khoan, **du_lieu)
            tho.ky_nang.set(ky_nang)
            tho.khu_vuc_phu_trach.set(khu_vuc)
            ghi_nhat_ky(nguoi_dung, "TAO_THO", tho, du_lieu_sau=_anh_chup(tho, TRUONG_THO))
        return tho, pin

    @staticmethod
    def sua(nguoi_dung, tho: Tho, du_lieu: dict) -> Tho:
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        du_lieu = dict(du_lieu)
        ky_nang = du_lieu.pop("ky_nang", None)
        khu_vuc = du_lieu.pop("khu_vuc_phu_trach", None)
        with transaction.atomic():
            tho = Tho.objects.select_for_update().select_related("nguoi_dung").get(pk=tho.pk)
            truoc = _anh_chup(tho, TRUONG_THO)
            sdt = chuan_hoa_sdt(du_lieu.get("so_dien_thoai", tho.so_dien_thoai))
            ho_ten = (du_lieu.get("ho_ten") or tho.ho_ten).strip()
            if sdt != tho.so_dien_thoai or ho_ten != tho.ho_ten:
                NguoiDungDAO.cap_nhat(nguoi_dung, tho.nguoi_dung, ho_ten, sdt, VaiTro.THO)
            du_lieu.update(ho_ten=ho_ten, so_dien_thoai=sdt)
            _gan(tho, du_lieu)
            tho.save()
            if ky_nang is not None:
                tho.ky_nang.set(ky_nang)
            if khu_vuc is not None:
                tho.khu_vuc_phu_trach.set(khu_vuc)
            ghi_nhat_ky(nguoi_dung, "SUA_THO", tho, truoc, _anh_chup(tho, TRUONG_THO))
        return tho

    @staticmethod
    def cap_nhat_cua_toi(nguoi_dung, **du_lieu) -> Tho:
        """Thợ tự sửa phần được phép của hồ sơ mình (SPEC 3.1: kênh thông báo; UC07: “Sẵn sàng nhận việc”)."""
        kiem_tra_vai_tro(nguoi_dung, VaiTro.THO)
        duoc_sua = {"dang_nhan_viec", "kenh_thong_bao"}
        if set(du_lieu) - duoc_sua:
            raise ValidationError("Không được sửa trường này.")
        if "kenh_thong_bao" in du_lieu and du_lieu["kenh_thong_bao"] not in Tho.KenhThongBao.values:
            raise ValidationError({"kenh_thong_bao": "Kênh không hợp lệ."})
        with transaction.atomic():
            tho = Tho.objects.select_for_update().get(nguoi_dung=nguoi_dung)
            truoc = _anh_chup(tho, tuple(du_lieu))
            _gan(tho, du_lieu)
            tho.save(update_fields=[*du_lieu, "cap_nhat_luc"])
            ghi_nhat_ky(nguoi_dung, "THO_CAP_NHAT", tho, truoc, _anh_chup(tho, tuple(du_lieu)))
        return tho

    @staticmethod
    def cap_lai_pin(nguoi_dung, tho: Tho) -> str:
        return NguoiDungDAO.dat_lai_mat_khau(nguoi_dung, tho.nguoi_dung)

    @staticmethod
    def dat_khoa(nguoi_dung, tho: Tho, khoa: bool) -> None:
        NguoiDungDAO.dat_khoa(nguoi_dung, tho.nguoi_dung, khoa)


# ---------------------------------------------------------------- Khách hàng, địa chỉ, thiết bị

TRUONG_KHACH = (
    "ho_ten",
    "so_dien_thoai",
    "so_dien_thoai_phu",
    "loai_khach",
    "vip_thu_cong",
    "ly_do_vip",
    "ghi_chu",
)
TRUONG_DIA_CHI = ("khach_hang", "dia_chi_chi_tiet", "khu_vuc", "ghi_chu_duong_di", "la_mac_dinh")
TRUONG_THIET_BI = ("dia_chi", "loai_thiet_bi", "hang_san_xuat", "model", "vi_tri_lap", "ghi_chu")


def _ap_vip_thu_cong(kh: KhachHang, vip_thu_cong_truoc: bool = False) -> None:
    """VIP thủ công (giám đốc giới thiệu) → VIP bất kể số lần dùng (BR07); bắt buộc có lý do.
    Bỏ VIP thủ công → về THUONG; tác vụ đêm cap_nhat_khach_vip (BR07) sẽ xét lại theo số đơn."""
    if kh.vip_thu_cong:
        if not (kh.ly_do_vip or "").strip():
            raise ValidationError(
                {"ly_do_vip": "Nhập lý do khi đánh dấu VIP thủ công."}, code="thieu_ly_do_vip"
            )
        kh.loai_khach = KhachHang.LoaiKhach.VIP
    elif vip_thu_cong_truoc:
        kh.loai_khach = KhachHang.LoaiKhach.THUONG


class KhachHangDAO:
    @staticmethod
    def lay_danh_sach(nguoi_dung, tu_khoa: str = ""):
        kiem_tra_vai_tro(nguoi_dung, *VAN_PHONG)
        qs = KhachHang.objects.annotate(so_dia_chi=Count("ds_dia_chi"))
        if tu_khoa:
            so = "".join(c for c in tu_khoa if c.isdigit())
            dieu_kien = Q(ho_ten__icontains=tu_khoa)
            if so:
                if so.startswith("84") and len(so) == 11:
                    so = "0" + so[2:]
                dieu_kien |= Q(so_dien_thoai__contains=so) | Q(so_dien_thoai_phu__contains=so)
            qs = qs.filter(dieu_kien)
        return qs.order_by("-loai_khach", "-tao_luc")

    @staticmethod
    def lay_chi_tiet(nguoi_dung, pk) -> KhachHang:
        kiem_tra_vai_tro(nguoi_dung, *VAN_PHONG)
        return KhachHang.objects.prefetch_related("ds_dia_chi__khu_vuc", "ds_dia_chi__ds_thiet_bi").get(pk=pk)

    @staticmethod
    def tra_cuu_theo_sdt(nguoi_dung, so_dien_thoai: str) -> KhachHang | None:
        """UC02 bước 1: khách theo SĐT (chính hoặc phụ) kèm địa chỉ, thiết bị và 5 đơn gần nhất (`don_gan_nhat`)."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_KHACH_HANG)
        sdt = chuan_hoa_sdt(so_dien_thoai)
        kh = (
            KhachHang.objects.filter(Q(so_dien_thoai=sdt) | Q(so_dien_thoai_phu=sdt))
            .prefetch_related("ds_dia_chi__khu_vuc", "ds_dia_chi__ds_thiet_bi")
            .order_by(models.Case(models.When(so_dien_thoai=sdt, then=0), default=1))
            .first()
        )
        if kh is not None:
            # DonSuaChua thuộc gói lõi (tầng trên) — đọc qua quan hệ ngược, không import.
            kh.don_gan_nhat = list(
                kh.ds_don.select_related("dich_vu_yeu_cau", "dia_chi", "phieu_bao_hanh").order_by(
                    "-ngay_tiep_nhan"
                )[:5]
            )
        return kh

    @staticmethod
    def kiem_tra_trung_sdt(sdt: str, tru_pk=None) -> None:
        qs = KhachHang.objects.filter(so_dien_thoai=sdt)
        if tru_pk:
            qs = qs.exclude(pk=tru_pk)
        if qs.exists():
            raise ValidationError({"so_dien_thoai": f"Đã có khách hàng số {sdt}."}, code="trung_sdt")

    @staticmethod
    def tao(nguoi_dung, du_lieu: dict) -> KhachHang:
        kiem_tra_vai_tro(nguoi_dung, *GHI_KHACH_HANG)
        kh = KhachHang(**du_lieu)
        kh.so_dien_thoai = chuan_hoa_sdt(kh.so_dien_thoai)
        _ap_vip_thu_cong(kh)
        with transaction.atomic():
            KhachHangDAO.kiem_tra_trung_sdt(kh.so_dien_thoai)
            kh.save()
            ghi_nhat_ky(nguoi_dung, "TAO_KHACH_HANG", kh, du_lieu_sau=_anh_chup(kh, TRUONG_KHACH))
        return kh

    @staticmethod
    def sua(nguoi_dung, kh: KhachHang, du_lieu: dict) -> KhachHang:
        kiem_tra_vai_tro(nguoi_dung, *GHI_KHACH_HANG)
        with transaction.atomic():
            kh = KhachHang.objects.select_for_update().get(pk=kh.pk)
            truoc = _anh_chup(kh, TRUONG_KHACH)
            _gan(kh, du_lieu)
            kh.so_dien_thoai = chuan_hoa_sdt(kh.so_dien_thoai)
            _ap_vip_thu_cong(kh, vip_thu_cong_truoc=truoc["vip_thu_cong"])
            KhachHangDAO.kiem_tra_trung_sdt(kh.so_dien_thoai, tru_pk=kh.pk)
            kh.save()
            ghi_nhat_ky(nguoi_dung, "SUA_KHACH_HANG", kh, truoc, _anh_chup(kh, TRUONG_KHACH))
        return kh

    @staticmethod
    def xoa(nguoi_dung, kh: KhachHang) -> None:
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        _xoa(nguoi_dung, kh, "XOA_KHACH_HANG", TRUONG_KHACH, "Khách hàng đã có đơn, không xóa được.")


class DiaChiDAO:
    @staticmethod
    def _dat_mac_dinh(dc: DiaChi) -> None:
        DiaChi.objects.filter(khach_hang=dc.khach_hang, la_mac_dinh=True).exclude(pk=dc.pk).update(
            la_mac_dinh=False
        )

    @staticmethod
    def tao(nguoi_dung, kh: KhachHang, du_lieu: dict) -> DiaChi:
        kiem_tra_vai_tro(nguoi_dung, *GHI_KHACH_HANG)
        with transaction.atomic():
            KhachHang.objects.select_for_update().get(pk=kh.pk)
            dc = DiaChi(khach_hang=kh, **du_lieu)
            if not kh.ds_dia_chi.exists():
                dc.la_mac_dinh = True  # địa chỉ đầu tiên là mặc định
            if dc.la_mac_dinh:
                DiaChi.objects.filter(khach_hang=kh, la_mac_dinh=True).update(la_mac_dinh=False)
            dc.save()
            ghi_nhat_ky(nguoi_dung, "TAO_DIA_CHI", dc, du_lieu_sau=_anh_chup(dc, TRUONG_DIA_CHI))
        return dc

    @staticmethod
    def sua(nguoi_dung, dc: DiaChi, du_lieu: dict) -> DiaChi:
        kiem_tra_vai_tro(nguoi_dung, *GHI_KHACH_HANG)
        with transaction.atomic():
            KhachHang.objects.select_for_update().get(pk=dc.khach_hang_id)
            dc = DiaChi.objects.get(pk=dc.pk)
            truoc = _anh_chup(dc, TRUONG_DIA_CHI)
            _gan(dc, du_lieu)
            if dc.la_mac_dinh:
                DiaChiDAO._dat_mac_dinh(dc)
            elif truoc["la_mac_dinh"]:
                dc.la_mac_dinh = True  # luôn giữ một địa chỉ mặc định; đổi bằng cách chọn địa chỉ khác
            dc.save()
            ghi_nhat_ky(nguoi_dung, "SUA_DIA_CHI", dc, truoc, _anh_chup(dc, TRUONG_DIA_CHI))
        return dc

    @staticmethod
    def xoa(nguoi_dung, dc: DiaChi) -> None:
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        kh = dc.khach_hang
        with transaction.atomic():
            la_mac_dinh = dc.la_mac_dinh
            _xoa(nguoi_dung, dc, "XOA_DIA_CHI", TRUONG_DIA_CHI, "Địa chỉ đã có đơn, không xóa được.")
            if la_mac_dinh:
                con_lai = kh.ds_dia_chi.order_by("id").first()
                if con_lai:
                    con_lai.la_mac_dinh = True
                    con_lai.save(update_fields=["la_mac_dinh", "cap_nhat_luc"])


class ThietBiDAO:
    @staticmethod
    def tao(nguoi_dung, dc: DiaChi, du_lieu: dict) -> ThietBi:
        kiem_tra_vai_tro(nguoi_dung, *GHI_KHACH_HANG)
        with transaction.atomic():
            tb = ThietBi.objects.create(dia_chi=dc, **du_lieu)
            ghi_nhat_ky(nguoi_dung, "TAO_THIET_BI", tb, du_lieu_sau=_anh_chup(tb, TRUONG_THIET_BI))
        return tb

    @staticmethod
    def sua(nguoi_dung, tb: ThietBi, du_lieu: dict) -> ThietBi:
        kiem_tra_vai_tro(nguoi_dung, *GHI_KHACH_HANG)
        with transaction.atomic():
            tb = ThietBi.objects.select_for_update().get(pk=tb.pk)
            truoc = _anh_chup(tb, TRUONG_THIET_BI)
            _gan(tb, du_lieu)
            tb.save()
            ghi_nhat_ky(nguoi_dung, "SUA_THIET_BI", tb, truoc, _anh_chup(tb, TRUONG_THIET_BI))
        return tb

    @staticmethod
    def xoa(nguoi_dung, tb: ThietBi) -> None:
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        _xoa(nguoi_dung, tb, "XOA_THIET_BI", TRUONG_THIET_BI, "Thiết bị đã có trong đơn, không xóa được.")

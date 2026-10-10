from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.he_thong.cau_hinh import chuyen_doi
from apps.he_thong.models import CauHinh
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.he_thong.so_dien_thoai import chuan_hoa_sdt

from .mat_khau import kiem_tra_mat_khau_moi, sinh_bi_mat
from .models import NguoiDung, VaiTro
from .phan_quyen import CHI_QUAN_TRI, QUAN_TRI_GIAM_DOC, kiem_tra_vai_tro

TRUONG_NHAT_KY_NGUOI_DUNG = ("ho_ten", "so_dien_thoai", "vai_tro", "is_active")


def anh_chup(doi_tuong, truong) -> dict:
    return {t: getattr(doi_tuong, t) for t in truong}


class NguoiDungDAO:
    @staticmethod
    def lay_danh_sach(nguoi_dung, tu_khoa: str = ""):
        kiem_tra_vai_tro(nguoi_dung, *QUAN_TRI_GIAM_DOC)
        qs = NguoiDung.objects.order_by("vai_tro", "ho_ten")
        if tu_khoa:
            qs = qs.filter(ho_ten__icontains=tu_khoa) | qs.filter(so_dien_thoai__contains=tu_khoa)
        return qs

    @staticmethod
    def kiem_tra_trung_sdt(sdt: str, tru_pk=None) -> None:
        qs = NguoiDung.objects.filter(so_dien_thoai=sdt) | NguoiDung.objects.filter(username=sdt)
        if tru_pk is not None:
            qs = qs.exclude(pk=tru_pk)
        if qs.exists():
            raise ValidationError(
                {"so_dien_thoai": f"Số điện thoại {sdt} đã có tài khoản."}, code="trung_sdt"
            )

    @staticmethod
    def _tao(ho_ten, so_dien_thoai, vai_tro, mat_khau, phai_doi_mat_khau, nguoi_thuc_hien) -> NguoiDung:
        """Phần lõi, gọi bên trong transaction.atomic() của bên gọi (cả ThoDAO dùng)."""
        ho_ten = (ho_ten or "").strip()
        if not ho_ten:
            raise ValidationError({"ho_ten": "Họ tên không được để trống."}, code="thieu_ho_ten")
        sdt = chuan_hoa_sdt(so_dien_thoai)
        NguoiDungDAO.kiem_tra_trung_sdt(sdt)
        moi = NguoiDung(
            username=sdt,
            ho_ten=ho_ten,
            so_dien_thoai=sdt,
            vai_tro=vai_tro,
            phai_doi_mat_khau=phai_doi_mat_khau,
        )
        moi.set_password(mat_khau)
        moi.save()
        ghi_nhat_ky(
            nguoi_thuc_hien, "TAO_NGUOI_DUNG", moi, du_lieu_sau=anh_chup(moi, TRUONG_NHAT_KY_NGUOI_DUNG)
        )
        return moi

    @staticmethod
    def tao_quan_tri(ho_ten: str, so_dien_thoai: str, mat_khau: str, nguoi_dung=None) -> NguoiDung:
        """Lệnh tao_quan_tri: tạo tài khoản QUAN_TRI đầu tiên; tên đăng nhập = số điện thoại."""
        mau = NguoiDung(username=so_dien_thoai, ho_ten=ho_ten, vai_tro=VaiTro.QUAN_TRI)
        validate_password(mat_khau, mau)
        with transaction.atomic():
            try:
                return NguoiDungDAO._tao(ho_ten, so_dien_thoai, VaiTro.QUAN_TRI, mat_khau, False, nguoi_dung)
            except ValidationError as loi:
                # Lệnh dòng lệnh cần thông điệp phẳng
                raise ValidationError(loi.messages) from loi

    @staticmethod
    def tao_nguoi_dung(nguoi_dung, ho_ten: str, so_dien_thoai: str, vai_tro: str) -> tuple[NguoiDung, str]:
        """Quản trị tạo tài khoản văn phòng. Trả (người dùng, mật khẩu tạm) — mật khẩu chỉ hiện một lần."""
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        if vai_tro == VaiTro.THO:
            raise ValidationError({"vai_tro": "Tạo thợ ở Danh mục → Thợ."}, code="tao_tho_o_danh_muc")
        mat_khau = sinh_bi_mat(vai_tro)
        with transaction.atomic():
            moi = NguoiDungDAO._tao(ho_ten, so_dien_thoai, vai_tro, mat_khau, True, nguoi_dung)
        return moi, mat_khau

    @staticmethod
    def cap_nhat(
        nguoi_dung, doi_tuong: NguoiDung, ho_ten: str, so_dien_thoai: str, vai_tro: str
    ) -> NguoiDung:
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        if VaiTro.THO in (vai_tro, doi_tuong.vai_tro) and vai_tro != doi_tuong.vai_tro:
            raise ValidationError({"vai_tro": "Không đổi vai trò thợ ↔ văn phòng."}, code="doi_vai_tro_tho")
        if doi_tuong.pk == nguoi_dung.pk and vai_tro != doi_tuong.vai_tro:
            raise ValidationError({"vai_tro": "Không tự đổi vai trò của chính mình."}, code="tu_doi_vai_tro")
        sdt = chuan_hoa_sdt(so_dien_thoai)
        with transaction.atomic():
            doi_tuong = NguoiDung.objects.select_for_update().get(pk=doi_tuong.pk)
            NguoiDungDAO.kiem_tra_trung_sdt(sdt, tru_pk=doi_tuong.pk)
            truoc = anh_chup(doi_tuong, TRUONG_NHAT_KY_NGUOI_DUNG)
            doi_tuong.ho_ten = (ho_ten or "").strip() or doi_tuong.ho_ten
            doi_tuong.so_dien_thoai = sdt
            doi_tuong.username = sdt if doi_tuong.username == truoc["so_dien_thoai"] else doi_tuong.username
            doi_tuong.vai_tro = vai_tro
            doi_tuong.save()
            ghi_nhat_ky(
                nguoi_dung,
                "SUA_NGUOI_DUNG",
                doi_tuong,
                truoc,
                anh_chup(doi_tuong, TRUONG_NHAT_KY_NGUOI_DUNG),
            )
        return doi_tuong

    @staticmethod
    def dat_khoa(nguoi_dung, doi_tuong: NguoiDung, khoa: bool) -> NguoiDung:
        """Khóa/mở khóa tài khoản (không xóa người dùng)."""
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        if doi_tuong.pk == nguoi_dung.pk and khoa:
            raise ValidationError("Không tự khóa tài khoản của chính mình.", code="tu_khoa")
        with transaction.atomic():
            doi_tuong = NguoiDung.objects.select_for_update().get(pk=doi_tuong.pk)
            truoc = doi_tuong.is_active
            doi_tuong.is_active = not khoa
            doi_tuong.save(update_fields=["is_active", "cap_nhat_luc"])
            ghi_nhat_ky(
                nguoi_dung,
                "KHOA_TAI_KHOAN" if khoa else "MO_KHOA_TAI_KHOAN",
                doi_tuong,
                {"is_active": truoc},
                {"is_active": doi_tuong.is_active},
            )
        return doi_tuong

    @staticmethod
    def dat_lai_mat_khau(nguoi_dung, doi_tuong: NguoiDung) -> str:
        """Cấp mật khẩu tạm (văn phòng) hoặc PIN mới (thợ); bắt buộc đổi ở lần đăng nhập kế tiếp."""
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        bi_mat = sinh_bi_mat(doi_tuong.vai_tro)
        with transaction.atomic():
            doi_tuong = NguoiDung.objects.select_for_update().get(pk=doi_tuong.pk)
            doi_tuong.set_password(bi_mat)
            doi_tuong.phai_doi_mat_khau = True
            doi_tuong.save(update_fields=["password", "phai_doi_mat_khau", "cap_nhat_luc"])
            ghi_nhat_ky(nguoi_dung, "DAT_LAI_MAT_KHAU", doi_tuong)
        return bi_mat

    @staticmethod
    def doi_mat_khau(nguoi_dung: NguoiDung, mat_khau_moi: str) -> None:
        """Người dùng tự đổi mật khẩu/PIN của mình."""
        kiem_tra_mat_khau_moi(mat_khau_moi, nguoi_dung)
        with transaction.atomic():
            nguoi_dung.set_password(mat_khau_moi)
            nguoi_dung.phai_doi_mat_khau = False
            nguoi_dung.save(update_fields=["password", "phai_doi_mat_khau", "cap_nhat_luc"])
            ghi_nhat_ky(nguoi_dung, "DOI_MAT_KHAU", nguoi_dung)


class CauHinhDAO:
    @staticmethod
    def lay_danh_sach(nguoi_dung):
        kiem_tra_vai_tro(nguoi_dung, *QUAN_TRI_GIAM_DOC)
        return CauHinh.objects.order_by("khoa")

    @staticmethod
    def sua(nguoi_dung, ban_ghi: CauHinh, gia_tri: str) -> CauHinh:
        kiem_tra_vai_tro(nguoi_dung, *CHI_QUAN_TRI)
        try:
            chuyen_doi(gia_tri, ban_ghi.kieu)
        except ValidationError as loi:
            raise ValidationError({"gia_tri": loi.messages}) from loi
        with transaction.atomic():
            ban_ghi = CauHinh.objects.select_for_update().get(pk=ban_ghi.pk)
            truoc = ban_ghi.gia_tri
            ban_ghi.gia_tri = gia_tri
            ban_ghi.save()
            ghi_nhat_ky(
                nguoi_dung,
                "SUA_CAU_HINH",
                f"CauHinh:{ban_ghi.khoa}",
                {"gia_tri": truoc},
                {"gia_tri": gia_tri},
            )
        return ban_ghi

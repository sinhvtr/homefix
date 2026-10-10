from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.he_thong.so_dien_thoai import chuan_hoa_sdt

from .models import NguoiDung, VaiTro


class NguoiDungDAO:
    @staticmethod
    def tao_quan_tri(ho_ten: str, so_dien_thoai: str, mat_khau: str, nguoi_dung=None) -> NguoiDung:
        """Tạo tài khoản QUAN_TRI; tên đăng nhập = số điện thoại."""
        ho_ten = (ho_ten or "").strip()
        if not ho_ten:
            raise ValidationError("Họ tên không được để trống.", code="thieu_ho_ten")
        sdt = chuan_hoa_sdt(so_dien_thoai)
        moi = NguoiDung(username=sdt, ho_ten=ho_ten, so_dien_thoai=sdt, vai_tro=VaiTro.QUAN_TRI)
        validate_password(mat_khau, moi)
        with transaction.atomic():
            if (
                NguoiDung.objects.filter(so_dien_thoai=sdt).exists()
                or NguoiDung.objects.filter(username=sdt).exists()
            ):
                raise ValidationError(f"Số điện thoại {sdt} đã có tài khoản.", code="trung_sdt")
            moi.set_password(mat_khau)
            moi.save()
            ghi_nhat_ky(
                nguoi_dung,
                "TAO_NGUOI_DUNG",
                moi,
                du_lieu_sau={"ho_ten": ho_ten, "so_dien_thoai": sdt, "vai_tro": moi.vai_tro},
            )
        return moi

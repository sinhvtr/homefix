from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from apps.he_thong.bieu_mau import KieuBieuMau
from apps.he_thong.so_dien_thoai import chuan_hoa_sdt

from .mat_khau import kiem_tra_mat_khau_moi
from .models import VaiTro


class DangNhapForm(AuthenticationForm):
    username = forms.CharField(
        label="Số điện thoại hoặc tên đăng nhập",
        max_length=150,
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username", "inputmode": "tel"}),
    )
    password = forms.CharField(
        label="Mật khẩu / mã PIN",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        "invalid_login": "Số điện thoại/tên đăng nhập hoặc mật khẩu không đúng.",
        "inactive": "Tài khoản đã bị khóa.",
    }


class DoiMatKhauForm(KieuBieuMau, forms.Form):
    mat_khau_cu = forms.CharField(
        label="Mật khẩu / PIN hiện tại", strip=False, widget=forms.PasswordInput(attrs={"autofocus": True})
    )
    mat_khau_moi = forms.CharField(label="Mật khẩu / PIN mới", strip=False, widget=forms.PasswordInput)
    nhap_lai = forms.CharField(label="Nhập lại", strip=False, widget=forms.PasswordInput)

    def __init__(self, nguoi_dung, *args, **kwargs):
        self.nguoi_dung = nguoi_dung
        super().__init__(*args, **kwargs)
        if nguoi_dung.vai_tro == VaiTro.THO:
            for ten in ("mat_khau_cu", "mat_khau_moi", "nhap_lai"):
                self.fields[ten].widget.attrs.update({"inputmode": "numeric", "maxlength": "6"})
            self.fields["mat_khau_cu"].label = "Mã PIN hiện tại"
            self.fields["mat_khau_moi"].label = "Mã PIN mới (6 số)"
            self.fields["mat_khau_moi"].help_text = "Không dùng 6 số giống nhau hoặc liên tiếp."

    def clean_mat_khau_cu(self):
        cu = self.cleaned_data["mat_khau_cu"]
        if not self.nguoi_dung.check_password(cu):
            raise ValidationError("Mật khẩu / PIN hiện tại không đúng.")
        return cu

    def clean(self):
        du_lieu = super().clean()
        moi, lai = du_lieu.get("mat_khau_moi"), du_lieu.get("nhap_lai")
        if moi and lai and moi != lai:
            self.add_error("nhap_lai", "Hai lần nhập không khớp.")
        if moi and moi == du_lieu.get("mat_khau_cu"):
            self.add_error("mat_khau_moi", "Mật khẩu / PIN mới phải khác cái cũ.")
        elif moi:
            try:
                kiem_tra_mat_khau_moi(moi, self.nguoi_dung)
            except ValidationError as loi:
                self.add_error("mat_khau_moi", loi)
        return du_lieu


class NguoiDungForm(KieuBieuMau, forms.Form):
    ho_ten = forms.CharField(label="Họ tên", max_length=100)
    so_dien_thoai = forms.CharField(
        label="Số điện thoại", max_length=20, widget=forms.TextInput({"inputmode": "tel"})
    )
    vai_tro = forms.ChoiceField(label="Vai trò")

    def __init__(self, *args, cho_phep_tho=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vai_tro"].choices = [
            (ma, nhan) for ma, nhan in VaiTro.choices if cho_phep_tho or ma != VaiTro.THO
        ]

    def clean_so_dien_thoai(self):
        return chuan_hoa_sdt(self.cleaned_data["so_dien_thoai"])


class CauHinhForm(KieuBieuMau, forms.Form):
    gia_tri = forms.CharField(label="Giá trị", max_length=1000, widget=forms.Textarea({"rows": 3}))

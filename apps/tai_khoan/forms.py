from django import forms
from django.contrib.auth.forms import AuthenticationForm


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

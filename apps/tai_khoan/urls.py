from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "tai_khoan"

urlpatterns = [
    path("", views.trang_chu, name="trang_chu"),
    path("dang-nhap/", views.DangNhapView.as_view(), name="dang_nhap"),
    path("dang-xuat/", auth_views.LogoutView.as_view(), name="dang_xuat"),
]

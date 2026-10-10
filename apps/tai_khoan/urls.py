from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "tai_khoan"

urlpatterns = [
    path("", views.trang_chu, name="trang_chu"),
    path("dang-nhap/", views.DangNhapView.as_view(), name="dang_nhap"),
    path("dang-xuat/", auth_views.LogoutView.as_view(), name="dang_xuat"),
    path("doi-mat-khau/", views.doi_mat_khau, name="doi_mat_khau"),
    path("quan-tri/nguoi-dung/", views.nguoi_dung_danh_sach, name="nguoi_dung_danh_sach"),
    path("quan-tri/nguoi-dung/moi/", views.nguoi_dung_moi, name="nguoi_dung_moi"),
    path("quan-tri/nguoi-dung/<int:pk>/sua/", views.nguoi_dung_sua, name="nguoi_dung_sua"),
    path("quan-tri/nguoi-dung/<int:pk>/khoa/", views.nguoi_dung_khoa, name="nguoi_dung_khoa"),
    path(
        "quan-tri/nguoi-dung/<int:pk>/dat-lai-mat-khau/",
        views.nguoi_dung_dat_lai_mat_khau,
        name="nguoi_dung_dat_lai_mat_khau",
    ),
    path("quan-tri/cau-hinh/", views.cau_hinh_danh_sach, name="cau_hinh_danh_sach"),
    path("quan-tri/cau-hinh/<int:pk>/sua/", views.cau_hinh_sua, name="cau_hinh_sua"),
]

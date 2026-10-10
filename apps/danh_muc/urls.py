from django.urls import path

from . import views

app_name = "danh_muc"

urlpatterns = [
    path("khu-vuc/", views.khu_vuc_danh_sach, name="khu_vuc_danh_sach"),
    path("khu-vuc/moi/", views.khu_vuc_moi, name="khu_vuc_moi"),
    path("khu-vuc/<int:pk>/sua/", views.khu_vuc_sua, name="khu_vuc_sua"),
    path("khu-vuc/<int:pk>/xoa/", views.khu_vuc_xoa, name="khu_vuc_xoa"),
    path("dich-vu/", views.dich_vu_danh_sach, name="dich_vu_danh_sach"),
    path("dich-vu/moi/", views.dich_vu_moi, name="dich_vu_moi"),
    path("dich-vu/<int:pk>/sua/", views.dich_vu_sua, name="dich_vu_sua"),
    path("dich-vu/<int:pk>/xoa/", views.dich_vu_xoa, name="dich_vu_xoa"),
    path("dich-vu/nhap/", views.dich_vu_nhap, name="dich_vu_nhap"),
    path("dich-vu/mau.xlsx", views.dich_vu_mau, name="dich_vu_mau"),
    path("tho/", views.tho_danh_sach, name="tho_danh_sach"),
    path("tho/moi/", views.tho_moi, name="tho_moi"),
    path("tho/nhap/", views.tho_nhap, name="tho_nhap"),
    path("tho/mau.xlsx", views.tho_mau, name="tho_mau"),
    path("tho/<int:pk>/", views.tho_chi_tiet, name="tho_chi_tiet"),
    path("tho/<int:pk>/sua/", views.tho_sua, name="tho_sua"),
    path("tho/<int:pk>/cap-pin/", views.tho_cap_pin, name="tho_cap_pin"),
    path("tho/<int:pk>/khoa/", views.tho_khoa, name="tho_khoa"),
    path("khach-hang/", views.khach_hang_danh_sach, name="khach_hang_danh_sach"),
    path("khach-hang/moi/", views.khach_hang_moi, name="khach_hang_moi"),
    path("khach-hang/<int:pk>/", views.khach_hang_chi_tiet, name="khach_hang_chi_tiet"),
    path("khach-hang/<int:pk>/sua/", views.khach_hang_sua, name="khach_hang_sua"),
    path("khach-hang/<int:pk>/xoa/", views.khach_hang_xoa, name="khach_hang_xoa"),
    path("khach-hang/<int:pk>/dia-chi/moi/", views.dia_chi_moi, name="dia_chi_moi"),
    path("dia-chi/<int:pk>/sua/", views.dia_chi_sua, name="dia_chi_sua"),
    path("dia-chi/<int:pk>/xoa/", views.dia_chi_xoa, name="dia_chi_xoa"),
    path("dia-chi/<int:pk>/thiet-bi/moi/", views.thiet_bi_moi, name="thiet_bi_moi"),
    path("thiet-bi/<int:pk>/sua/", views.thiet_bi_sua, name="thiet_bi_sua"),
    path("thiet-bi/<int:pk>/xoa/", views.thiet_bi_xoa, name="thiet_bi_xoa"),
]

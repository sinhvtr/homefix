from django.urls import path

from apps.tiep_nhan_dieu_phoi.urls import MaDonConverter  # noqa: F401 — đăng ký bộ chuyển <ma_don:>

from . import views

app_name = "thuc_hien"

urlpatterns = [
    path("", views.trang_chu, name="trang_chu"),
    path("san-sang/", views.san_sang, name="san_sang"),
    path("de-nghi/<int:pk>/", views.de_nghi, name="de_nghi"),
    path("de-nghi/<int:pk>/nhan/", views.nhan_viec, name="nhan_viec"),
    path("de-nghi/<int:pk>/tu-choi/", views.tu_choi, name="tu_choi"),
    path("don/<ma_don:ma_don>/", views.don, name="don"),
    path("don/<ma_don:ma_don>/tra-viec/", views.tra_viec, name="tra_viec"),
    path("cai-dat/", views.cai_dat, name="cai_dat"),
    path("cai-dat/gui-thu/", views.gui_thu, name="gui_thu"),
]

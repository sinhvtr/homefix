from django.contrib import admin
from django.urls import include, path

from apps.he_thong import views as he_thong_views
from apps.tai_khoan.phan_quyen import GD, KT, QT, yeu_cau_vai_tro
from apps.thuc_hien import views as thuc_hien_views

admin.site.site_header = "HomeFix — quản trị kỹ thuật"

trang_tam = he_thong_views.trang_dang_xay_dung

urlpatterns = [
    path("", include("apps.tai_khoan.urls")),
    path("danh-muc/", include("apps.danh_muc.urls")),
    path("", include("apps.tiep_nhan_dieu_phoi.urls")),
    path("suc-khoe/", he_thong_views.suc_khoe, name="suc_khoe"),
    # Trang đích sau đăng nhập — tạm thời, thay bằng màn hình thật ở P2–P6 (A-05). Quyền theo SPEC 3.1.
    path("tho/", include("apps.thuc_hien.urls")),
    path("", include("apps.thong_bao.urls")),
    path("manifest.webmanifest", thuc_hien_views.manifest, name="manifest"),
    path("service-worker.js", thuc_hien_views.service_worker, name="service_worker"),
    path("anh/<int:pk>/", thuc_hien_views.xem_anh, name="xem_anh"),
    path("anh/thanh-toan/<int:pk>/", thuc_hien_views.xem_chung_tu, name="xem_chung_tu"),
    path(
        "ke-toan/doi-soat/",
        yeu_cau_vai_tro(KT, QT, GD)(trang_tam),
        {"tieu_de": "Đối soát tiền thợ"},
        name="ke_toan_doi_soat",
    ),
    path("bao-cao/", yeu_cau_vai_tro(QT, KT, GD)(trang_tam), {"tieu_de": "Báo cáo"}, name="bao_cao"),
    path("he-thong-noi-bo/", admin.site.urls),
]

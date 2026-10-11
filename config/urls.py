from django.contrib import admin
from django.urls import include, path

from apps.he_thong import views as he_thong_views
from apps.thuc_hien import views as thuc_hien_views

admin.site.site_header = "HomeFix — quản trị kỹ thuật"

urlpatterns = [
    path("", include("apps.tai_khoan.urls")),
    path("danh-muc/", include("apps.danh_muc.urls")),
    path("", include("apps.tiep_nhan_dieu_phoi.urls")),
    path("suc-khoe/", he_thong_views.suc_khoe, name="suc_khoe"),
    path("huong-dan/", he_thong_views.huong_dan, name="huong_dan"),
    path("tho/", include("apps.thuc_hien.urls")),
    path("", include("apps.thong_bao.urls")),
    path("manifest.webmanifest", thuc_hien_views.manifest, name="manifest"),
    path("service-worker.js", thuc_hien_views.service_worker, name="service_worker"),
    path("anh/<int:pk>/", thuc_hien_views.xem_anh, name="xem_anh"),
    path("anh/thanh-toan/<int:pk>/", thuc_hien_views.xem_chung_tu, name="xem_chung_tu"),
    path("ke-toan/", include("apps.tai_chinh.urls")),
    path("bao-hanh/", include("apps.bao_hanh.urls")),
    path("bao-cao/", include("apps.bao_cao.urls")),
    path("he-thong-noi-bo/", admin.site.urls),
]

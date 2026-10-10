from django.contrib import admin
from django.urls import include, path

from apps.he_thong import views as he_thong_views

admin.site.site_header = "HomeFix — quản trị kỹ thuật"

urlpatterns = [
    path("", include("apps.tai_khoan.urls")),
    path("suc-khoe/", he_thong_views.suc_khoe, name="suc_khoe"),
    # P0: trang đích sau đăng nhập theo vai trò — tạm thời, thay bằng màn hình thật ở P2–P6 (A-05).
    path("tong-dai/", he_thong_views.trang_dang_xay_dung, {"tieu_de": "Bảng đơn"}, name="tong_dai"),
    path("tho/", he_thong_views.trang_dang_xay_dung, {"tieu_de": "Việc của tôi"}, name="tho_trang_chu"),
    path(
        "ke-toan/doi-soat/",
        he_thong_views.trang_dang_xay_dung,
        {"tieu_de": "Đối soát tiền thợ"},
        name="ke_toan_doi_soat",
    ),
    path("bao-cao/", he_thong_views.trang_dang_xay_dung, {"tieu_de": "Báo cáo"}, name="bao_cao"),
    path("he-thong-noi-bo/", admin.site.urls),
]

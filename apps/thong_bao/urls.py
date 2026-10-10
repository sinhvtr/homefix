from django.urls import path

from . import views

app_name = "thong_bao"

urlpatterns = [
    path("thong-bao/", views.danh_sach, name="danh_sach"),
    path("thong-bao/<int:pk>/mo/", views.mo, name="mo"),
    path("push/dang-ky/", views.dang_ky_push, name="dang_ky_push"),
    path("telegram/webhook/<str:bi_mat>/", views.telegram_webhook, name="telegram_webhook"),
]

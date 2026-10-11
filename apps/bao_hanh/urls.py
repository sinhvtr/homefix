from django.urls import path

from . import views

app_name = "bao_hanh"

urlpatterns = [
    path("moi/", views.tao_don_bao_hanh, name="tao_don_bao_hanh"),
]

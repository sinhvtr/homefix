from django.urls import path

from . import views

app_name = "tai_chinh"

urlpatterns = [
    path("doi-soat/", views.tong_hop, name="tong_hop"),
    path("doi-soat/lap/", views.lap_phieu, name="lap_phieu"),
    path("doi-soat/<str:ma>/", views.phieu, name="phieu"),
    path("xuat/", views.xuat, name="xuat"),
]

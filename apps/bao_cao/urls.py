from django.urls import path

from . import views

urlpatterns = [
    path("", views.bao_cao, name="bao_cao"),
    path("xuat/", views.xuat, name="bao_cao_xuat"),
]

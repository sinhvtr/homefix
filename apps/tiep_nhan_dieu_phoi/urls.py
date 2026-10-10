from django.urls import path, register_converter

from . import views


class MaDonConverter:
    regex = r"HF\d{6}-\d{3,5}"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(MaDonConverter, "ma_don")

urlpatterns = [
    path("tong-dai/", views.bang_don, name="tong_dai"),
    path("don/moi/", views.tiep_nhan, name="tiep_nhan"),
    path("khach-hang/tra-cuu/", views.tra_cuu_khach, name="tra_cuu_khach"),
    path("don/<ma_don:ma_don>/", views.chi_tiet_don, name="chi_tiet_don"),
    path("don/<ma_don:ma_don>/chot-lich/", views.chot_lich, name="chot_lich"),
    path("don/<ma_don:ma_don>/doi-hen/", views.doi_hen, name="doi_hen"),
    path("don/<ma_don:ma_don>/khach-chua-tra-loi/", views.khach_chua_tra_loi, name="khach_chua_tra_loi"),
    path("don/<ma_don:ma_don>/giuc/", views.khach_giuc, name="khach_giuc"),
    path("don/<ma_don:ma_don>/huy/", views.huy_don, name="huy_don"),
]

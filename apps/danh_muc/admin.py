"""Django Admin chỉ cho superuser kỹ thuật (/he-thong-noi-bo/); người dùng nghiệp vụ dùng màn hình danh mục."""

from django.contrib import admin

from .models import DiaChi, DichVu, KhachHang, KhuVuc, ThietBi, Tho

admin.site.register(KhuVuc, list_display=["ma", "ten"], search_fields=["ma", "ten"])
admin.site.register(
    DichVu,
    list_display=["ma", "ten_dich_vu", "nhom_dich_vu", "loai_thiet_bi", "don_gia_tham_khao", "dang_ap_dung"],
    list_filter=["nhom_dich_vu", "loai_thiet_bi", "dang_ap_dung"],
    search_fields=["ma", "ten_dich_vu"],
)
admin.site.register(
    Tho, list_display=["ho_ten", "so_dien_thoai", "hinh_thuc", "dang_nhan_viec"], search_fields=["ho_ten"]
)
admin.site.register(
    KhachHang,
    list_display=["ho_ten", "so_dien_thoai", "loai_khach"],
    search_fields=["ho_ten", "so_dien_thoai"],
)
admin.site.register(DiaChi, list_display=["dia_chi_chi_tiet", "khach_hang", "khu_vuc", "la_mac_dinh"])
admin.site.register(ThietBi, list_display=["loai_thiet_bi", "hang_san_xuat", "dia_chi"])

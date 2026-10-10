from django.contrib import admin

from .models import CauHinh, NhatKyThaoTac


@admin.register(CauHinh)
class CauHinhAdmin(admin.ModelAdmin):
    list_display = ["khoa", "gia_tri", "kieu", "mo_ta"]
    search_fields = ["khoa"]


@admin.register(NhatKyThaoTac)
class NhatKyThaoTacAdmin(admin.ModelAdmin):
    list_display = ["thoi_diem", "nguoi_dung", "hanh_dong", "doi_tuong", "dia_chi_ip"]
    list_filter = ["hanh_dong"]
    search_fields = ["doi_tuong"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

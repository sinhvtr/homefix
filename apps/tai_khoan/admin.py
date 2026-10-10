from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import NguoiDung


@admin.register(NguoiDung)
class NguoiDungAdmin(UserAdmin):
    list_display = ["username", "ho_ten", "so_dien_thoai", "vai_tro", "is_active"]
    list_filter = ["vai_tro", "is_active"]
    search_fields = ["username", "ho_ten", "so_dien_thoai"]
    fieldsets = [
        *UserAdmin.fieldsets,
        ("HomeFix", {"fields": ["ho_ten", "so_dien_thoai", "vai_tro"]}),
    ]
    add_fieldsets = [
        *UserAdmin.add_fieldsets,
        ("HomeFix", {"fields": ["ho_ten", "so_dien_thoai", "vai_tro"]}),
    ]

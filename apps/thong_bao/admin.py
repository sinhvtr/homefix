from django.contrib import admin

from .models import DangKyPush, ThongBao

admin.site.register(ThongBao, list_display=["tao_luc", "nguoi_nhan", "tieu_de", "da_doc"])
admin.site.register(DangKyPush, list_display=["nguoi_dung", "user_agent", "tao_luc"])

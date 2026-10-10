"""Cấp số thứ tự trong ngày bằng bảng đếm có khóa dòng (an toàn khi nhiều tổng đài tạo đơn cùng lúc)."""

from datetime import date

from django.db import transaction
from django.db.models import F

from .models import BoDemMaDon


def cap_so_thu_tu(ngay: date) -> int:
    """Trả số kế tiếp của ngày (bắt đầu từ 1). Phải gọi trong giao dịch của thao tác tạo đơn."""
    with transaction.atomic():
        # Tạo dòng của ngày nếu chưa có; ignore_conflicts tránh lỗi khi hai giao dịch cùng tạo.
        BoDemMaDon.objects.bulk_create([BoDemMaDon(ngay=ngay)], ignore_conflicts=True)
        bo_dem = BoDemMaDon.objects.select_for_update().get(ngay=ngay)
        bo_dem.so_cuoi = F("so_cuoi") + 1
        bo_dem.save(update_fields=["so_cuoi", "cap_nhat_luc"])
        bo_dem.refresh_from_db(fields=["so_cuoi"])
        return bo_dem.so_cuoi

"""Nén ảnh tải lên phía máy chủ (SPEC 2.1): cạnh dài ≤ 1600 px, JPEG chất lượng 80%.
Bỏ toàn bộ EXIF (kể cả tọa độ GPS) — không lưu vị trí (OI-05)."""

import io

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

CANH_TOI_DA = 1600
CHAT_LUONG = 80
DUNG_LUONG_TOI_DA = 15 * 1024 * 1024  # 15 MB ảnh gốc từ điện thoại


def nen_anh(tep) -> tuple[ContentFile, int, int]:
    """Trả (nội dung JPEG đã nén, rộng, cao). Tệp không phải ảnh hoặc quá lớn → ValidationError."""
    if getattr(tep, "size", 0) > DUNG_LUONG_TOI_DA:
        raise ValidationError("Ảnh quá lớn (tối đa 15 MB).", code="anh_qua_lon")
    try:
        anh = Image.open(tep)
        anh.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as loi:
        raise ValidationError("Tệp không phải ảnh hợp lệ.", code="khong_phai_anh") from loi
    anh = ImageOps.exif_transpose(anh)  # xoay đúng chiều trước khi bỏ EXIF
    if anh.mode not in ("RGB", "L"):
        nen = Image.new("RGB", anh.size, (255, 255, 255))
        nen.paste(anh.convert("RGBA"), mask=anh.convert("RGBA").split()[-1])
        anh = nen
    anh = anh.convert("RGB")
    anh.thumbnail((CANH_TOI_DA, CANH_TOI_DA), Image.Resampling.LANCZOS)
    dem = io.BytesIO()
    anh.save(dem, format="JPEG", quality=CHAT_LUONG, optimize=True)  # không truyền exif → không giữ metadata
    return ContentFile(dem.getvalue(), name="anh.jpg"), anh.width, anh.height

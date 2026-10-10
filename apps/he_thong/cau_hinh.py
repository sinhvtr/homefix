"""Tham số nghiệp vụ (SPEC 8.2). Đọc qua cau_hinh("KHOA"), bộ nhớ đệm 60 giây."""

import json

from django.core.cache import cache
from django.core.exceptions import ValidationError

THOI_GIAN_DEM_GIAY = 60

# khoa: (gia_tri dạng chuỗi, kieu, mo_ta)
MAC_DINH: dict[str, tuple[str, str, str]] = {
    "THOI_HAN_PHAN_HOI_PHUT": ("15", "INT", "Số phút thợ được nhận/từ chối đề nghị (BR02)."),
    "NHAC_XAC_NHAN_SAU_GIO": ("24", "INT", "Số giờ chờ trước khi nhắc khách chốt lịch (BR08)."),
    "SO_LAN_NHAC_TOI_DA": ("3", "INT", "Số lần nhắc tối đa trước khi hủy đơn (BR08)."),
    "BAO_HANH_VE_SINH_NGAY": ("7", "INT", "Thời hạn bảo hành mặc định nhóm vệ sinh, bảo dưỡng (BR05)."),
    "BAO_HANH_SUA_CHUA_NGAY": ("90", "INT", "Thời hạn bảo hành mặc định nhóm sửa chữa, thay vật tư (BR05)."),
    "VIP_SO_DON_TOI_THIEU": ("3", "INT", "Số đơn hoàn thành trong 365 ngày để thành khách VIP (BR07)."),
    "VIP_TY_LE_GIAM": ("10", "INT", "Tỷ lệ giảm giá cho khách VIP, tính theo % (BR07)."),
    "VIP_PHAM_VI_GIAM": ("TIEN_CONG", "STR", "Phạm vi giảm VIP: TIEN_CONG hoặc CONG_VA_VAT_TU (OI-02)."),
    "NGUONG_BAO_GIA_TONG_DAI_XAC_NHAN": (
        "2000000",
        "INT",
        "Báo giá từ mức này (đồng) phải chờ tổng đài gọi xác nhận; 0 = tắt (OI-08).",
    ),
    "PHI_KIEM_TRA_KHI_TU_CHOI": ("0", "INT", "Phí kiểm tra (đồng) khi khách từ chối báo giá (A-04)."),
    "CANH_BAO_CHO_CU_THO_PHUT": ("30", "INT", "Đơn chờ cử thợ quá số phút này thì gắn nhãn đỏ."),
    "DEM_DI_CHUYEN_PHUT": ("30", "INT", "Thời gian đệm di chuyển giữa hai lịch của thợ (BR04)."),
    "KHUNG_GIO": (
        '["08:00-10:00", "10:00-12:00", "13:00-15:00", "15:00-17:00", "17:00-19:00"]',
        "JSON",
        "Các khung giờ hẹn khách.",
    ),
    "SO_ANH_TOI_THIEU_KHI_HOAN_THANH": ("1", "INT", "Số ảnh hiện trường tối thiểu khi báo hoàn thành."),
    "MAU_TIN_NHAN_XAC_NHAN_LICH": (
        "HomeFix xin chào {ten_khach}. Đơn {ma_don} đã được hẹn lịch {khung_gio}. "
        "Thợ sẽ gọi trước khi đến. Cảm ơn quý khách!",
        "STR",
        "Mẫu tin nhắn xác nhận lịch; biến: {ten_khach}, {ma_don}, {khung_gio}.",
    ),
}

_DUNG = {"1", "true", "co", "có", "yes"}
_SAI = {"0", "false", "khong", "không", "no"}


def chuyen_doi(gia_tri: str, kieu: str):
    """Chuyển chuỗi lưu trong CSDL sang kiểu Python. Sai kiểu → ValidationError."""
    try:
        if kieu == "INT":
            return int(gia_tri)
        if kieu == "BOOL":
            chuoi = gia_tri.strip().lower()
            if chuoi in _DUNG:
                return True
            if chuoi in _SAI:
                return False
            raise ValueError(gia_tri)
        if kieu == "JSON":
            return json.loads(gia_tri)
        if kieu == "STR":
            return gia_tri
    except (ValueError, TypeError) as loi:
        raise ValidationError(f"Giá trị “{gia_tri}” không đúng kiểu {kieu}.", code="sai_kieu") from loi
    raise ValidationError(f"Kiểu cấu hình không hỗ trợ: {kieu}.", code="kieu_khong_ho_tro")


def khoa_bo_dem(khoa: str) -> str:
    return f"cau_hinh:{khoa}"


def cau_hinh(khoa: str):
    """Trả giá trị cấu hình đã chuyển kiểu; ưu tiên bản ghi CauHinh, không có thì lấy MAC_DINH."""
    from .models import CauHinh

    gia_tri = cache.get(khoa_bo_dem(khoa))
    if gia_tri is not None:
        return gia_tri
    ban_ghi = CauHinh.objects.filter(khoa=khoa).first()
    if ban_ghi is not None:
        gia_tri = chuyen_doi(ban_ghi.gia_tri, ban_ghi.kieu)
    elif khoa in MAC_DINH:
        chuoi, kieu, _ = MAC_DINH[khoa]
        gia_tri = chuyen_doi(chuoi, kieu)
    else:
        raise KeyError(f"Không có tham số cấu hình {khoa}")
    cache.set(khoa_bo_dem(khoa), gia_tri, THOI_GIAN_DEM_GIAY)
    return gia_tri

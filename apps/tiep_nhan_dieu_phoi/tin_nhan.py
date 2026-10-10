"""Tin nhắn mẫu để tổng đài sao chép gửi khách qua Zalo/SMS thủ công (SPEC 2.1 — không phát sinh chi phí)."""

from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.cau_hinh import cau_hinh

MAU_GOI_LAI = (
    "HomeFix xin chào {ten_khach}. Đơn {ma_don} ({dich_vu}) của quý khách đang chờ chốt giờ hẹn. "
    "Quý khách vui lòng phản hồi khung giờ thuận tiện để HomeFix cử thợ. Cảm ơn quý khách!"
)


def _ten_khach(don: DonSuaChua) -> str:
    return (don.khach_hang.ho_ten or "").strip() or "quý khách"


def tin_nhan_xac_nhan_lich(don: DonSuaChua) -> str:
    """Theo mẫu cấu hình MAU_TIN_NHAN_XAC_NHAN_LICH: biến {ten_khach}, {ma_don}, {khung_gio}."""
    lich = don.lich_hieu_luc
    khung_gio = lich.khung_gio if lich else (don.khung_gio_mong_muon or "(chưa chốt)")
    return cau_hinh("MAU_TIN_NHAN_XAC_NHAN_LICH").format(
        ten_khach=_ten_khach(don), ma_don=don.ma_don, khung_gio=khung_gio
    )


def tin_nhan_goi_lai(don: DonSuaChua) -> str:
    """Kèm việc cần làm “Gọi lại khách” (BR08)."""
    return MAU_GOI_LAI.format(
        ten_khach=_ten_khach(don), ma_don=don.ma_don, dich_vu=don.dich_vu_yeu_cau.ten_dich_vu
    )

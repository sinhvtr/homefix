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


LY_DO_TU_CHOI_GIA = ["Giá cao", "Khách tự sửa / mua mới", "Để khách cân nhắc thêm", "Lý do khác"]

MAU_CAM_ON = (
    "HomeFix cảm ơn {ten_khach}! Đơn {ma_don} ({dich_vu}) đã hoàn thành, tổng thanh toán {tong}. "
    "{bao_hanh}Cần hỗ trợ xin gọi lại số tổng đài HomeFix."
)


def tin_nhan_cam_on(don) -> str:
    """Thợ sao chép gửi khách sau khi hoàn thành (UC09)."""
    phieu = getattr(don, "phieu_bao_hanh", None)
    bao_hanh = (
        f"Bảo hành đến hết ngày {phieu.ngay_het_han:%d/%m/%Y} (mã {phieu.ma}). " if phieu is not None else ""
    )
    return MAU_CAM_ON.format(
        ten_khach=_ten_khach(don),
        ma_don=don.ma_don,
        dich_vu=don.dich_vu_yeu_cau.ten_dich_vu,
        tong=f"{don.tong_tien_phai_thu or 0:,} đ".replace(",", "."),
        bao_hanh=bao_hanh,
    )

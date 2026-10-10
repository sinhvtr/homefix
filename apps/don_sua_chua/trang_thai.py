"""Máy trạng thái DonSuaChua (SPEC 6.1). Bảng CHUYEN_TRANG_THAI là nguồn duy nhất; mọi phương thức nghiệp vụ tra bảng này.

Mỗi dòng có một sự kiện riêng; khi SPEC phân nhánh theo điều kiện (T1/T2, T4/T5, T9/T10, T11/T12) thì phương thức
nghiệp vụ xét điều kiện rồi chọn sự kiện tương ứng. Thêm trạng thái/chuyển mới = thêm một dòng vào bảng.
"""

from dataclasses import dataclass

from django.db import models


class TrangThaiDon(models.TextChoices):
    CHO_XAC_NHAN_LICH = "CHO_XAC_NHAN_LICH", "Chờ khách xác nhận lịch"
    CHO_CU_THO = "CHO_CU_THO", "Chờ cử thợ"
    DA_CO_THO = "DA_CO_THO", "Đã có thợ"
    CHO_DUYET_GIA = "CHO_DUYET_GIA", "Chờ khách duyệt giá"
    DANG_SUA = "DANG_SUA", "Đang sửa"
    HOAN_THANH = "HOAN_THANH", "Hoàn thành"
    DANG_BAO_HANH = "DANG_BAO_HANH", "Đang bảo hành"
    DA_HUY = "DA_HUY", "Đã hủy"
    DA_DONG = "DA_DONG", "Đã đóng"


T = TrangThaiDon

# Nhóm phức hợp (không lưu, dùng để lọc/kiểm tra)
DANG_XU_LY = frozenset({T.CHO_XAC_NHAN_LICH, T.CHO_CU_THO, T.DA_CO_THO, T.CHO_DUYET_GIA, T.DANG_SUA})
DANG_THUC_HIEN = frozenset({T.CHO_DUYET_GIA, T.DANG_SUA})

DAU = None  # trạng thái "(đầu)" — đơn chưa tồn tại


class SuKien(models.TextChoices):
    TAO_DON_CHUA_CHOT_LICH = "TAO_DON_CHUA_CHOT_LICH", "Tạo đơn (chưa chốt lịch)"
    TAO_DON_DA_CHOT_LICH = "TAO_DON_DA_CHOT_LICH", "Tạo đơn (đã chốt lịch)"
    CHOT_LICH = "CHOT_LICH", "Khách chốt khung giờ"
    NHAC_XAC_NHAN = "NHAC_XAC_NHAN", "Nhắc khách xác nhận lịch"
    HET_LUOT_NHAC = "HET_LUOT_NHAC", "Hết lượt nhắc"
    DE_NGHI_DOI_LICH = "DE_NGHI_DOI_LICH", "Đề nghị khách đổi lịch"
    THO_NHAN_VIEC = "THO_NHAN_VIEC", "Thợ nhận việc"
    RUT_VIEC = "RUT_VIEC", "Thợ báo bận / tổng đài rút việc"
    DEN_NOI_SUA_CHUA = "DEN_NOI_SUA_CHUA", "Thợ đến nơi (sửa chữa)"
    DEN_NOI_VE_SINH = "DEN_NOI_VE_SINH", "Thợ đến nơi (vệ sinh)"
    KHACH_DUYET_GIA = "KHACH_DUYET_GIA", "Khách đồng ý giá"
    TONG_DAI_XAC_NHAN_GIA = "TONG_DAI_XAC_NHAN_GIA", "Tổng đài xác nhận giá"
    KHACH_TU_CHOI_GIA = "KHACH_TU_CHOI_GIA", "Khách từ chối giá"
    KHACH_HUY = "KHACH_HUY", "Khách hủy"
    HOAN_THANH = "HOAN_THANH", "Thợ báo hoàn thành"
    MO_BAO_HANH = "MO_BAO_HANH", "Tạo đơn bảo hành"
    KET_THUC_BAO_HANH = "KET_THUC_BAO_HANH", "Đơn bảo hành con kết thúc"
    HET_HAN_BAO_HANH = "HET_HAN_BAO_HANH", "Hết hạn bảo hành"


@dataclass(frozen=True)
class ChuyenTrangThai:
    ma: str
    tu: frozenset  # tập trạng thái nguồn; {DAU} cho chuyển khởi tạo
    su_kien: str
    dieu_kien: str
    hanh_dong: str
    den: str | None  # None = giữ nguyên trạng thái
    nguon: str


def _tu(*trang_thai) -> frozenset:
    return frozenset(trang_thai)


S = SuKien
CHUYEN_TRANG_THAI: tuple[ChuyenTrangThai, ...] = (
    ChuyenTrangThai(
        "T1", _tu(DAU), S.TAO_DON_CHUA_CHOT_LICH, "chưa chốt lịch", "—", T.CHO_XAC_NHAN_LICH, "UC02"
    ),
    ChuyenTrangThai(
        "T2", _tu(DAU), S.TAO_DON_DA_CHOT_LICH, "đã chốt lịch", "tạo LichHen", T.CHO_CU_THO, "UC02, UC03"
    ),
    ChuyenTrangThai("T3", _tu(T.CHO_XAC_NHAN_LICH), S.CHOT_LICH, "—", "tạo LichHen", T.CHO_CU_THO, "UC03"),
    ChuyenTrangThai(
        "T4", _tu(T.CHO_XAC_NHAN_LICH), S.NHAC_XAC_NHAN, "đã nhắc < 3 lần", "tăng so_lan_nhac", None, "BR08"
    ),
    ChuyenTrangThai(
        "T5", _tu(T.CHO_XAC_NHAN_LICH), S.HET_LUOT_NHAC, "đã nhắc đủ 3 lần", "ghi lý do", T.DA_HUY, "BR08"
    ),
    ChuyenTrangThai(
        "T6",
        _tu(T.CHO_CU_THO),
        S.DE_NGHI_DOI_LICH,
        "—",
        "lịch hiện tại → DA_HUY",
        T.CHO_XAC_NHAN_LICH,
        "UC04 2a",
    ),
    ChuyenTrangThai(
        "T7", _tu(T.CHO_CU_THO), S.THO_NHAN_VIEC, "đơn chưa có thợ", "gán tho", T.DA_CO_THO, "UC04; BR03"
    ),
    ChuyenTrangThai("T8", _tu(T.DA_CO_THO), S.RUT_VIEC, "—", "tho = null", T.CHO_CU_THO, "[ĐX] A-03"),
    ChuyenTrangThai(
        "T9",
        _tu(T.DA_CO_THO),
        S.DEN_NOI_SUA_CHUA,
        "nhóm = SUA_CHUA_THAY_VAT_TU",
        "—",
        T.CHO_DUYET_GIA,
        "A-02; BR06",
    ),
    ChuyenTrangThai(
        "T10",
        _tu(T.DA_CO_THO),
        S.DEN_NOI_VE_SINH,
        "nhóm = VE_SINH_BAO_DUONG",
        "tạo dòng CONG theo bảng giá",
        T.DANG_SUA,
        "A-02; BR06",
    ),
    ChuyenTrangThai(
        "T11",
        _tu(T.CHO_DUYET_GIA),
        S.KHACH_DUYET_GIA,
        "không cần tổng đài xác nhận",
        "chốt báo giá",
        T.DANG_SUA,
        "UC08",
    ),
    ChuyenTrangThai(
        "T12",
        _tu(T.CHO_DUYET_GIA),
        S.TONG_DAI_XAC_NHAN_GIA,
        "cho_tong_dai_xac_nhan_gia",
        "chốt báo giá",
        T.DANG_SUA,
        "[ĐX][OI-08]",
    ),
    ChuyenTrangThai(
        "T13",
        _tu(T.CHO_DUYET_GIA),
        S.KHACH_TU_CHOI_GIA,
        "—",
        "ghi lý do, phí kiểm tra",
        T.DA_HUY,
        "UC08; A-04",
    ),
    ChuyenTrangThai("T14", DANG_XU_LY, S.KHACH_HUY, "—", "hủy lịch & đề nghị đang chờ", T.DA_HUY, "Tổng đài"),
    ChuyenTrangThai(
        "T15",
        _tu(T.DANG_SUA),
        S.HOAN_THANH,
        "đã nhập tiền thu, đủ ảnh",
        "chốt tong_tien_phai_thu",
        T.HOAN_THANH,
        "UC09",
    ),
    ChuyenTrangThai(
        "T16", _tu(T.HOAN_THANH), S.MO_BAO_HANH, "phiếu bảo hành còn hạn", "—", T.DANG_BAO_HANH, "UC11; BR05"
    ),
    ChuyenTrangThai("T17", _tu(T.DANG_BAO_HANH), S.KET_THUC_BAO_HANH, "—", "—", T.HOAN_THANH, "UC11"),
    ChuyenTrangThai("T18", _tu(T.HOAN_THANH), S.HET_HAN_BAO_HANH, "hết hạn bảo hành", "—", T.DA_DONG, "BR05"),
)


class ChuyenTrangThaiKhongHopLe(Exception):
    """Sự kiện không hợp lệ với trạng thái hiện tại, hoặc điều kiện của dòng chuyển không thỏa."""


def tim_chuyen(tu: str | None, su_kien: str) -> ChuyenTrangThai:
    for dong in CHUYEN_TRANG_THAI:
        if dong.su_kien == su_kien and tu in dong.tu:
            return dong
    nhan_tu = T(tu).label if tu else "(đầu)"
    raise ChuyenTrangThaiKhongHopLe(f"Không thể “{SuKien(su_kien).label}” khi đơn đang “{nhan_tu}”.")


def cac_su_kien_hop_le(tu: str | None) -> list[str]:
    return [d.su_kien for d in CHUYEN_TRANG_THAI if tu in d.tu]

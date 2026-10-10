"""Bố cục và menu thanh bên theo vai trò (SPEC 13). Chỉ hiện mục mà vai trò được xem (SPEC 3.1)."""

from .models import VaiTro

_BANG_DON = ("Bảng đơn", "/tong-dai/")
_TONG_DAI = [_BANG_DON, ("Tạo đơn mới", "/don/moi/"), ("Lịch thợ", "/tho-lich/")]
_XEM_DANH_MUC = [
    ("Khách hàng", "/danh-muc/khach-hang/"),
    ("Thợ", "/danh-muc/tho/"),
    ("Dịch vụ, bảng giá", "/danh-muc/dich-vu/"),
    ("Khu vực", "/danh-muc/khu-vuc/"),
]
_QUAN_TRI = [
    ("Người dùng", "/quan-tri/nguoi-dung/"),
    ("Cấu hình", "/quan-tri/cau-hinh/"),
    ("Nhật ký", "/quan-tri/nhat-ky/"),
]

MENU = {
    VaiTro.QUAN_TRI: _TONG_DAI
    + _XEM_DANH_MUC
    + [("Đối soát", "/ke-toan/doi-soat/"), ("Báo cáo", "/bao-cao/")]
    + _QUAN_TRI,
    VaiTro.TONG_DAI: _TONG_DAI + _XEM_DANH_MUC,
    VaiTro.KE_TOAN: [("Đối soát", "/ke-toan/doi-soat/"), ("Báo cáo", "/bao-cao/")] + _XEM_DANH_MUC,
    VaiTro.GIAM_DOC: [("Báo cáo", "/bao-cao/"), _BANG_DON, ("Đối soát", "/ke-toan/doi-soat/")]
    + _XEM_DANH_MUC
    + _QUAN_TRI,
    VaiTro.THO: [],
}


def menu_theo_vai_tro(request):
    nguoi_dung = getattr(request, "user", None)
    if nguoi_dung is None or not nguoi_dung.is_authenticated:
        return {"menu": [], "bo_cuc": "base_van_phong.html"}
    return {
        "menu": MENU.get(nguoi_dung.vai_tro, []),
        "bo_cuc": "base_tho.html" if nguoi_dung.vai_tro == VaiTro.THO else "base_van_phong.html",
    }

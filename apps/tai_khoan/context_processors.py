"""Menu thanh bên của bố cục văn phòng theo vai trò (SPEC 13). Đường dẫn theo bản đồ URL SPEC 13."""

from .models import VaiTro

_TONG_DAI = [
    ("Bảng đơn", "/tong-dai/"),
    ("Tạo đơn mới", "/don/moi/"),
    ("Lịch thợ", "/tho-lich/"),
    ("Khách hàng", "/danh-muc/khach-hang/"),
]
_DANH_MUC = [
    ("Thợ", "/danh-muc/tho/"),
    ("Dịch vụ, bảng giá", "/danh-muc/dich-vu/"),
    ("Khu vực", "/danh-muc/khu-vuc/"),
]

MENU = {
    VaiTro.QUAN_TRI: _TONG_DAI
    + _DANH_MUC
    + [
        ("Người dùng", "/quan-tri/nguoi-dung/"),
        ("Cấu hình", "/quan-tri/cau-hinh/"),
        ("Nhật ký", "/quan-tri/nhat-ky/"),
    ],
    VaiTro.TONG_DAI: _TONG_DAI,
    VaiTro.KE_TOAN: [("Đối soát", "/ke-toan/doi-soat/"), ("Báo cáo", "/bao-cao/")],
    VaiTro.GIAM_DOC: [
        ("Báo cáo", "/bao-cao/"),
        ("Bảng đơn", "/tong-dai/"),
        ("Nhật ký", "/quan-tri/nhat-ky/"),
    ],
    VaiTro.THO: [],
}


def menu_theo_vai_tro(request):
    nguoi_dung = getattr(request, "user", None)
    if nguoi_dung is None or not nguoi_dung.is_authenticated:
        return {"menu": []}
    return {"menu": MENU.get(nguoi_dung.vai_tro, [])}

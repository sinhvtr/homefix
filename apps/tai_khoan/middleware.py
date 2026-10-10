from django.shortcuts import redirect
from django.urls import reverse

DUONG_DAN_CHO_PHEP = ("/doi-mat-khau/", "/dang-xuat/", "/static/", "/suc-khoe/")


class BatDoiMatKhauMiddleware:
    """Người dùng được cấp/đặt lại mật khẩu, PIN phải đổi trước khi dùng chức năng khác (UC01)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        nguoi_dung = getattr(request, "user", None)
        if (
            nguoi_dung is not None
            and nguoi_dung.is_authenticated
            and getattr(nguoi_dung, "phai_doi_mat_khau", False)
            and not request.path.startswith(DUONG_DAN_CHO_PHEP)
        ):
            return redirect(reverse("tai_khoan:doi_mat_khau"))
        return self.get_response(request)

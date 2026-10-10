from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
@never_cache
def suc_khoe(request):
    """Health check cho Docker: kiểm tra kết nối CSDL."""
    try:
        with connection.cursor() as con_tro:
            con_tro.execute("SELECT 1")
    except Exception:
        return JsonResponse({"trang_thai": "loi", "csdl": "khong_ket_noi"}, status=503)
    return JsonResponse({"trang_thai": "ok", "csdl": "ok"})


@login_required
def trang_dang_xay_dung(request, tieu_de):
    """Trang đích tạm của P0 (A-05)."""
    bo_cuc = "base_tho.html" if request.user.vai_tro == "THO" else "base_van_phong.html"
    return render(request, "he_thong/dang_xay_dung.html", {"tieu_de": tieu_de, "bo_cuc": bo_cuc})

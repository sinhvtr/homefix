from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .markdown_don_gian import neo, sang_html


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
def huong_dan(request):
    """/huong-dan/ (NFR09): hiển thị docs/HUONG_DAN_SU_DUNG.md; mở sẵn phần của vai trò người xem."""
    van_ban = (Path(settings.BASE_DIR) / "docs" / "HUONG_DAN_SU_DUNG.md").read_text(encoding="utf-8")
    noi_dung, muc_luc = sang_html(van_ban)
    vai_tro = neo(request.user.get_vai_tro_display())
    phan_cua_toi = next((ma for ma, _ in muc_luc if ma.startswith(vai_tro)), "")
    return render(
        request,
        "he_thong/huong_dan.html",
        {"noi_dung": noi_dung, "muc_luc": muc_luc, "phan_cua_toi": phan_cua_toi},
    )

import contextlib
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import DangKyPush, ThongBao
from .telegram import xu_ly_cap_nhat


@login_required
def danh_sach(request):
    ds = list(ThongBao.objects.filter(nguoi_nhan=request.user)[:100])
    ThongBao.objects.filter(nguoi_nhan=request.user, da_doc=False).update(da_doc=True)
    return render(request, "thong_bao/danh_sach.html", {"ds": ds})


@require_POST
@login_required
def mo(request, pk):
    """Bấm một thông báo: đánh dấu đã đọc rồi mở đường dẫn (chỉ đường dẫn nội bộ)."""
    tb = ThongBao.objects.filter(pk=pk, nguoi_nhan=request.user).first()
    if tb is None:
        raise Http404
    tb.da_doc = True
    tb.save(update_fields=["da_doc", "cap_nhat_luc"])
    return redirect(tb.duong_dan if tb.duong_dan.startswith("/") else "/thong-bao/")


@require_POST
@login_required
def dang_ky_push(request):
    """Trình duyệt gửi PushSubscription (JSON) sau khi người dùng bật thông báo."""
    try:
        du_lieu = json.loads(request.body)
        endpoint = du_lieu["endpoint"]
        khoa = du_lieu["keys"]
        if not endpoint.startswith("https://"):
            raise ValueError
    except (ValueError, KeyError, TypeError):
        return HttpResponseBadRequest("Dữ liệu đăng ký không hợp lệ")
    DangKyPush.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "nguoi_dung": request.user,
            "p256dh": khoa["p256dh"],
            "auth": khoa["auth"],
            "user_agent": request.headers.get("User-Agent", "")[:300],
        },
    )
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def telegram_webhook(request, bi_mat):
    if not settings.TELEGRAM_WEBHOOK_SECRET or bi_mat != settings.TELEGRAM_WEBHOOK_SECRET:
        raise Http404
    with contextlib.suppress(ValueError):
        xu_ly_cap_nhat(json.loads(request.body))
    return HttpResponse("ok")  # luôn 200 để Telegram không gửi lại

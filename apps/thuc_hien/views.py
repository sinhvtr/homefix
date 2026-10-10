"""Màn hình thợ trên điện thoại (UC07; PWA). Không có lớp thực thể — chỉ gọi DAO.
NFR04: thợ chỉ thấy SĐT, địa chỉ khách của đơn mình đã nhận; đoán URL đơn/đề nghị khác → 404."""

import json
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from apps.danh_muc.dao import ThoDAO
from apps.danh_muc.models import Tho
from apps.don_sua_chua.models import DonSuaChua
from apps.tai_khoan.phan_quyen import THO, yeu_cau_vai_tro
from apps.thong_bao.dich_vu import DichVuThongBao
from apps.thong_bao.telegram import lien_ket_moi
from apps.tiep_nhan_dieu_phoi.dao import PhanCongDAO
from apps.tiep_nhan_dieu_phoi.models import PhanCong


def _tho_cua(request) -> Tho:
    tho = Tho.objects.filter(nguoi_dung=request.user).first()
    if tho is None:
        raise PermissionDenied("Tài khoản chưa có hồ sơ thợ — liên hệ quản trị.")
    return tho


@yeu_cau_vai_tro(THO)
def trang_chu(request):
    """Ba khối: Đề nghị đang chờ (đếm ngược), Việc hôm nay, Việc sắp tới; công tắc “Sẵn sàng nhận việc”."""
    hom_nay = timezone.localdate()
    viec = PhanCongDAO.viec_cua_tho(request.user)

    def ngay_hen(d):
        return timezone.localdate(d.lich_hieu_luc.bat_dau) if d.lich_hieu_luc else hom_nay

    return render(
        request,
        "thuc_hien/tho_trang_chu.html",
        {
            "tho": _tho_cua(request),
            "de_nghi": PhanCongDAO.de_nghi_dang_cho_cua_tho(request.user),
            "hom_nay": [d for d in viec if ngay_hen(d) <= hom_nay],
            "sap_toi": [d for d in viec if ngay_hen(d) > hom_nay],
        },
    )


@require_POST
@yeu_cau_vai_tro(THO)
def san_sang(request):
    tho = _tho_cua(request)
    tho = ThoDAO.cap_nhat_cua_toi(request.user, dang_nhan_viec=not tho.dang_nhan_viec)
    messages.info(request, "Đã bật nhận việc." if tho.dang_nhan_viec else "Đã tắt nhận việc.")
    return redirect("thuc_hien:trang_chu")


def _de_nghi(request, pk) -> PhanCong:
    try:
        return PhanCongDAO.lay_de_nghi_cua_tho(request.user, pk)
    except PhanCong.DoesNotExist as loi:
        raise Http404 from loi


@yeu_cau_vai_tro(THO)
def de_nghi(request, pk):
    """Chi tiết đề nghị: dịch vụ, khu vực, khung giờ, mô tả, tiền công dự kiến — KHÔNG có SĐT, địa chỉ chi tiết."""
    pc = _de_nghi(request, pk)
    return render(
        request,
        "thuc_hien/de_nghi.html",
        {
            "pc": pc,
            "don": pc.don,
            "con_nhan_duoc": pc.trang_thai in ("CHO_PHAN_HOI", "QUA_HAN")
            and pc.don.trang_thai == "CHO_CU_THO",
            "ly_do_tu_choi": PhanCong.LyDoTuChoi.choices,
        },
    )


@require_POST
@yeu_cau_vai_tro(THO)
def nhan_viec(request, pk):
    """Chạm NHẬN VIỆC — không có hộp xác nhận thứ hai (NFR07: ≤ 3 chạm)."""
    try:
        ok, thong_diep = PhanCongDAO.nhan_viec(request.user, pk)
    except PermissionDenied as loi:
        raise Http404 from loi
    if ok:
        messages.success(request, thong_diep)
        return redirect("thuc_hien:don", ma_don=PhanCong.objects.get(pk=pk).don.ma_don)
    messages.error(request, thong_diep)
    return redirect("thuc_hien:trang_chu")


@require_POST
@yeu_cau_vai_tro(THO)
def tu_choi(request, pk):
    """Từ chối: chọn một lý do có sẵn (một chạm) → gửi."""
    try:
        PhanCongDAO.tu_choi(request.user, pk, request.POST.get("ly_do", ""))
    except PermissionDenied as loi:
        raise Http404 from loi
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
        return redirect("thuc_hien:de_nghi", pk=pk)
    messages.info(request, "Đã từ chối đề nghị.")
    return redirect("thuc_hien:trang_chu")


@yeu_cau_vai_tro(THO)
def don(request, ma_don):
    """Sau khi nhận: tên, SĐT (gọi), địa chỉ, ghi chú đường đi, mở bản đồ, lịch sử tại địa chỉ."""
    try:
        d = PhanCongDAO.lay_don_cua_tho(request.user, ma_don)
    except DonSuaChua.DoesNotExist as loi:
        raise Http404 from loi
    dia_chi = f"{d.dia_chi.dia_chi_chi_tiet}, {d.dia_chi.khu_vuc.ten}, Hà Nội"
    return render(
        request,
        "thuc_hien/don.html",
        {
            "don": d,
            "lich": d.lich_hieu_luc,
            # Liên kết tìm kiếm theo chuỗi địa chỉ — không gửi tọa độ
            "url_ban_do": "https://www.google.com/maps/search/?api=1&query=" + quote(dia_chi),
            "lich_su": PhanCongDAO.lich_su_tai_dia_chi(d),
        },
    )


@require_POST
@yeu_cau_vai_tro(THO)
def tra_viec(request, ma_don):
    """“Báo bận / trả việc” (chỉ trước khi “Đã đến nơi”) → T8, bắt buộc lý do, báo tổng đài."""
    try:
        d = PhanCongDAO.lay_don_cua_tho(request.user, ma_don)
        PhanCongDAO.tra_viec(request.user, d, request.POST.get("ly_do", ""))
    except DonSuaChua.DoesNotExist as loi:
        raise Http404 from loi
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
        return redirect("thuc_hien:don", ma_don=ma_don)
    messages.info(request, "Đã trả việc, tổng đài đã được báo.")
    return redirect("thuc_hien:trang_chu")


@yeu_cau_vai_tro(THO)
def cai_dat(request):
    """Kênh thông báo, bật Web Push, gắn Telegram, gửi thử; hướng dẫn cài lên màn hình chính (iPhone)."""
    tho = _tho_cua(request)
    if request.method == "POST":
        kenh = request.POST.get("kenh_thong_bao")
        try:
            ThoDAO.cap_nhat_cua_toi(request.user, kenh_thong_bao=kenh)
            messages.success(request, "Đã lưu kênh thông báo.")
        except ValidationError as loi:
            messages.error(request, " ".join(loi.messages))
        return redirect("thuc_hien:cai_dat")
    return render(
        request,
        "thuc_hien/cai_dat.html",
        {
            "tho": tho,
            "vapid_public_key": settings.VAPID_PUBLIC_KEY,
            "lien_ket_telegram": lien_ket_moi(request.user) if settings.TELEGRAM_BOT_USERNAME else "",
            "kenh": Tho.KenhThongBao.choices,
            "so_thiet_bi_push": request.user.ds_dang_ky_push.count(),
        },
    )


@require_POST
@yeu_cau_vai_tro(THO)
def gui_thu(request):
    DichVuThongBao.gui(
        request.user, "Thông báo thử", "Nếu bạn thấy tin này, thông báo đã hoạt động.", "/tho/"
    )
    messages.info(request, "Đã gửi thông báo thử — kiểm tra điện thoại hoặc Telegram.")
    return redirect("thuc_hien:cai_dat")


# ------------------------------------------------------------------ PWA


@cache_control(max_age=3600)
def manifest(request):
    return JsonResponse(
        {
            "name": "HomeFix Thợ",
            "short_name": "HomeFix",
            "lang": "vi",
            "start_url": "/tho/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#1e293b",
            "icons": [
                {"src": static("img/bieu_tuong_192.png"), "sizes": "192x192", "type": "image/png"},
                {"src": static("img/bieu_tuong_512.png"), "sizes": "512x512", "type": "image/png"},
                {
                    "src": static("img/bieu_tuong_512.png"),
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable",
                },
            ],
        },
        content_type="application/manifest+json",
        json_dumps_params={"ensure_ascii": False},
    )


@cache_control(no_cache=True)
def service_worker(request):
    """Phục vụ ở gốc site để phạm vi (scope) là “/”. Nhận push, mở URL khi chạm thông báo; chỉ cache tệp tĩnh."""
    noi_dung = render(
        request, "thuc_hien/service-worker.js", {"tep_tinh": json.dumps([static("css/tailwind.css")])}
    ).content
    phan_hoi = HttpResponse(noi_dung, content_type="application/javascript; charset=utf-8")
    phan_hoi["Service-Worker-Allowed"] = "/"
    return phan_hoi

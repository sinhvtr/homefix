"""Màn hình thợ trên điện thoại (UC07; PWA). Không có lớp thực thể — chỉ gọi DAO.
NFR04: thợ chỉ thấy SĐT, địa chỉ khách của đơn mình đã nhận; đoán URL đơn/đề nghị khác → 404."""

import json
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST

from apps.danh_muc.dao import ThoDAO
from apps.danh_muc.models import DichVu, Tho
from apps.don_sua_chua.dao import SO_ANH_TOI_DA, HienTruongDAO
from apps.don_sua_chua.models import AnhHienTruong, DonSuaChua, HangMucSuaChua
from apps.don_sua_chua.trang_thai import ChuyenTrangThaiKhongHopLe, TrangThaiDon
from apps.he_thong.cau_hinh import cau_hinh
from apps.tai_chinh.dao import DoiSoatDAO
from apps.tai_chinh.models import ThanhToan
from apps.tai_khoan.models import VaiTro
from apps.tai_khoan.phan_quyen import THO, VAN_PHONG, co_vai_tro, yeu_cau_vai_tro
from apps.thong_bao.dich_vu import DichVuThongBao
from apps.thong_bao.telegram import lien_ket_moi
from apps.tiep_nhan_dieu_phoi.dao import PhanCongDAO
from apps.tiep_nhan_dieu_phoi.models import PhanCong
from apps.tiep_nhan_dieu_phoi.tin_nhan import LY_DO_TU_CHOI_GIA, tin_nhan_cam_on

from .dao import DonSuaChuaDAO as HoanThanhDAO


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


# ------------------------------------------------------------------ UC08–UC10: hiện trường


def _so_nguyen(chuoi, mac_dinh=None):
    """'150.000' / '150000' / '150 000 đ' → 150000; rỗng → mac_dinh."""
    so = "".join(c for c in str(chuoi or "") if c.isdigit())
    return int(so) if so else mac_dinh


def _so_luong(chuoi) -> Decimal:
    try:
        return Decimal(str(chuoi or "1").replace(",", "."))
    except InvalidOperation as loi:
        raise ValidationError("Số lượng không hợp lệ.") from loi


def _don_cua_toi(request, ma_don) -> DonSuaChua:
    try:
        return PhanCongDAO.lay_don_cua_tho(request.user, ma_don)
    except DonSuaChua.DoesNotExist as loi:
        raise Http404 from loi


def _hang_muc_cua_don(don, pk) -> HangMucSuaChua:
    hm = HangMucSuaChua.objects.filter(pk=pk, don=don).select_related("don__tho").first()
    if hm is None:
        raise Http404
    return hm


def _bao_loi(request, loi) -> None:
    messages.error(request, " ".join(getattr(loi, "messages", [str(loi)])))


@require_POST
@yeu_cau_vai_tro(THO)
def den_noi(request, ma_don):
    """Nút “Đã đến nơi” (A-02): sửa chữa → báo giá (T9); vệ sinh → hoàn thành theo bảng giá (T10)."""
    d = _don_cua_toi(request, ma_don)
    try:
        trang_thai = HienTruongDAO.tho_den_noi(request.user, d)
    except (ValidationError, ChuyenTrangThaiKhongHopLe) as loi:
        _bao_loi(request, loi)
        return redirect("thuc_hien:don", ma_don=ma_don)
    if trang_thai == TrangThaiDon.CHO_DUYET_GIA:
        return redirect("thuc_hien:bao_gia", ma_don=ma_don)
    return redirect("thuc_hien:hoan_thanh", ma_don=ma_don)


def _them_dong(request, d) -> None:
    hanh_dong = request.POST.get("hanh_dong")
    if hanh_dong == "them_dich_vu":
        dv = DichVu.objects.filter(pk=_so_nguyen(request.POST.get("dich_vu"), 0), dang_ap_dung=True).first()
        HienTruongDAO.them_hang_muc(
            request.user,
            d,
            {
                "loai": HangMucSuaChua.Loai.CONG,
                "dich_vu": dv,
                "so_luong": _so_luong(request.POST.get("so_luong")),
                "don_gia_thuc_te": _so_nguyen(request.POST.get("don_gia")),
            },
        )
    elif hanh_dong == "them_vat_tu":  # UC10
        HienTruongDAO.them_hang_muc(
            request.user,
            d,
            {
                "loai": HangMucSuaChua.Loai.VAT_TU,
                "mo_ta": request.POST.get("mo_ta", ""),
                "so_luong": _so_luong(request.POST.get("so_luong")),
                "don_gia_thuc_te": _so_nguyen(request.POST.get("don_gia")),
                "gia_mua": _so_nguyen(request.POST.get("gia_mua")),
                "co_hoa_don": request.POST.get("co_hoa_don") == "on",
                "nguoi_ung": request.POST.get("nguoi_ung") or HangMucSuaChua.NguoiUng.THO,
            },
        )
    elif hanh_dong == "xoa":
        HienTruongDAO.xoa_hang_muc(
            request.user, _hang_muc_cua_don(d, _so_nguyen(request.POST.get("hang_muc"), 0))
        )
    elif hanh_dong == "sua":
        HienTruongDAO.sua_hang_muc(
            request.user,
            _hang_muc_cua_don(d, _so_nguyen(request.POST.get("hang_muc"), 0)),
            _so_luong(request.POST.get("so_luong")),
            _so_nguyen(request.POST.get("don_gia"), 0),
        )
    else:
        raise ValidationError("Thao tác không hợp lệ.")


def _ngu_canh_hang_muc(d) -> dict:
    ds = list(d.ds_hang_muc.select_related("dich_vu"))
    return {
        "don": d,
        "ds_hang_muc": ds,
        "tien": d.bang_tinh_tien(ds),
        "ds_dich_vu": DichVu.objects.filter(dang_ap_dung=True).order_by("-loai_thiet_bi", "ten_dich_vu"),
        "ten_vat_tu": HienTruongDAO.goi_y_ten_vat_tu(),
        "nguoi_ung": HangMucSuaChua.NguoiUng.choices,
    }


@yeu_cau_vai_tro(THO)
def bao_gia(request, ma_don):
    """UC08 — chỉ với nhóm sửa chữa ở CHO_DUYET_GIA. Tổng tự tính theo 7.2 (đã trừ VIP)."""
    d = _don_cua_toi(request, ma_don)
    if d.trang_thai != TrangThaiDon.CHO_DUYET_GIA:
        return redirect("thuc_hien:don", ma_don=ma_don)
    if request.method == "POST":
        hanh_dong = request.POST.get("hanh_dong")
        try:
            if hanh_dong == "dong_y":
                if request.FILES.get("anh_bao_gia"):
                    HienTruongDAO.luu_anh(
                        request.user, d, request.FILES["anh_bao_gia"], AnhHienTruong.Loai.BAO_GIA
                    )
                ten = request.POST.get("nguoi_xac_nhan", "").strip() or d.khach_hang.ho_ten
                if HienTruongDAO.khach_duyet_gia(request.user, d, ten):
                    messages.success(request, "Khách đã đồng ý báo giá — bắt đầu sửa.")
                    return redirect("thuc_hien:hoan_thanh", ma_don=ma_don)
                messages.warning(
                    request, "Báo giá từ ngưỡng phải chờ tổng đài gọi khách xác nhận. Đã báo tổng đài."
                )
            elif hanh_dong == "tu_choi":
                HienTruongDAO.khach_tu_choi_gia(
                    request.user, d, request.POST.get("ly_do", "Khách từ chối báo giá")
                )
                messages.info(request, "Đã ghi nhận khách từ chối — đơn đóng lại.")
                return redirect("thuc_hien:trang_chu")
            else:
                _them_dong(request, d)
        except (ValidationError, ChuyenTrangThaiKhongHopLe) as loi:
            _bao_loi(request, loi)
        return redirect("thuc_hien:bao_gia", ma_don=ma_don)
    return render(
        request,
        "thuc_hien/bao_gia.html",
        {**_ngu_canh_hang_muc(d), "ly_do_tu_choi": LY_DO_TU_CHOI_GIA},
    )


@yeu_cau_vai_tro(THO)
def hoan_thanh(request, ma_don):
    """UC09 — một trang cuộn, ít ô nhập: hạng mục → ảnh → tiền đã thu + hình thức → HOÀN THÀNH."""
    d = _don_cua_toi(request, ma_don)
    if d.trang_thai != TrangThaiDon.DANG_SUA:
        return redirect("thuc_hien:don", ma_don=ma_don)
    if request.method == "POST":
        hanh_dong = request.POST.get("hanh_dong")
        try:
            if hanh_dong == "tai_anh":
                ds_tep = request.FILES.getlist("anh")
                if not ds_tep:
                    raise ValidationError("Chọn hoặc chụp ít nhất một ảnh.")
                for tep in ds_tep:
                    HienTruongDAO.luu_anh(request.user, d, tep)
                messages.success(request, f"Đã tải {len(ds_tep)} ảnh.")
            elif hanh_dong == "xoa_anh":
                anh = AnhHienTruong.objects.filter(pk=_so_nguyen(request.POST.get("anh"), 0), don=d).first()
                if anh is None:
                    raise Http404
                HienTruongDAO.xoa_anh(request.user, anh)
            elif hanh_dong == "hoan_thanh":
                kq = HoanThanhDAO.hoan_thanh(
                    request.user,
                    d,
                    _so_nguyen(request.POST.get("so_tien")),
                    request.POST.get("hinh_thuc", ""),
                    request.POST.get("ly_do_lech", ""),
                    request.FILES.get("anh_chung_tu"),
                )
                messages.success(request, "Đã hoàn thành đơn. Gửi tin nhắn cảm ơn cho khách.")
                return redirect("thuc_hien:da_xong", ma_don=kq.don.ma_don)
            else:
                _them_dong(request, d)
                if HienTruongDAO.vuot_bao_gia(DonSuaChua.objects.get(pk=d.pk)):
                    messages.warning(
                        request, "Tổng mới vượt báo giá đã duyệt hơn 10% — cần khách xác nhận lại."
                    )
        except (ValidationError, ChuyenTrangThaiKhongHopLe) as loi:
            _bao_loi(request, loi)
        return redirect("thuc_hien:hoan_thanh", ma_don=ma_don)
    ngu_canh = _ngu_canh_hang_muc(d)
    return render(
        request,
        "thuc_hien/hoan_thanh.html",
        {
            **ngu_canh,
            "ds_anh": d.ds_anh.filter(loai=AnhHienTruong.Loai.HIEN_TRUONG),
            "so_anh_toi_da": SO_ANH_TOI_DA,
            "so_anh_toi_thieu": cau_hinh("SO_ANH_TOI_THIEU_KHI_HOAN_THANH"),
            "hinh_thuc": ThanhToan.HinhThuc.choices,
            "vuot_bao_gia": HienTruongDAO.vuot_bao_gia(d),
        },
    )


@yeu_cau_vai_tro(THO)
def da_xong(request, ma_don):
    """Sau khi hoàn thành: tin nhắn cảm ơn + thông tin bảo hành để thợ sao chép gửi khách."""
    d = DonSuaChua.objects.filter(
        ma_don=ma_don, tho__nguoi_dung=request.user, trang_thai=TrangThaiDon.HOAN_THANH
    ).first()
    if d is None:
        raise Http404
    return render(request, "thuc_hien/da_xong.html", {"don": d, "tin_nhan": tin_nhan_cam_on(d)})


@require_POST
@yeu_cau_vai_tro(THO)
def nguyen_nhan_bao_hanh(request, ma_don):
    """UC11: thợ xác định nguyên nhân đơn bảo hành (tay nghề / vật tư) trước khi hoàn thành."""
    d = _don_cua_toi(request, ma_don)
    try:
        HoanThanhDAO.xac_dinh_nguyen_nhan_bao_hanh(request.user, d, request.POST.get("nguyen_nhan", ""))
        messages.success(request, "Đã ghi nguyên nhân bảo hành.")
    except (ValidationError, ChuyenTrangThaiKhongHopLe) as loi:
        _bao_loi(request, loi)
    if d.trang_thai == TrangThaiDon.DANG_SUA:
        return redirect("thuc_hien:hoan_thanh", ma_don=ma_don)
    return redirect("thuc_hien:don", ma_don=ma_don)


@yeu_cau_vai_tro(THO)
def doi_soat(request):
    """UC12: thợ xem phiếu đối soát của mình (SPEC 3.1: R của mình) kèm các khoản trong phiếu."""
    ds = DoiSoatDAO.danh_sach_phieu(request.user)
    return render(
        request,
        "thuc_hien/doi_soat.html",
        {"ds_phieu": [(p, DoiSoatDAO.dong_cua_phieu(p)) for p in ds[:12]]},
    )


# ------------------------------------------------------------------ ảnh phục vụ qua view có kiểm quyền (NFR04)


def _duoc_xem_cua_don(nguoi_dung, don) -> bool:
    if co_vai_tro(nguoi_dung, *VAN_PHONG):
        return True
    return (
        nguoi_dung.vai_tro == VaiTro.THO and don.tho_id is not None and don.tho.nguoi_dung_id == nguoi_dung.pk
    )


def _tra_anh(tep) -> FileResponse:
    phan_hoi = FileResponse(tep.open("rb"), content_type="image/jpeg")
    phan_hoi["Cache-Control"] = "private, max-age=3600"
    phan_hoi["X-Content-Type-Options"] = "nosniff"
    return phan_hoi


@login_required
def xem_anh(request, pk):
    anh = AnhHienTruong.objects.select_related("don__tho").filter(pk=pk).first()
    if anh is None or not _duoc_xem_cua_don(request.user, anh.don):
        raise Http404
    return _tra_anh(anh.tep)


@login_required
def xem_chung_tu(request, pk):
    tt = ThanhToan.objects.select_related("don__tho").filter(pk=pk).first()
    if tt is None or not tt.anh_chung_tu or not _duoc_xem_cua_don(request.user, tt.don):
        raise Http404
    return _tra_anh(tt.anh_chung_tu)

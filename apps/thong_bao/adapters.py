"""Kênh thông báo (SPEC 11). Đều miễn phí; Zalo ZNS và SMS có phí → để lớp rỗng cho v2.

Mọi kênh chỉ được gọi từ tác vụ nền SAU khi giao dịch đã commit (không gọi mạng trong giao dịch).
"""

import json
import logging
from typing import Protocol

import httpx
from django.conf import settings

from .models import DangKyPush

log = logging.getLogger(__name__)


class KenhThongBao(Protocol):
    ten: str

    def gui(self, nguoi_nhan, tieu_de: str, noi_dung: str, duong_dan: str) -> bool: ...


def _url_day_du(duong_dan: str) -> str:
    if not duong_dan or duong_dan.startswith("http"):
        return duong_dan
    return settings.SITE_URL.rstrip("/") + duong_dan


class ConsoleKenh:
    """In ra log — dùng khi phát triển và kiểm thử."""

    ten = "CONSOLE"

    def gui(self, nguoi_nhan, tieu_de, noi_dung, duong_dan) -> bool:
        log.info("[THÔNG BÁO] → %s: %s — %s (%s)", nguoi_nhan, tieu_de, noi_dung, duong_dan)
        return True


class WebPushKenh:
    """pywebpush + khóa VAPID. Endpoint hết hạn (404/410) → xóa DangKyPush."""

    ten = "WEB_PUSH"

    def gui(self, nguoi_nhan, tieu_de, noi_dung, duong_dan) -> bool:
        from pywebpush import WebPushException, webpush

        if not (settings.VAPID_PRIVATE_KEY and settings.VAPID_EMAIL):
            return False
        du_lieu = json.dumps({"tieu_de": tieu_de, "noi_dung": noi_dung, "duong_dan": duong_dan or "/"})
        thanh_cong = False
        for dk in DangKyPush.objects.filter(nguoi_dung=nguoi_nhan):
            try:
                webpush(
                    subscription_info={
                        "endpoint": dk.endpoint,
                        "keys": {"p256dh": dk.p256dh, "auth": dk.auth},
                    },
                    data=du_lieu,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": f"mailto:{settings.VAPID_EMAIL.removeprefix('mailto:')}"},
                    timeout=10,
                )
                thanh_cong = True
            except WebPushException as loi:
                ma = getattr(getattr(loi, "response", None), "status_code", None)
                if ma in (404, 410):
                    log.info("Xóa đăng ký push hết hạn %s", dk.pk)
                    dk.delete()
                else:
                    log.warning("Web Push lỗi (%s) cho %s: %s", ma, nguoi_nhan, loi)
        return thanh_cong


class TelegramKenh:
    """Gọi Bot API sendMessage bằng httpx. Chat id lấy từ hồ sơ thợ (gắn qua liên kết mời bot)."""

    ten = "TELEGRAM"

    def gui(self, nguoi_nhan, tieu_de, noi_dung, duong_dan) -> bool:
        tho = getattr(nguoi_nhan, "tho", None)  # Tho thuộc app danh_muc (tầng trên) — đọc qua quan hệ ngược
        chat_id = getattr(tho, "telegram_chat_id", None)
        if not (settings.TELEGRAM_BOT_TOKEN and chat_id):
            return False
        van_ban = f"{tieu_de}\n{noi_dung}".strip()
        if duong_dan:
            van_ban += f"\n{_url_day_du(duong_dan)}"
        return gui_tin_telegram(chat_id, van_ban)


def gui_tin_telegram(chat_id, van_ban: str) -> bool:
    try:
        phan_hoi = httpx.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": van_ban},
            timeout=10,
        )
        return phan_hoi.status_code == 200
    except httpx.HTTPError as loi:
        log.warning("Telegram lỗi: %s", loi)
        return False


class ZaloZnsKenh:
    """v2 — có phí (Zalo OA/ZNS)."""

    ten = "ZALO_ZNS"

    def gui(self, nguoi_nhan, tieu_de, noi_dung, duong_dan) -> bool:
        raise NotImplementedError("v2 — có phí")


class SmsKenh:
    """v2 — có phí."""

    ten = "SMS"

    def gui(self, nguoi_nhan, tieu_de, noi_dung, duong_dan) -> bool:
        raise NotImplementedError("v2 — có phí")


def cac_kenh_theo_thu_tu(nguoi_nhan) -> list[KenhThongBao]:
    """Kênh ưu tiên của người nhận trước, kênh còn lại sau (thất bại kênh chính → thử kênh còn lại)."""
    if settings.THONG_BAO_CHI_CONSOLE:
        return [ConsoleKenh()]
    tho = getattr(nguoi_nhan, "tho", None)
    if tho is not None and tho.kenh_thong_bao == "TELEGRAM":
        return [TelegramKenh(), WebPushKenh()]
    return [WebPushKenh(), TelegramKenh()]

"""Gắn tài khoản Telegram của thợ: liên kết https://t.me/<bot>?start=<token> (SPEC 11).

Token không lưu CSDL: `<mã người dùng>-<thời điểm>-<HMAC>` (chỉ gồm ký tự Telegram cho phép), hết hạn sau 24 giờ.
"""

import hashlib
import hmac
import logging
import time

from django.conf import settings
from django.contrib.auth import get_user_model

from .adapters import gui_tin_telegram

log = logging.getLogger(__name__)
HIEU_LUC_GIAY = 24 * 3600


def _chu_ky(chuoi: str) -> str:
    khoa = f"telegram-lien-ket:{settings.SECRET_KEY}".encode()
    return hmac.new(khoa, chuoi.encode(), hashlib.sha256).hexdigest()[:24]


def tao_token(nguoi_dung_id: int, luc: int | None = None) -> str:
    phan = f"{nguoi_dung_id}-{int(luc or time.time())}"
    return f"{phan}-{_chu_ky(phan)}"


def doc_token(token: str, luc: int | None = None) -> int | None:
    try:
        nd_id, thoi_diem, chu_ky = token.split("-")
        if not hmac.compare_digest(chu_ky, _chu_ky(f"{nd_id}-{thoi_diem}")):
            return None
        if int(luc or time.time()) - int(thoi_diem) > HIEU_LUC_GIAY:
            return None
        return int(nd_id)
    except (ValueError, AttributeError):
        return None


def lien_ket_moi(nguoi_dung) -> str:
    return f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={tao_token(nguoi_dung.pk)}"


def xu_ly_cap_nhat(cap_nhat: dict) -> bool:
    """Xử lý một update của Bot API: '/start <token>' → lưu chat id vào hồ sơ thợ. Trả True nếu gắn thành công."""
    tin = cap_nhat.get("message") or {}
    van_ban = (tin.get("text") or "").strip()
    chat_id = (tin.get("chat") or {}).get("id")
    if not van_ban.startswith("/start ") or chat_id is None:
        return False
    nd_id = doc_token(van_ban.split(maxsplit=1)[1])
    nguoi_dung = get_user_model().objects.filter(pk=nd_id, is_active=True).first() if nd_id else None
    tho = getattr(nguoi_dung, "tho", None) if nguoi_dung else None
    if tho is None:
        gui_tin_telegram(
            chat_id, "Liên kết không hợp lệ hoặc đã hết hạn. Hãy lấy liên kết mới trong mục Cài đặt."
        )
        return False
    tho.telegram_chat_id = str(chat_id)
    tho.save(update_fields=["telegram_chat_id", "cap_nhat_luc"])
    log.info("Gắn Telegram cho thợ %s", tho.pk)
    gui_tin_telegram(chat_id, f"Đã gắn Telegram cho {tho.ho_ten}. Bạn sẽ nhận thông báo việc mới tại đây.")
    return True

"""Cấu hình máy chủ thật. Chỉ nghe 127.0.0.1; HTTPS do Tailscale Funnel hoặc Cloudflare Tunnel lo."""

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, SILENCED_SYSTEM_CHECKS, env

DEBUG = False

# Health check của Docker gọi từ bên trong container.
ALLOWED_HOSTS = [*ALLOWED_HOSTS, "localhost", "127.0.0.1"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# HTTPS kết thúc ở tunnel (Tailscale Funnel chỉ mở 443; Cloudflare Tunnel bật "Always Use HTTPS"); gunicorn chỉ nghe
# 127.0.0.1 nên không có đường HTTP từ ngoài vào — chuyển hướng ở Django là thừa và có thể lặp vô hạn nếu tunnel không
# gửi X-Forwarded-Proto. Bật bằng biến môi trường khi chắc chắn tunnel gửi header (A-90).
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
SECURE_REDIRECT_EXEMPT = [r"^suc-khoe/$"]  # health check của Docker gọi http://127.0.0.1
SESSION_COOKIE_SECURE = env.bool("DJANGO_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
# HSTS 1 năm: trình duyệt chỉ ghi nhận header qua HTTPS, nên cách C (mạng nội bộ, HTTP) không bị ảnh hưởng.
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=31_536_000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False  # tên miền *.ts.net / tên miền con không đưa vào danh sách preload được
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Rà soát `check --deploy` (SPEC 15-P6, A-90): hai cảnh báo dưới đây đã xét và chấp nhận có lý do ở trên.
SILENCED_SYSTEM_CHECKS = [*SILENCED_SYSTEM_CHECKS, "security.W008", "security.W021"]

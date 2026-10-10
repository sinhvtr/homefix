"""Cấu hình máy chủ thật. Chỉ nghe 127.0.0.1; HTTPS do Tailscale Funnel hoặc Cloudflare Tunnel lo."""

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, env

DEBUG = False

# Health check của Docker gọi từ bên trong container.
ALLOWED_HOSTS = [*ALLOWED_HOSTS, "localhost", "127.0.0.1"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("DJANGO_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=0)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

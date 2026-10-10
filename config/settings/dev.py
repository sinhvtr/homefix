"""Cấu hình phát triển và kiểm thử."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "dev-khong-dung-cho-may-that")
os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],web,testserver")
os.environ.setdefault("THONG_BAO_CHI_CONSOLE", "1")
os.environ.setdefault("DATABASE_URL", "postgres://homefix:homefix@localhost:5433/homefix")

from .base import *  # noqa: E402,F403

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

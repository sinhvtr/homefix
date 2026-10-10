"""Cấu hình chung cho mọi môi trường. Bí mật đọc từ biến môi trường / .env (SPEC 8.1)."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
SITE_URL = env("SITE_URL", default="http://localhost:8000")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_htmx",
    "django_tailwind_cli",
    "django_q",
    "apps.he_thong",
    "apps.thong_bao",
    "apps.tai_khoan",
    "apps.danh_muc",
    "apps.don_sua_chua",
    "apps.tiep_nhan_dieu_phoi",
    "apps.thuc_hien",
    "apps.tai_chinh",
    "apps.bao_hanh",
    "apps.bao_cao",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.tai_khoan.context_processors.menu_theo_vai_tro",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = False
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Tài khoản ---
AUTH_USER_MODEL = "tai_khoan.NguoiDung"
AUTHENTICATION_BACKENDS = ["apps.tai_khoan.backends.XacThucSdtHoacTenDangNhap"]
LOGIN_URL = "tai_khoan:dang_nhap"
LOGIN_REDIRECT_URL = "tai_khoan:trang_chu"
LOGOUT_REDIRECT_URL = "tai_khoan:dang_nhap"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Ngôn ngữ, thời gian, định dạng số (SPEC 5, 13) ---
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True
FORMAT_MODULE_PATH = ["config.formats"]

# --- Tệp tĩnh và tệp tải lên ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# --- Tailwind (django-tailwind-cli, không cần Node) ---
TAILWIND_CLI_VERSION = "4.1.13"
TAILWIND_CLI_PATH = env("TAILWIND_CLI_PATH", default=".django_tailwind_cli")
TAILWIND_CLI_SRC_CSS = "frontend/nguon.css"
TAILWIND_CLI_DIST_CSS = "css/tailwind.css"

# --- Tác vụ nền: django-q2 dùng PostgreSQL làm hàng đợi (SPEC 2.1) ---
Q_CLUSTER = {
    "name": "homefix",
    "orm": "default",
    "workers": 2,
    "timeout": 120,
    "retry": 180,
    "catch_up": False,
    "label": "Tác vụ nền",
}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- Thông báo (dùng từ P3) ---
VAPID_PUBLIC_KEY = env("VAPID_PUBLIC_KEY", default="")
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", default="")
VAPID_EMAIL = env("VAPID_EMAIL", default="")
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")

BACKUP_KEEP_DAYS = env.int("BACKUP_KEEP_DAYS", default=14)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"don_gian": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "don_gian"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}

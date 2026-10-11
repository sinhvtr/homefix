"""Cấu hình chung cho mọi môi trường. Bí mật đọc từ biến môi trường / .env (SPEC 8.1)."""

from datetime import timedelta
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
    "axes",
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
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "apps.he_thong.nhat_ky.GhiIPNhatKyMiddleware",
    "apps.tai_khoan.middleware.BatDoiMatKhauMiddleware",
    "axes.middleware.AxesMiddleware",
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
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "apps.tai_khoan.backends.XacThucSdtHoacTenDangNhap",
]
LOGIN_URL = "tai_khoan:dang_nhap"
LOGIN_REDIRECT_URL = "tai_khoan:trang_chu"
LOGOUT_REDIRECT_URL = "tai_khoan:dang_nhap"

# Khóa 15 phút sau 5 lần sai liên tiếp (UC01). Khóa theo tài khoản: sau tunnel mọi yêu cầu chung một IP.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_RESET_ON_SUCCESS = True
AXES_USERNAME_CALLABLE = "apps.tai_khoan.backends.ten_dang_nhap_chuan"
AXES_LOCKOUT_TEMPLATE = "tai_khoan/bi_khoa.html"
AXES_VERBOSE = False
# W006 khuyên khóa thêm theo IP; ở đây mọi yêu cầu qua tunnel chung một IP nên cố ý chỉ khóa theo tài khoản.
SILENCED_SYSTEM_CHECKS = ["axes.W006"]

# Thông điệp (có thể chứa mật khẩu tạm/PIN hiện một lần) lưu ở session phía máy chủ, không ở cookie.
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Ngôn ngữ, thời gian, định dạng số (SPEC 5, 13) ---
# Giao diện luôn tiếng Việt (SPEC 13): không dùng LocaleMiddleware để trình duyệt tiếng Anh không đổi định dạng.
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
# Bí mật trong URL webhook Telegram (/telegram/webhook/<secret>/); để trống = tắt webhook, dùng lệnh telegram_poll
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")
# Chỉ in thông báo ra log (ConsoleKenh) thay vì gửi Web Push/Telegram — dùng khi phát triển
THONG_BAO_CHI_CONSOLE = env.bool("THONG_BAO_CHI_CONSOLE", default=False)
# Gửi thông báo đồng bộ ngay sau commit thay vì xếp hàng django-q2 — chỉ dùng khi kiểm thử
THONG_BAO_DONG_BO = env.bool("THONG_BAO_DONG_BO", default=False)

BACKUP_KEEP_DAYS = env.int("BACKUP_KEEP_DAYS", default=14)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"don_gian": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "don_gian"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}

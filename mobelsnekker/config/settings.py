"""Django settings for the Møbelsnekker I&W site.

Configuration comes from environment variables or a `.env` file next to
manage.py (see `.env.example`).  No extra packages are needed for this.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return env(key, str(default)).lower() in ("1", "true", "yes", "on")


def env_list(key, default=""):
    return [x.strip() for x in env(key, default).split(",") if x.strip()]


DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
if not DEBUG and SECRET_KEY.startswith("dev-only"):
    raise RuntimeError("Set DJANGO_SECRET_KEY in production")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3")),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en"
TIME_ZONE = "Europe/Oslo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = Path(env("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Uploads: 5 files x 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_MB = 10

# ---------------------------------------------------------------- email ---
# Where new orders / consultation requests are sent.
NOTIFY_EMAIL = env("NOTIFY_EMAIL", "milkaolder@gmail.com")
# Shown on the site (footer, emails).
CONTACT_EMAIL = env("CONTACT_EMAIL", "client@example.com")
FACEBOOK_URL = env("FACEBOOK_URL", "https://www.facebook.com/share/1BSzNeotP4/?mibextid=wwXIfr")

EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
if EMAIL_HOST_PASSWORD:
    # Gmail: create an App Password (Google account → Security → App passwords)
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(env("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
else:
    # No password configured → emails are printed in the terminal.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", f"Møbelsnekker I&W <{EMAIL_HOST_USER or 'noreply@localhost'}>")
EMAIL_TIMEOUT = 15

# Public address of the site, used for admin links in emails sent by the
# maintenance command (normal submissions use the request host).
SITE_URL = env("SITE_URL", "http://127.0.0.1:8000")

# Uploaded photos are resized/compressed (needs Pillow; pillow-heif for iPhone HEIC)
IMAGE_MAX_SIDE = int(env("IMAGE_MAX_SIDE", "2000"))
IMAGE_QUALITY = int(env("IMAGE_QUALITY", "82"))

# Housekeeping (python manage.py maintenance) — also runs automatically once a day
BACKUP_DIR = Path(env("BACKUP_DIR", str(BASE_DIR / "backups")))
BACKUP_KEEP = int(env("BACKUP_KEEP", "14"))               # number of daily backups kept
BACKUP_INTERVAL_HOURS = int(env("BACKUP_INTERVAL_HOURS", "24"))
RETENTION_DAYS = int(env("RETENTION_DAYS", "365"))         # delete closed requests after this
AUTO_MAINTENANCE = env_bool("AUTO_MAINTENANCE", True)

# Simple rate limit for the public forms (per IP)
FORM_RATE_LIMIT = int(env("FORM_RATE_LIMIT", "8"))      # requests
FORM_RATE_WINDOW = int(env("FORM_RATE_WINDOW", "3600"))  # seconds

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"core": {"handlers": ["console"], "level": "INFO"}},
}

"""
Django settings for prajapati project.

SECURITY NOTE
-------------
This file reads secrets (SECRET_KEY, DEBUG, ALLOWED_HOSTS, Razorpay keys,
DATABASE_URL) from environment variables / a local ``.env`` file instead of
hard-coding them in source control. Copy ``.env.example`` to ``.env`` and
fill in real values before running the project.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


# ── Tiny .env loader (no extra pip package required) ───────────────────────
def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_env_file(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# Whether to store uploaded media (gallery photos, volunteer photos) on
# Cloudflare R2 instead of the local filesystem. See .env.example for the
# R2_* variables this needs. Falls back to local disk storage if False —
# handy for local development without needing an R2 account.
USE_R2_STORAGE = env_bool("USE_R2_STORAGE", default=False)


# ── Core security settings ──────────────────────────────────────────────────
# SECURITY WARNING: never commit a real SECRET_KEY to source control.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")

# SECURITY WARNING: keep DEBUG off in production. Defaults to False now;
# set DJANGO_DEBUG=True in your local .env for development.
DEBUG = env_bool("DJANGO_DEBUG", default=False)

# Refuse to boot in production without a real secret key — a working
# insecure fallback is worse than a loud crash, since it invites the app
# to run "successfully" with a known-public key.
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-local-dev-only-CHANGE-ME"
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY environment variable is not set. "
            "Set it in Railway's Variables tab (or your .env for local dev)."
        )

# SECURITY WARNING: '*' was removed. List real hostnames/IPs via env var,
# comma separated, e.g. DJANGO_ALLOWED_HOSTS=example.com,www.example.com
_default_hosts = "127.0.0.1,localhost" if DEBUG else ""
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", _default_hosts).split(",")
    if h.strip()
]

# Needed for POST requests (donation/join/contact forms) to work once the
# site is behind a real domain — Django checks the Origin/Referer header
# against this list for any unsafe (POST/PUT/DELETE) request.
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',
]

if USE_R2_STORAGE:
    INSTALLED_APPS.append('storages')


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # serves static files in production (no nginx needed)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'prajapati.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'prajapati.wsgi.application'


# ── Database ─────────────────────────────────────────────────────────────
# Reads Railway's DATABASE_URL (postgres://user:pass@host:port/dbname) if
# present; falls back to local SQLite for development when it isn't set.
# No dj-database-url dependency needed — small manual parser below.

def _parse_database_url(url: str) -> dict:
    parsed = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username,
        "PASSWORD": parsed.password,
        "HOST": parsed.hostname,
        "PORT": parsed.port or 5432,
    }


_database_url = os.environ.get("DATABASE_URL", "")

if _database_url:
    DATABASES = {"default": _parse_database_url(_database_url)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('hi', 'Hindi'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]


# Static & media files
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'   # generated by `collectstatic`, not source-controlled
STATICFILES_DIRS = [
    BASE_DIR / 'static',                 # <- source CSS/JS/images live here
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ── Cloudflare R2 media storage (optional) ──────────────────────────────────
# Set USE_R2_STORAGE=True in .env once you've created a bucket at
# https://dash.cloudflare.com -> R2. When False (default), uploaded files
# (gallery photos, volunteer photos) are saved to the local media/ folder.
#
# Required .env variables when USE_R2_STORAGE=True:
#   R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
#   R2_BUCKET_NAME, R2_PUBLIC_URL
if USE_R2_STORAGE:
    R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
    R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "").replace("https://", "").replace("http://", "").rstrip("/")

    AWS_ACCESS_KEY_ID = R2_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = R2_SECRET_ACCESS_KEY
    AWS_STORAGE_BUCKET_NAME = R2_BUCKET_NAME
    AWS_S3_ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    AWS_S3_CUSTOM_DOMAIN = R2_PUBLIC_URL
    AWS_S3_REGION_NAME = "auto"
    AWS_S3_ADDRESSING_STYLE = "virtual"
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False
    AWS_S3_VERIFY = True

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL]):
        import warnings
        warnings.warn(
            "USE_R2_STORAGE=True but one or more R2_* variables are missing in .env "
            "(R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_URL). "
            "File uploads will fail until these are set.",
            stacklevel=2,
        )


# ── Uploads (security: cap request/body size to avoid abuse) ───────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB
FILE_UPLOAD_PERMISSIONS = 0o644


# ── News auto-refresh (see main/views.py _maybe_trigger_background_fetch) ──
NEWS_AUTO_REFRESH_ENABLED = env_bool("NEWS_AUTO_REFRESH_ENABLED", default=True)
NEWS_REFRESH_INTERVAL_HOURS = float(os.environ.get("NEWS_REFRESH_INTERVAL_HOURS", "6"))


# ── Razorpay ────────────────────────────────────────────────────────────────
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")


# ── Security headers ────────────────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # must be readable by JS so fetch() can send the header

# Railway (and most PaaS hosts) terminate HTTPS at a proxy and forward plain
# HTTP internally, adding this header to say "this was actually HTTPS".
# Without it, SECURE_SSL_REDIRECT causes an infinite redirect loop.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# ── Logging (so fetch_news / payment errors are visible, not silently lost) ─
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
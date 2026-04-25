from pathlib import Path
import sqlite3
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Configure SQLite with WAL mode BEFORE Django loads
DB_PATH = BASE_DIR / "db.sqlite3"

def _configure_sqlite_wal():
    """Configure SQLite for better concurrency."""
    if not DB_PATH.exists():
        return

    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=60)
        cursor = conn.cursor()

        # Enable WAL mode - allows concurrent reads during writes
        cursor.execute("PRAGMA journal_mode=WAL;")

        # Increase busy timeout
        cursor.execute("PRAGMA busy_timeout=60000;")  # 60 seconds

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys=ON;")

        # Better performance
        cursor.execute("PRAGMA synchronous=NORMAL;")

        conn.commit()
        conn.close()
        print(f"[DB] SQLite WAL mode configured: {DB_PATH}")
    except Exception as e:
        print(f"[DB] Warning: Could not configure WAL: {e}")

# Run immediately
_configure_sqlite_wal()

# Django settings
SECRET_KEY = "django-insecure-change-me"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "vnstock_web.urls"

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
            ],
        },
    }
]

WSGI_APPLICATION = "vnstock_web.wsgi.application"
ASGI_APPLICATION = "vnstock_web.asgi.application"

# SQLite with WAL mode for better concurrency
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            "timeout": 60,
            "isolation_level": None,  # Autocommit mode, rely on WAL
        },
        "CONN_MAX_AGE": 600,  # Keep connections for 10 minutes
    }
}

# Session engine - use cached sessions to reduce DB load
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "trading-dashboard-cache",
    }
}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "vi-vn"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "dashboard": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

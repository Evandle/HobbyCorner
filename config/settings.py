"""
Django settings for HobbyCorner project.

Vertical-slice layout per CSIT327 guide: feature apps live in apps/<feature>/,
each with its own templates/<feature>/ and static/{css,js,images}/<feature>/.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from .env (DATABASE_URL, SECRET_KEY, etc.)
load_dotenv(BASE_DIR / ".env")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-nm-)_32v-udvi6)txo6nm^fl+j27qsk5-u-dk!a#9cwp6dr029",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h]


# Application definition
# Each feature ("vertical slice") is its own app under apps/.

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Feature apps
    "apps.login",
    "apps.register",
    "apps.home",
    "apps.profile",
    "apps.user_settings",
    "apps.hubs",
    "apps.chat",
    # Shared lookup / model-only apps (no screens of their own yet)
    "apps.locations",
    "apps.ratings",
    "apps.discovery",   # models only; the Discovery screen is not wired in yet
    "apps.dbsecurity",  # turns on Supabase row-level security after migrate
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
        # Project-level templates dir, with one subfolder per feature
        # (templates/login/, templates/register/, etc.) plus base.html
        # for the shared layout shell.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases
#
# Task 2 (Supabase): if DATABASE_URL is set in .env, use Supabase Postgres.
# Otherwise fall back to local SQLite so the project still runs before
# Supabase is wired up (e.g. while grading Task 1/3 in isolation).

DATABASE_URL = os.environ.get("DATABASE_URL")

# "test" check: `manage.py test` must never run against Supabase.
if DATABASE_URL and "test" not in sys.argv:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/
#
# Per the guide: one project-level static/ directory, with feature
# subfolders under css/, js/, and images/ (e.g. static/css/login/login.css).

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media (user-uploaded profile images)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Auth redirects — namespaced per feature app
LOGIN_URL = "login:login"
LOGIN_REDIRECT_URL = "home:home"
LOGOUT_REDIRECT_URL = "login:login"


# Which email domains count as "university" emails. Empty = any valid email.
# Later: UNIVERSITY_EMAIL_DOMAINS=cit.edu in .env (subdomains are included).
UNIVERSITY_EMAIL_DOMAINS = [
    domain.strip().lower().lstrip("@")
    for domain in os.environ.get("UNIVERSITY_EMAIL_DOMAINS", "").split(",")
    if domain.strip()
]

# Email
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

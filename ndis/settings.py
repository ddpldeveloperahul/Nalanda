"""
Django settings for ndis project.
"""

import os
import glob
from datetime import timedelta
from pathlib import Path
from ctypes import CDLL

BASE_DIR = Path(__file__).resolve().parent.parent

# Detect and configure GDAL / GEOS library paths for Windows
HAS_GDAL = False
if os.name == "nt":
    osgeo_dirs = [r"C:\OSGeo4W\bin", r"C:\Program Files\GDAL", r"C:\Program Files\GDAL\bin"]
    for bin_dir in osgeo_dirs:
        if os.path.exists(bin_dir):
            try:
                os.add_dll_directory(bin_dir)
            except Exception:
                pass
            os.environ["PATH"] = bin_dir + os.path.pathsep + os.environ.get("PATH", "")

            # Set PROJ_LIB / PROJ_DATA to point to matching GDAL/OSGeo PROJ database
            proj_candidates = [
                os.path.abspath(os.path.join(bin_dir, "..", "share", "proj")),
                os.path.abspath(os.path.join(bin_dir, "proj")),
                os.path.abspath(os.path.join(bin_dir, "..", "proj")),
            ]
            found_proj = False
            for pdir in proj_candidates:
                if os.path.exists(pdir) and (os.path.exists(os.path.join(pdir, "proj.db")) or os.path.exists(os.path.join(pdir, "proj.ini"))):
                    os.environ["PROJ_LIB"] = pdir
                    os.environ["PROJ_DATA"] = pdir
                    found_proj = True
                    break

            if not found_proj:
                # Remove PROJ environment variables if pointing to incompatible PostgreSQL PostGIS directory
                if "PROJ_LIB" in os.environ and "PostgreSQL" in os.environ["PROJ_LIB"]:
                    del os.environ["PROJ_LIB"]
                if "PROJ_DATA" in os.environ and "PostgreSQL" in os.environ["PROJ_DATA"]:
                    del os.environ["PROJ_DATA"]
            
            gdal_candidates = sorted(glob.glob(os.path.join(bin_dir, "gdal3*.dll")), reverse=True) + \
                              sorted(glob.glob(os.path.join(bin_dir, "gdal*.dll")), reverse=True)
            for dll in gdal_candidates:
                try:
                    CDLL(dll)
                    GDAL_LIBRARY_PATH = dll
                    break
                except Exception:
                    pass
            
            geos_dll = os.path.join(bin_dir, "geos_c.dll")
            if os.path.exists(geos_dll):
                GEOS_LIBRARY_PATH = geos_dll
            
            if "GDAL_LIBRARY_PATH" in locals():
                break

try:
    from django.contrib.gis.gdal.libgdal import lgdal
    if lgdal:
        HAS_GDAL = True
except Exception:
    HAS_GDAL = False

SECRET_KEY = "django-insecure-yk)_v0g#miecee=(hbth9m()ge1mji0=c$q_xtknfz&6v2(z!-"

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "myapp",
]

if HAS_GDAL:
    INSTALLED_APPS.insert(6, "django.contrib.gis")

AUTH_USER_MODEL = "myapp.User"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ndis.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "ndis.wsgi.application"

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }
db_engine = 'django.contrib.gis.db.backends.postgis' if HAS_GDAL else 'django.db.backends.postgresql'

DATABASES = {
    'default': {
        'ENGINE': db_engine,
        'NAME': 'nalanda',
        'USER': 'postgres',
        'PASSWORD': 'rahul',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}


STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ==========================================
# SMTP EMAIL CONFIGURATION (Gmail SMTP)
# ==========================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = "faizansari715@gmail.com"
EMAIL_HOST_PASSWORD = "byvy roaw geop lcyc"
DEFAULT_FROM_EMAIL = "NDISP Portal <faizansari715@gmail.com>"
from pathlib import Path

try:
    import django_stubs_ext

    django_stubs_ext.monkeypatch()
except ImportError:
    pass

DEBUG = True
SECRET_KEY = "psst"
USE_TZ = True
USE_I18N = True
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"

STATIC_ROOT = Path(__file__).parent / "global_static"
STATIC_URL = "/static/"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(__file__).parent / "test.db",
    }
}


INSTALLED_APPS = [
    "autotranslate",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
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

SESSION_ENGINE = "django.contrib.sessions.backends.db"

SITE_ID = 1

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROOT_URLCONF = "tests.urls"

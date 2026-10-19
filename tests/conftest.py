from urllib.parse import urlsplit

import django
from django.conf import settings

from tests.settings import DATABASE_URL

# Configured at import time, not in a pytest hook: conftest files below this one import the
# Django models and are loaded before session hooks run when their directory is targeted.
url = urlsplit(DATABASE_URL)
settings.configure(
    INSTALLED_APPS=[
        "tests.django",
    ],
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": url.path.lstrip("/"),
            "USER": url.username,
            "PASSWORD": url.password,
            "HOST": url.hostname,
            "PORT": url.port,
        }
    },
)
django.setup()

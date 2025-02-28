def pytest_sessionstart(session):
    import django
    from django.conf import settings

    settings.configure(
        INSTALLED_APPS=[
            "tests.builders.django",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
    )
    django.setup()

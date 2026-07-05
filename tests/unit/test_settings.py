from django.conf import settings


def test_argon2id_is_primary_password_hasher() -> None:
    assert settings.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"


def test_hardened_cookie_flags() -> None:
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"


def test_custom_user_model_is_the_stub() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_strong_password_floor() -> None:
    min_length = next(
        v["OPTIONS"]["min_length"]
        for v in settings.AUTH_PASSWORD_VALIDATORS
        if v["NAME"].endswith("MinimumLengthValidator")
    )
    assert min_length >= 16

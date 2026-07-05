import pytest

from hw_radar.accounts.models import User


@pytest.mark.django_db
def test_password_hash_is_argon2id() -> None:
    user = User.objects.create_user(username="owner", password="a-strong-password-123!")
    assert user.password.startswith("argon2$argon2id$")
    assert user.check_password("a-strong-password-123!")


@pytest.mark.django_db
def test_users_table_name_matches_spec() -> None:
    assert User._meta.db_table == "users"

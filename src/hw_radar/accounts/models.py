from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Single-account stub (ADR-0005).

    No extra fields yet. The custom model exists so multi-user growth is
    additive: AUTH_USER_MODEL cannot be changed after the first migration.
    """

    class Meta:
        db_table = "users"

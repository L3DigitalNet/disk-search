from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from hw_radar import __version__


def _release() -> str:
    release_file = settings.BASE_DIR / "RELEASE"
    try:
        return release_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"


def healthz(request: HttpRequest) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_ok = cursor.fetchone() == (1,)
    except DatabaseError:
        db_ok = False
    payload = {
        "status": "ok" if db_ok else "degraded",
        "version": __version__,
        "release": _release(),
        "database": db_ok,
    }
    return JsonResponse(payload, status=200 if db_ok else 503)


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "web/dashboard.html", {"version": __version__, "release": _release()})

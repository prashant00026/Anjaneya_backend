"""Health-check endpoints for nginx / uptime monitoring / deploy scripts.

  /health/        — liveness:  is the process up? (no dependencies touched)
  /health/ready/  — readiness: can it reach Postgres + Redis?
"""

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt


@never_cache
@csrf_exempt
def health(request):
    """Liveness probe — 200 as long as the WSGI process is serving."""
    return JsonResponse({"status": "ok"})


@never_cache
@csrf_exempt
def health_ready(request):
    """Readiness probe — checks the database and cache backends.

    Returns 200 when both are reachable, 503 (degraded) otherwise. The
    deploy script polls this after `systemctl reload` to confirm the
    new code came up healthy.
    """
    checks = {}
    ok = True

    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"
        ok = False

    try:
        cache.set("__health__", "ok", 10)
        assert cache.get("__health__") == "ok"
        checks["cache"] = "ok"
    except Exception as e:
        checks["cache"] = f"error: {type(e).__name__}"
        ok = False

    return JsonResponse(
        {"status": "ok" if ok else "degraded", "checks": checks},
        status=200 if ok else 503,
    )

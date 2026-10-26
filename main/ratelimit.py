from functools import wraps

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse


def get_client_ip(request):
    # Cloudflare ke peeche asli IP is header me aata hai
    ip = request.META.get("HTTP_CF_CONNECTING_IP")
    if not ip:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")
    return ip or "unknown"


def ratelimit(name, limit, window, as_json=False):
    """
    Sirf POST requests count hoti hain.
    name   : bucket ka naam (har view ka alag)
    limit  : window ke andar max kitni POST allowed
    window : seconds
    """
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method != "POST":
                return view(request, *args, **kwargs)

            key = f"rl:{name}:{get_client_ip(request)}"
            cache.add(key, 0, timeout=window)
            try:
                count = cache.incr(key)
            except ValueError:
                cache.set(key, 1, timeout=window)
                count = 1

            if count > limit:
                msg = "Bahut zyada requests aa gayi hain. Kripya thodi der baad try karein."
                if as_json:
                    return JsonResponse({"ok": False, "error": msg}, status=429)
                return HttpResponse(msg, status=429, content_type="text/plain; charset=utf-8")

            return view(request, *args, **kwargs)
        return wrapper
    return decorator
import hashlib
import hmac
import json
import logging
import threading

import requests as http
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import connections
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .forms import ContactForm, StudentHelpForm, VolunteerForm
from .models import Donation, GalleryImage, GovScheme, News, SchemeUpdate, Volunteer
from .ratelimit import ratelimit

logger = logging.getLogger(__name__)

HOME_CAROUSEL_LIMIT = 8
GALLERY_PAGE_SIZE = 24
VOLUNTEER_PAGE_SIZE = 20
ABOUT_VOLUNTEER_PREVIEW = 10


# ─────────────────────────────────────────────────────────────────────────
# Small helpers
# ─────────────────────────────────────────────────────────────────────────

def _same(a, b) -> bool:
    """Constant-time compare. Bytes me encode karte hain taaki non-ASCII
    input pe TypeError (500) na aaye."""
    return hmac.compare_digest(
        str(a or "").encode("utf-8"),
        str(b or "").encode("utf-8"),
    )


def _json_body(request):
    """Request body ko dict me parse karo, galat ho to None."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


# ─────────────────────────────────────────────────────────────────────────
# Public pages
# ─────────────────────────────────────────────────────────────────────────

def home(request):
    # Carousel ke liye sirf latest few photos, poori gallery load nahi hogi
    images = list(GalleryImage.objects.order_by("-uploaded_at")[:HOME_CAROUSEL_LIMIT])
    return render(request, "pages/index.html", {"images": images})


@ratelimit("join", limit=10, window=3600)
def join(request):
    if request.method == "POST":
        form = VolunteerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Application submitted successfully!")
            return redirect("join")
        messages.error(request, "Kuch fields sahi se bharein aur dobara try karein.")
        return render(request, "pages/join.html", {"form": form})

    return render(request, "pages/join.html", {"form": VolunteerForm()})


def volunteers(request):
    qs = Volunteer.objects.filter(approved=True).order_by("-created")
    page_obj = Paginator(qs, VOLUNTEER_PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "pages/volunteers.html", {
        "volunteers": page_obj,
        "page_obj": page_obj,
    })


def about(request):
    # About page pe sirf preview, poori list /volunteers/ pe hai
    approved = list(
        Volunteer.objects.filter(approved=True).order_by("-created")[:ABOUT_VOLUNTEER_PREVIEW]
    )
    return render(request, "pages/about.html", {"volunteers": approved})


def gallery(request):
    qs = GalleryImage.objects.order_by("-uploaded_at")
    page_obj = Paginator(qs, GALLERY_PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "pages/gallery.html", {
        "images": page_obj,
        "page_obj": page_obj,
    })


@ratelimit("education", limit=10, window=3600)
def education(request):
    if request.method == "POST":
        form = StudentHelpForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Request submitted successfully")
            return redirect("education")
        messages.error(request, "Kuch fields sahi se bharein aur dobara try karein.")
        return render(request, "pages/education.html", {"form": form})

    return render(request, "pages/education.html", {"form": StudentHelpForm()})


@ratelimit("contact", limit=10, window=3600)
def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Message sent successfully")
            return redirect("contact")
        messages.error(request, "Kuch fields sahi se bharein aur dobara try karein.")
        return render(request, "pages/contact.html", {"form": form})

    return render(request, "pages/contact.html", {"form": ContactForm()})


# ─────────────────────────────────────────────────────────────────────────
# Donations (Razorpay)
#
# Flow:
#   1. create-order: server amount + donor info Razorpay order ke notes me rakhta hai
#   2. Razorpay Checkout chalta hai
#   3. save: signature verify, phir order Razorpay se fetch karke amount/notes
#      wahin se lete hain (browser ka amount ignore)
#   4. webhook: browser band ho jaye tab bhi payment.captured se record bane
# ─────────────────────────────────────────────────────────────────────────

RZP_API = "https://api.razorpay.com/v1"
MAX_DONATION = 1_000_000  # ₹10 lakh


def _rzp_auth():
    return (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)


def _fetch_order(order_id):
    r = http.get(f"{RZP_API}/orders/{order_id}", auth=_rzp_auth(), timeout=10)
    r.raise_for_status()
    return r.json()


def _record_donation(order, payment_id, fallback=None):
    """
    Idempotent: same payment_id dobara aaye (save + webhook) to duplicate nahi banta.
    Amount order se aata hai (server-decided). Agar pehle amount 0 save hua tha
    (Razorpay fetch fail hua) to baad me sahi amount se update ho jaata hai.
    """
    fallback = fallback or {}
    notes = order.get("notes")
    if not isinstance(notes, dict):   # Razorpay khaali notes ko [] bhejta hai
        notes = {}

    name = str(notes.get("name") or fallback.get("name") or "").strip()[:200] or "Anonymous"
    email = str(notes.get("email") or fallback.get("email") or "").strip()[:254]
    show_public = notes.get("show_public") == "1"

    try:
        amount = int(order.get("amount") or 0) // 100   # paise -> rupees
    except (ValueError, TypeError):
        amount = 0

    donation, created = Donation.objects.get_or_create(
        payment_id=payment_id,
        defaults={
            "name": name,
            "email": email,
            "amount": amount,
            "razorpay_order_id": str(order.get("id") or ""),
            "show_public": show_public,
        },
    )
    if not created and donation.amount == 0 and amount > 0:
        donation.amount = amount
        donation.save(update_fields=["amount"])
    return donation


@ensure_csrf_cookie
def donation(request):
    donors = Donation.objects.filter(show_public=True).order_by("-created")[:12]
    return render(request, "pages/donation.html", {
        "donors": donors,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    })


@ratelimit("create_order", limit=20, window=600, as_json=True)
@require_POST
def donation_create_order(request):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        logger.error("Razorpay keys configured nahi hain.")
        return JsonResponse({"ok": False, "error": "Payments abhi available nahi hain."}, status=503)

    data = _json_body(request)
    if data is None:
        return JsonResponse({"ok": False, "error": "Invalid request."}, status=400)

    try:
        amount = int(data.get("amount", 0))
    except (ValueError, TypeError, OverflowError):
        return JsonResponse({"ok": False, "error": "Invalid request."}, status=400)

    if amount < 1 or amount > MAX_DONATION:
        return JsonResponse({"ok": False, "error": "Please enter a valid amount."}, status=400)

    name = str(data.get("name") or "").strip()[:200]
    if len(name) < 2:
        return JsonResponse({"ok": False, "error": "Please enter your name."}, status=400)
    email = str(data.get("email") or "").strip()[:254]

    try:
        resp = http.post(
            f"{RZP_API}/orders",
            auth=_rzp_auth(),
            json={
                "amount": amount * 100,  # paise
                "currency": "INR",
                "payment_capture": 1,    # auto-capture, taaki payment.captured webhook aaye
                "notes": {
                    "name": name,
                    "email": email,
                    "show_public": "1" if data.get("show_public") is True else "0",
                },
            },
            timeout=10,
        )
        resp.raise_for_status()
        order = resp.json()
    except (http.RequestException, ValueError) as exc:
        logger.error("Razorpay order creation failed: %s", exc)
        return JsonResponse({"ok": False, "error": "Could not start payment. Try again."}, status=502)

    return JsonResponse({
        "ok": True,
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key": settings.RAZORPAY_KEY_ID,
    })


@require_POST
def donation_save(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"ok": False, "error": "Invalid request."}, status=400)

    order_id = str(data.get("razorpay_order_id") or "").strip()
    payment_id = str(data.get("razorpay_payment_id") or "").strip()
    signature = str(data.get("razorpay_signature") or "").strip()

    if not (order_id and payment_id and signature):
        return JsonResponse({"ok": False, "error": "Missing payment details."}, status=400)

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        logger.error("Razorpay keys not configured; refusing to trust unverified payment.")
        return JsonResponse({"ok": False, "error": "Payments are not configured yet."}, status=503)

    # 1) Signature verify (order_id|payment_id)
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not _same(expected_signature, signature):
        logger.warning("Razorpay signature mismatch for order %s", order_id)
        return JsonResponse({"ok": False, "error": "Payment verification failed."}, status=400)

    # 2) Amount/notes browser se NAHI, Razorpay ke order se lo
    try:
        order = _fetch_order(order_id)
    except (http.RequestException, ValueError) as exc:
        # Payment genuine hai (signature match hua), isliye record to banega,
        # amount 0 rahega; webhook baad me sahi amount se update kar dega.
        logger.error("Could not fetch Razorpay order %s: %s", order_id, exc)
        order = {"id": order_id, "amount": 0, "notes": {}}

    _record_donation(
        order,
        payment_id,
        fallback={"name": data.get("name"), "email": data.get("email")},
    )
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def donation_webhook(request):
    """Razorpay webhook (payment.captured). Signature se verify hota hai, CSRF ki zaroorat nahi."""
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if not secret:
        logger.error("RAZORPAY_WEBHOOK_SECRET set nahi hai; webhook reject.")
        return JsonResponse({"ok": False}, status=503)

    body = request.body
    sig = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not _same(expected, sig):
        logger.warning("Razorpay webhook signature mismatch")
        return JsonResponse({"ok": False}, status=400)

    try:
        event = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"ok": False}, status=400)

    if isinstance(event, dict) and event.get("event") == "payment.captured":
        try:
            pay = event["payload"]["payment"]["entity"]
            order_id, payment_id = pay.get("order_id"), pay.get("id")
        except (KeyError, TypeError, AttributeError):
            return JsonResponse({"ok": False}, status=400)

        if order_id and payment_id:
            try:
                _record_donation(_fetch_order(order_id), payment_id)
            except (http.RequestException, ValueError):
                logger.exception("Webhook: order fetch failed for %s", order_id)
                return JsonResponse({"ok": False}, status=500)  # Razorpay retry karega

    # Baaki events pe bhi 200, warna Razorpay baar-baar retry karega
    return JsonResponse({"ok": True})


# ─────────────────────────────────────────────────────────────────────────
# News
#
# Auto-fetch request ke andar nahi chalta. External cron (cron-job.org) se
# neeche wale /cron/ endpoints ko POST karo (header: X-Cron-Key), ya
# manually: python manage.py fetch_news
# ─────────────────────────────────────────────────────────────────────────

def news(request):
    """URL: /news/?category=<category name>"""
    category = request.GET.get("category", "").strip()

    qs = News.objects.order_by("-published_date")
    if category:
        qs = qs.filter(category=category)

    news_list = list(qs[:30])
    trending = list(News.objects.order_by("-published_date")[:6])

    categories = (
        News.objects.exclude(category="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    return render(request, "pages/news.html", {
        "news_list": news_list,
        "trending": trending,
        "categories": categories,
        "active_category": category,
    })


def _cron_authorized(request) -> bool:
    secret = getattr(settings, "CRON_SECRET", "")
    key = request.headers.get("X-Cron-Key", "")
    # CRON_SECRET empty ho to endpoint band rahega
    return bool(secret) and _same(key, secret)


def _run_in_background(fn, label):
    """Kaam thread me chalao taaki cron ko turant response mile (gunicorn timeout se bachav)."""
    def _run():
        try:
            logger.info("%s finished: %s", label, fn())
        except Exception:
            logger.exception("%s failed", label)
        finally:
            connections.close_all()   # thread ka DB connection band

    threading.Thread(target=_run, daemon=True).start()


@csrf_exempt
@require_POST
def _fetch_news_and_cleanup():
    from . import news_fetcher
    from .cleanup import cleanup_old_entries

    stats = news_fetcher.fetch_news()
    stats["cleanup"] = cleanup_old_entries()
    return stats
def cron_fetch_news(request):
    """curl -X POST -H "X-Cron-Key: <CRON_SECRET>" https://prajapatifoundation.in/cron/fetch-news/"""
    if not _cron_authorized(request):
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

    from . import news_fetcher
    _run_in_background(news_fetcher.fetch_news, "News fetch")
    return JsonResponse({"ok": True, "started": True}, status=202)


@csrf_exempt
@require_POST
def cron_fetch_schemes(request):
    """curl -X POST -H "X-Cron-Key: <CRON_SECRET>" https://prajapatifoundation.in/cron/fetch-schemes/"""
    if not _cron_authorized(request):
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

    from . import scheme_fetcher
    _run_in_background(scheme_fetcher.fetch_scheme_updates, "Scheme fetch")
    return JsonResponse({"ok": True, "started": True}, status=202)


# ─────────────────────────────────────────────────────────────────────────
# Artisan Support
# ─────────────────────────────────────────────────────────────────────────

def artisan_support(request):
    """Curated schemes + PIB se auto-fetched announcements."""
    category = request.GET.get("category", "").strip()

    schemes_qs = GovScheme.objects.filter(is_active=True)
    updates_qs = SchemeUpdate.objects.all()
    if category:
        schemes_qs = schemes_qs.filter(category=category)
        updates_qs = updates_qs.filter(category=category)

    return render(request, "pages/artisan_support.html", {
        "schemes": schemes_qs,
        "updates": updates_qs[:15],
        "categories": GovScheme.CATEGORY_CHOICES,
        "active_category": category,
    })
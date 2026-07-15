import razorpay
import hashlib
import hmac
import json
import logging
import threading
import time

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import ContactForm, StudentHelpForm, VolunteerForm
from .models import Donation, GalleryImage, News, Volunteer

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Public pages
# ─────────────────────────────────────────────────────────────────────────

def home(request):
    images = GalleryImage.objects.all()
    return render(request, 'pages/index.html', {'images': images})


def join(request):
    if request.method == "POST":
        form = VolunteerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Application submitted successfully!")
            return redirect('join')
        messages.error(request, "Kuch fields sahi se bharein aur dobara try karein.")
        return render(request, 'pages/join.html', {'form': form})

    return render(request, 'pages/join.html', {'form': VolunteerForm()})


def volunteers(request):
    approved_volunteers = Volunteer.objects.filter(approved=True)
    return render(request, 'pages/volunteers.html', {'volunteers': approved_volunteers})


def about(request):
    approved_volunteers = Volunteer.objects.filter(approved=True)
    return render(request, 'pages/about.html', {'volunteers': approved_volunteers})


def gallery(request):
    images = GalleryImage.objects.all().order_by("-uploaded_at")
    return render(request, "pages/gallery.html", {"images": images})


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


def donation(request):
    donors = Donation.objects.filter(show_public=True).order_by('-created')[:12]
    return render(request, "pages/donation.html", {
        "donors": donors,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    })


# ─────────────────────────────────────────────────────────────────────────
# Razorpay — secure order creation + signature-verified save
#
# SECURITY: the old implementation trusted whatever "amount" and
# "payment_id" the browser sent to /donation/save/, with @csrf_exempt and
# no verification at all — anyone could POST a fake payment_id and amount
# to create bogus "successful donation" records without paying anything.
#
# Fixed flow:
#   1. Browser asks the server to create a Razorpay Order (server decides
#      the amount that goes to Razorpay).
#   2. Razorpay Checkout runs using that order_id.
#   3. On success, the browser sends the order_id + payment_id + signature
#      back to the server, which recomputes the HMAC-SHA256 signature with
#      the secret key and only saves the donation if it matches.
#
# NOTE: both endpoints below require CSRF tokens (no @csrf_exempt). Make
# sure the donation page includes {% csrf_token %} somewhere so the
# csrftoken cookie is set, and that the frontend JS sends it via the
# X-CSRFToken header on both fetch() calls.
# ─────────────────────────────────────────────────────────────────────────

@require_POST
def donation_create_order(request):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        logger.error("Razorpay keys are not configured (see .env.example).")
        return JsonResponse({"ok": False, "error": "Payments are not configured yet."}, status=503)

    try:
        data = json.loads(request.body.decode("utf-8"))
        amount = int(data.get("amount", 0))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Invalid request."}, status=400)

    if amount < 1 or amount > 1_000_000:
        return JsonResponse({"ok": False, "error": "Please enter a valid amount."}, status=400)

    import requests as http  # local import keeps module import light for non-donation pages

    try:
        resp = http.post(
            "https://api.razorpay.com/v1/orders",
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
            json={
                "amount": amount * 100,   # paise
                "currency": "INR",
                "payment_capture": 1,
            },
            timeout=10,
        )
        resp.raise_for_status()
        order = resp.json()
    except http.RequestException as exc:
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
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid request."}, status=400)

    order_id = (data.get("razorpay_order_id") or "").strip()
    payment_id = (data.get("razorpay_payment_id") or "").strip()
    signature = (data.get("razorpay_signature") or "").strip()

    if not (order_id and payment_id and signature):
        return JsonResponse({"ok": False, "error": "Missing payment details."}, status=400)

    if Donation.objects.filter(payment_id=payment_id).exists():
        # Already recorded (e.g. duplicate callback) — treat as success, don't duplicate.
        return JsonResponse({"ok": True})

    if not settings.RAZORPAY_KEY_SECRET:
        logger.error("Razorpay secret is not configured; refusing to trust unverified payment.")
        return JsonResponse({"ok": False, "error": "Payments are not configured yet."}, status=503)

    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        logger.warning("Razorpay signature mismatch for order %s", order_id)
        return JsonResponse({"ok": False, "error": "Payment verification failed."}, status=400)

    name = (data.get("name") or "").strip()[:200] or "Anonymous"
    email = (data.get("email") or "").strip()[:254]

    try:
        amount = int(data.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0
    if amount < 1:
        amount = 0

    Donation.objects.create(
        name=name,
        email=email,
        amount=amount,
        razorpay_order_id=order_id,
        payment_id=payment_id,
        show_public=True,
    )

    return JsonResponse({"ok": True})


# ─────────────────────────────────────────────────────────────────────────
# News — category filter + lightweight "auto refresh" so the page always
# tries to keep itself current without needing someone to run a command
# by hand. A real cron job / `python manage.py fetch_news` is still the
# most reliable option for production (see README), this is a best-effort
# fallback that runs in a background thread so page loads stay fast.
# ─────────────────────────────────────────────────────────────────────────

NEWS_FETCH_COOLDOWN_SECONDS = 15 * 60       # never attempt more than once / 15 min
_FETCH_LOCK_KEY = "news_fetch_in_progress"


def _maybe_trigger_background_fetch():
    """Kick off a background news fetch if data looks stale. Non-blocking."""
    if not getattr(settings, "NEWS_AUTO_REFRESH_ENABLED", True):
        return

    if cache.get(_FETCH_LOCK_KEY):
        return  # a fetch is already running or ran very recently

    stale_after_seconds = getattr(settings, "NEWS_REFRESH_INTERVAL_HOURS", 6) * 3600

    latest = News.objects.order_by("-created_at").values_list("created_at", flat=True).first()
    is_stale = latest is None or (time.time() - latest.timestamp()) > stale_after_seconds

    if not is_stale:
        return

    # Set the cooldown flag immediately so concurrent requests don't all spawn threads.
    cache.set(_FETCH_LOCK_KEY, True, timeout=NEWS_FETCH_COOLDOWN_SECONDS)

    def _run():
        try:
            from . import news_fetcher
            stats = news_fetcher.fetch_news()
            logger.info("Auto news fetch finished: %s", stats)
        except Exception:
            logger.exception("Background news fetch failed")

    threading.Thread(target=_run, daemon=True).start()


def news(request):
    """
    News page — category filter support.
    URL: /news/?category=<category name>
    """
    category = request.GET.get("category", "").strip()

    _maybe_trigger_background_fetch()

    qs = News.objects.all().order_by("-published_date")
    if category:
        qs = qs.filter(category=category)

    news_list = qs[:30]
    trending = News.objects.all().order_by("-published_date")[:6]

    categories = (
        News.objects
        .values_list("category", flat=True)
        .exclude(category="")
        .distinct()
        .order_by("category")
    )

    return render(request, "pages/news.html", {
        "news_list": news_list,
        "trending": trending,
        "categories": categories,
        "active_category": category,
    })
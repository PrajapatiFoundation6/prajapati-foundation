import hashlib
import hmac
import json
import logging

import requests as http
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .forms import ContactForm, StudentHelpForm, VolunteerForm
from .models import Donation, GalleryImage, GovScheme, News, SchemeUpdate, Volunteer

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Public pages
# ─────────────────────────────────────────────────────────────────────────

def home(request):
    # Carousel ke liye sirf latest 6, poori gallery load nahi hogi
    images = GalleryImage.objects.order_by("-uploaded_at")[:6]
    return render(request, "pages/index.html", {"images": images})


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
    approved = Volunteer.objects.filter(approved=True)
    return render(request, "pages/volunteers.html", {"volunteers": approved})


def about(request):
    approved = Volunteer.objects.filter(approved=True)
    return render(request, "pages/about.html", {"volunteers": approved})


def gallery(request):
    # Abhi pagination template me nahi hai, isliye safe cap lagaya
    images = GalleryImage.objects.order_by("-uploaded_at")[:60]
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


# ─────────────────────────────────────────────────────────────────────────
# Donations (Razorpay)
#
# Flow:
#   1. create-order: server amount + donor info Razorpay order me (notes) rakhta hai
#   2. Checkout chalta hai
#   3. save: signature verify, phir order Razorpay se fetch karke
#      status == paid aur amount_paid wahin se lete hain (browser ka amount ignore)
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


def _record_donation(order, payment_id):
    """Idempotent: same payment_id dobara aaye to duplicate nahi banta."""
    notes = order.get("notes") or {}
    return Donation.objects.get_or_create(
        payment_id=payment_id,
        defaults={
            "name": (notes.get("name") or "Anonymous")[:200],
            "email": (notes.get("email") or "")[:254],
            "amount": int(order.get("amount_paid", 0)) // 100,
            "razorpay_order_id": order["id"],
            "show_public": notes.get("show_public") == "1",
        },
    )


@ensure_csrf_cookie
def donation(request):
    donors = Donation.objects.filter(show_public=True).order_by("-created")[:12]
    return render(request, "pages/donation.html", {
        "donors": donors,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    })


@require_POST
def donation_create_order(request):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        logger.error("Razorpay keys configured nahi hain.")
        return JsonResponse({"ok": False, "error": "Payments abhi available nahi hain."}, status=503)

    try:
        data = json.loads(request.body.decode("utf-8"))
        amount = int(data.get("amount", 0))
    except (ValueError, TypeError, json.JSONDecodeError):
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
                "notes": {
                    "name": name,
                    "email": email,
                    "show_public": "1" if data.get("show_public") else "0",
                },
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

    order_id = str(data.get("razorpay_order_id") or "").strip()
    payment_id = str(data.get("razorpay_payment_id") or "").strip()
    signature = str(data.get("razorpay_signature") or "").strip()

    if not (order_id and payment_id and signature):
        return JsonResponse({"ok": False, "error": "Missing payment details."}, status=400)

    if not settings.RAZORPAY_KEY_SECRET:
        return JsonResponse({"ok": False, "error": "Payments abhi available nahi hain."}, status=503)

    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        logger.warning("Razorpay signature mismatch for order %s", order_id)
        return JsonResponse({"ok": False, "error": "Payment verification failed."}, status=400)

    try:
        order = _fetch_order(order_id)
    except http.RequestException as exc:
        logger.error("Order fetch failed (%s): %s", order_id, exc)
        return JsonResponse({"ok": False, "error": "Verification pending."}, status=502)

    if order.get("status") != "paid":
        return JsonResponse({"ok": False, "error": "Payment not completed."}, status=400)

    _record_donation(order, payment_id)
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def donation_webhook(request):
    """Razorpay webhook (payment.captured). Signature se verify hota hai, CSRF ki zaroorat nahi."""
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        return JsonResponse({"ok": False}, status=503)

    body = request.body
    sig = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return JsonResponse({"ok": False}, status=400)

    try:
        event = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False}, status=400)

    if event.get("event") == "payment.captured":
        pay = event.get("payload", {}).get("payment", {}).get("entity", {})
        order_id, payment_id = pay.get("order_id"), pay.get("id")
        if order_id and payment_id:
            try:
                _record_donation(_fetch_order(order_id), payment_id)
            except http.RequestException:
                return JsonResponse({"ok": False}, status=500)  # Razorpay retry karega

    return JsonResponse({"ok": True})


# ─────────────────────────────────────────────────────────────────────────
# News
#
# Auto-fetch ab request ke andar thread me nahi chalta (gunicorn workers me
# unreliable tha). Cron se chalao:
#   python manage.py fetch_news
# ya neeche wale /cron/ endpoints ko external cron se POST karo.
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
    secret = settings.CRON_SECRET
    key = request.headers.get("X-Cron-Key", "")
    # CRON_SECRET empty ho to endpoint band rahega
    return bool(secret) and hmac.compare_digest(key, secret)


@csrf_exempt
@require_POST
def cron_fetch_news(request):
    """curl -X POST -H "X-Cron-Key: <CRON_SECRET>" https://prajapatifoundation.in/cron/fetch-news/"""
    if not _cron_authorized(request):
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

    from . import news_fetcher
    stats = news_fetcher.fetch_news()
    return JsonResponse({"ok": True, "stats": stats})


@csrf_exempt
@require_POST
def cron_fetch_schemes(request):
    """curl -X POST -H "X-Cron-Key: <CRON_SECRET>" https://prajapatifoundation.in/cron/fetch-schemes/"""
    if not _cron_authorized(request):
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

    from . import scheme_fetcher
    stats = scheme_fetcher.fetch_scheme_updates()
    return JsonResponse({"ok": True, "stats": stats})


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
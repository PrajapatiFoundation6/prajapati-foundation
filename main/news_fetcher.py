"""
news_fetcher.py — Prajapati Foundation
========================================
Fetches India-focused news about:
  • Prajapati / Kumhar samaj
  • Mitti kala / pottery
  • Kumhar community events
  • Raebareli (NGO's home district) — Prajapati/Kumhar samaj news specifically

Used by:
  - main.views.news()  -> triggers a background fetch if data looks stale
  - management command `python manage.py fetch_news` -> manual/cron run

Design notes:
  - Network calls are wrapped in try/except so one bad source never breaks
    the whole run.
  - Images are extracted concurrently (ThreadPoolExecutor) so this stays fast
    even when fetching 20-30 articles.
  - Duplicate articles (same source_link) are skipped via a DB uniqueness
    check before hitting the network for images.

IMAGE FIX (why the old version showed Google's logo / no photo at all):
  Google News RSS `link` fields are encrypted redirect URLs
  (news.google.com/rss/articles/...). Since Google's 2024 encoding change, a
  plain requests.get() can no longer follow these to the real article — it
  either lands on a Google page (og:image = Google's own logo) or just fails.
  Fix, in order of preference:
    1. Use `googlenewsdecoder` to resolve the REAL publisher URL from the
       encrypted redirect link (pip install googlenewsdecoder).
    2. If the RSS <description> HTML already embeds a real (non-Google)
       thumbnail, prefer that — it's free, no extra network call.
    3. Fetch the real publisher URL and read its og:image / twitter:image.
    4. If anything resolves back to a google.com/gstatic.com domain, treat
       it as "no image found" (emoji fallback) instead of showing Google's
       branding.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from .models import News

try:
    from googlenewsdecoder import gnewsdecoder as _gnews_decode
except ImportError:
    try:
        from googlenewsdecoder import new_decoderv1 as _gnews_decode
    except ImportError:
        _gnews_decode = None  # library not installed — decoding step will be skipped

logger = logging.getLogger(__name__)

FALLBACK_IMAGE = ""  # blank -> template shows an emoji placeholder instead

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "hi-IN,hi;q=0.9,en-IN;q=0.8",
}

REQUEST_TIMEOUT = 6  # seconds

# Domains that indicate we're still on Google's own site — fetching these
# would only ever give us Google's own logo/branding, never the real
# article's image.
GOOGLE_DOMAINS = ("google.com", "gstatic.com", "googleusercontent.com")


def _google_news_rss(query: str, hl: str = "hi", gl: str = "IN", ceid: str = "IN:hi") -> str:
    """Build a Google News RSS search URL safely (auto URL-encodes the query)."""
    return f"https://news.google.com/rss/search?q={quote(query)}&hl={hl}&gl={gl}&ceid={ceid}"


# Google News RSS — India, Hindi (ceid=IN:hi)
RSS_SOURCES = [
    {
        "url": "https://news.google.com/rss/search?q=%E0%A4%AA%E0%A5%8D%E0%A4%B0%E0%A4%9C%E0%A4%BE%E0%A4%AA%E0%A4%A4%E0%A4%BF+%E0%A4%B8%E0%A4%AE%E0%A4%BE%E0%A4%9C&hl=hi&gl=IN&ceid=IN:hi",
        "category": "प्रजापति समाज",
        "limit": 12,
    },
    {
        "url": "https://news.google.com/rss/search?q=%E0%A4%95%E0%A5%81%E0%A4%AE%E0%A5%8D%E0%A4%B9%E0%A4%BE%E0%A4%B0+%E0%A4%B8%E0%A4%AE%E0%A4%BE%E0%A4%9C+%E0%A4%AD%E0%A4%BE%E0%A4%B0%E0%A4%A4&hl=hi&gl=IN&ceid=IN:hi",
        "category": "कुम्हार समाज",
        "limit": 12,
    },
    {
        "url": "https://news.google.com/rss/search?q=%E0%A4%AE%E0%A4%BF%E0%A4%9F%E0%A5%8D%E0%A4%9F%E0%A5%80+%E0%A4%95%E0%A4%B2%E0%A4%BE+%E0%A4%AD%E0%A4%BE%E0%A4%B0%E0%A4%A4&hl=hi&gl=IN&ceid=IN:hi",
        "category": "मिट्टी कला",
        "limit": 10,
    },
    {
        "url": "https://news.google.com/rss/search?q=%E0%A4%95%E0%A5%81%E0%A4%AE%E0%A5%8D%E0%A4%B9%E0%A4%BE%E0%A4%B0+%E0%A4%AE%E0%A4%BF%E0%A4%9F%E0%A5%8D%E0%A4%9F%E0%A5%80+%E0%A4%AC%E0%A4%B0%E0%A5%8D%E0%A4%A4%E0%A4%A8&hl=hi&gl=IN&ceid=IN:hi",
        "category": "मिट्टी शिल्प",
        "limit": 10,
    },
    {
        "url": "https://news.google.com/rss/search?q=pottery+kumhar+india&hl=hi&gl=IN&ceid=IN:hi",
        "category": "मिट्टी कला",
        "limit": 8,
    },
    {
        "url": "https://news.google.com/rss/search?q=%E0%A4%AA%E0%A5%8D%E0%A4%B0%E0%A4%9C%E0%A4%BE%E0%A4%AA%E0%A4%A4%E0%A4%BF+%E0%A4%95%E0%A5%81%E0%A4%AE%E0%A5%8D%E0%A4%B9%E0%A4%BE%E0%A4%B0+%E0%A4%89%E0%A4%A4%E0%A5%8D%E0%A4%A4%E0%A4%B0+%E0%A4%AA%E0%A5%8D%E0%A4%B0%E0%A4%A6%E0%A5%87%E0%A4%B6&hl=hi&gl=IN&ceid=IN:hi",
        "category": "प्रजापति समाज",
        "limit": 8,
    },

    # ---- Raebareli + Prajapati/Kumhar samaj (NGO's home district) ----
    {
        "url": _google_news_rss("रायबरेली प्रजापति समाज"),
        "category": "रायबरेली प्रजापति समाज",
        "limit": 12,
    },
    {
        "url": _google_news_rss("रायबरेली कुम्हार समाज"),
        "category": "रायबरेली कुम्हार समाज",
        "limit": 10,
    },
    {
        "url": _google_news_rss("site:bhaskar.com रायबरेली प्रजापति"),
        "category": "रायबरेली प्रजापति समाज (दैनिक भास्कर)",
        "limit": 10,
    },
    {
        "url": _google_news_rss("site:bhaskar.com रायबरेली कुम्हार"),
        "category": "रायबरेली कुम्हार समाज (दैनिक भास्कर)",
        "limit": 10,
    },
]

RELEVANT_KEYWORDS = [
    "प्रजापति", "कुम्हार", "मिट्टी", "pottery", "मटका", "दीया", "दीपक",
    "कुलाल", "kumbhar", "kumhar", "prajapati", "मूर्ति", "शिल्प", "clay",
    "earthen", "बर्तन", "घड़ा", "कलश", "मृदभांड",
]

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def _is_relevant(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    return any(kw.lower() in text for kw in RELEVANT_KEYWORDS)


def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = HTML_TAG_RE.sub("", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def _is_google_domain(url: str) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in GOOGLE_DOMAINS)


def _extract_rss_thumbnail(summary_html: str) -> str:
    """
    Some Google News RSS <description> blocks embed a small <img>. Use it
    only if it's NOT hosted on a Google domain (otherwise it's just
    Google's branding, not the real article's thumbnail).
    """
    if not summary_html:
        return ""
    try:
        soup = BeautifulSoup(summary_html, "html.parser")
        img = soup.find("img", src=True)
        if img and img["src"].startswith("http") and not _is_google_domain(img["src"]):
            return img["src"]
    except Exception:
        logger.debug("RSS thumbnail parse failed", exc_info=True)
    return ""


def _decode_google_news_url(url: str) -> str:
    """
    Google News RSS links are encrypted redirects (news.google.com/rss/articles/...).
    Since Google's 2024 encoding change, a plain requests.get() can no longer
    follow these to the real article — this resolves the actual publisher URL
    so we can fetch the real og:image (and link users straight to the article
    instead of through Google). Falls back to the original Google URL if
    decoding fails for any reason (rate-limited, network issue, library not
    installed, etc.) — never raises.
    """
    if _gnews_decode is None:
        return url
    try:
        result = _gnews_decode(url, interval=1)
        if isinstance(result, dict) and result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
    except Exception:
        logger.debug("Google News URL decode failed for %s", url, exc_info=True)
    return url


def _extract_image(url: str) -> str:
    """Best-effort og:image / twitter:image / first-large-<img> extraction."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS, allow_redirects=True)
        if resp.status_code != 200:
            return FALLBACK_IMAGE

        # If we're still on a google.com/gstatic.com page, the redirect never
        # actually reached the publisher — og:image here would just be
        # Google's own logo. Bail out to the emoji fallback instead.
        if _is_google_domain(resp.url):
            return FALLBACK_IMAGE

        soup = BeautifulSoup(resp.text, "html.parser")

        og = soup.find("meta", property="og:image")
        if og and og.get("content", "").startswith("http") and not _is_google_domain(og["content"]):
            return og["content"]

        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw and tw.get("content", "").startswith("http") and not _is_google_domain(tw["content"]):
            return tw["content"]

        for img in soup.find_all("img", src=True):
            src = img["src"]
            if not src.startswith("http") or _is_google_domain(src):
                continue
            width = img.get("width", "0")
            try:
                if int(str(width).replace("px", "")) >= 200:
                    return src
            except (ValueError, TypeError):
                if any(src.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                    return src

    except requests.RequestException as exc:
        logger.debug("Image extract failed for %s: %s", url, exc)
    except Exception:
        logger.debug("Unexpected error extracting image for %s", url, exc_info=True)

    return FALLBACK_IMAGE


def _parse_date(entry) -> datetime:
    try:
        if getattr(entry, "published_parsed", None):
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    except Exception:
        pass
    return datetime.now(tz=timezone.utc)


def _process_entry(entry, category: str, existing_links: set):
    link = entry.get("link", "").strip()
    title = _clean_html(entry.get("title", ""))
    desc = _clean_html(entry.get("summary", ""))

    if not link or not title:
        return None
    if link in existing_links:
        return None
    if not _is_relevant(title, desc):
        return None

    return {
        "link": link,
        "title": title[:300],
        "desc": desc,
        "category": category,
        "date": _parse_date(entry),
        "rss_thumb": _extract_rss_thumbnail(entry.get("summary", "")),
    }


def fetch_news(max_workers: int = 8) -> dict:
    """
    Fetch fresh news from all configured RSS sources, resolve real article
    URLs + extract images concurrently, and save new (non-duplicate,
    relevant) articles.

    Returns: {"added": int, "skipped": int, "errors": int}
    """
    stats = {"added": 0, "skipped": 0, "errors": 0}

    existing_links = set(News.objects.values_list("source_link", flat=True))
    pending = []

    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            logger.info("RSS %s -> %d entries", source["category"], len(feed.entries))
            for entry in feed.entries[: source["limit"]]:
                result = _process_entry(entry, source["category"], existing_links)
                if result:
                    pending.append(result)
                    existing_links.add(result["link"])  # avoid intra-batch dupes too
                else:
                    stats["skipped"] += 1
        except Exception:
            logger.exception("RSS fetch error for %s", source["url"])
            stats["errors"] += 1

    if not pending:
        logger.info("fetch_news: no new relevant entries found.")
        return stats

    logger.info("fetch_news: resolving links + fetching images for %d new articles...", len(pending))

    def _with_image(item):
        # Resolve the real publisher URL first — needed both for a correct
        # og:image AND so "read full article" links go straight to the
        # publisher instead of through Google's redirect.
        real_url = _decode_google_news_url(item["link"])
        item["link"] = real_url

        if item.get("rss_thumb"):
            item["image"] = item["rss_thumb"]
        else:
            item["image"] = _extract_image(real_url)
        return item

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_with_image, item) for item in pending]
        for future in as_completed(futures):
            item = future.result()
            try:
                News.objects.get_or_create(
                    source_link=item["link"],
                    defaults={
                        "title": item["title"],
                        "description": item["desc"],
                        "category": item["category"],
                        "image": item["image"],
                        "published_date": item["date"],
                    },
                )
                stats["added"] += 1
            except Exception:
                logger.exception("DB save error for %s", item["link"])
                stats["errors"] += 1

    logger.info(
        "fetch_news done — added: %d, skipped: %d, errors: %d",
        stats["added"], stats["skipped"], stats["errors"],
    )
    return stats
"""
news_fetcher.py — Prajapati Foundation
========================================
Fetches India-focused news about:
  • Prajapati / Kumhar samaj
  • Mitti kala / pottery
  • Kumhar community events

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
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

from .models import News

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


def _extract_image(url: str) -> str:
    """Best-effort og:image / twitter:image / first-large-<img> extraction."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS, allow_redirects=True)
        if resp.status_code != 200:
            return FALLBACK_IMAGE

        soup = BeautifulSoup(resp.text, "html.parser")

        og = soup.find("meta", property="og:image")
        if og and og.get("content", "").startswith("http"):
            return og["content"]

        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw and tw.get("content", "").startswith("http"):
            return tw["content"]

        for img in soup.find_all("img", src=True):
            src = img["src"]
            if not src.startswith("http"):
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
    }


def fetch_news(max_workers: int = 8) -> dict:
    """
    Fetch fresh news from all configured RSS sources, extract images
    concurrently, and save new (non-duplicate, relevant) articles.

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

    logger.info("fetch_news: fetching images for %d new articles...", len(pending))

    def _with_image(item):
        item["image"] = _extract_image(item["link"])
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

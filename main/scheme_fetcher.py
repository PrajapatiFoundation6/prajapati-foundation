"""
scheme_fetcher.py — Prajapati Foundation
==========================================
Auto-updates the Artisan Support page with genuine government scheme
announcements, pulled from PIB's official Press Releases RSS feed and
filtered to items relevant to:
  - Artisans / Kumhar samaj / PM Vishwakarma / KVIC
  - PMEGP / MSME / Startup India / Mudra
  - Skill India / youth / apprenticeship
  - Scholarships (NSP)

The *curated* scheme cards (PM Vishwakarma, PMEGP, myScheme, NSP,
Startup India, Mudra, Skill India) are managed separately as GovScheme
rows with hand-verified official links — this fetcher only adds fresh
"what's new" announcements underneath them. Same design as news_fetcher.py.
"""

import logging
import re
from datetime import datetime, timezone

import feedparser

from .models import SchemeUpdate

logger = logging.getLogger(__name__)

# Official PIB "All Press Releases" RSS feed — verified genuine gov.in feed.
PIB_RSS_URL = "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1"

SCHEME_KEYWORDS = {
    "artisan": ["vishwakarma", "artisan", "kumhar", "kumbhar", "handicraft", "handloom", "pottery", "khadi", "kvic"],
    "startup": ["startup india", "startup", "seed fund", "dpiit", "mudra", "msme", "udyam"],
    "youth": ["skill india", "pmkvy", "kaushal vikas", "apprenticeship", "naps", "employment generation", "pmegp"],
    "scholarship": ["scholarship", "national scholarship", "nsp", "fellowship"],
}

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = HTML_TAG_RE.sub("", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def _matched_category(text: str) -> str:
    text_lower = text.lower()
    for category, keywords in SCHEME_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return ""


def _parse_date(entry) -> datetime:
    try:
        if getattr(entry, "published_parsed", None):
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    except Exception:
        pass
    return datetime.now(tz=timezone.utc)


def fetch_scheme_updates() -> dict:
    """
    Pull latest PIB press releases, keep only scheme-relevant ones,
    save new (non-duplicate) entries.

    Returns: {"added": int, "skipped": int, "errors": int}
    """
    stats = {"added": 0, "skipped": 0, "errors": 0}

    try:
        feed = feedparser.parse(PIB_RSS_URL)
    except Exception:
        logger.exception("PIB RSS fetch failed")
        stats["errors"] += 1
        return stats

    existing_links = set(SchemeUpdate.objects.values_list("source_link", flat=True))

    for entry in feed.entries[:60]:
        link = entry.get("link", "").strip()
        title = _clean_html(entry.get("title", ""))

        if not link or not title or link in existing_links:
            stats["skipped"] += 1
            continue

        category = _matched_category(title + " " + _clean_html(entry.get("summary", "")))
        if not category:
            stats["skipped"] += 1
            continue

        try:
            SchemeUpdate.objects.get_or_create(
                source_link=link,
                defaults={
                    "title": title[:500],
                    "category": category,
                    "published_date": _parse_date(entry),
                },
            )
            existing_links.add(link)
            stats["added"] += 1
        except Exception:
            logger.exception("DB save error for %s", link)
            stats["errors"] += 1

    logger.info(
        "fetch_scheme_updates done — added: %d, skipped: %d, errors: %d",
        stats["added"], stats["skipped"], stats["errors"],
    )
    return stats
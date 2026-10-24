"""
scheme_fetcher.py — Prajapati Foundation
Artisan Support page ke "Latest Scheme Announcements" section ko gov sources
se auto-update karta hai.

Categories (page ke filters se match):
  artisan     -> Kumhar / Prajapati / PM Vishwakarma / KVIC / handicraft
  startup     -> Startup India + business loans (Mudra, PMEGP, Stand-Up India, CGTMSE, MSME)
  youth       -> Skill India, PMKVY, internship, rozgar
  scholarship -> NSP / scholarships

Sources:
  1. PIB RSS (English + Hindi, Delhi HQ) — keywords se category
  2. Google News RSS, gov sites tak limited (site:pib.gov.in / site:gov.in) —
     category query se aati hai. Sirf wahi item save hota hai jiska source
     .gov.in / .nic.in verify ho.

NOTE: Upar wale "Verified Schemes" cards (GovScheme) curated hain, wo auto-update
nahi hote — unhe admin ya seed_schemes se manage karo.

Render free tier / cron-job.org ke liye: ek run ~25s ke andar khatam hota hai.
"""

import logging
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout, as_completed
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse

import feedparser
import requests

from .models import SchemeUpdate
from .news_fetcher import _clean_html, _decode_google_news_url, _parse_date

logger = logging.getLogger(__name__)

FEED_TIMEOUT = 6
MAX_AGE_DAYS = 120            # isse purani announcement skip
RECENT_DEDUPE_WINDOW = 2000

FEED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
}


# ── Feed sources ───────────────────────────────────────────────────────────

def _google_feed(query: str, lang: str = "en") -> str:
    hl, ceid = ("hi", "IN:hi") if lang == "hi" else ("en-IN", "IN:en")
    return f"https://news.google.com/rss/search?q={quote(query)}&hl={hl}&gl=IN&ceid={ceid}"


FEEDS = [
    # ---- PIB official RSS (category keywords se nikalti hai) ----
    {"kind": "pib", "label": "PIB English", "limit": 100,
     "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"},
    {"kind": "pib", "label": "PIB Hindi", "limit": 100,
     "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=2&Regid=3"},

    # ---- Kumhar / Prajapati / artisans ----
    {"kind": "google", "category": "artisan", "limit": 8, "label": "PM Vishwakarma",
     "url": _google_feed("site:pib.gov.in PM Vishwakarma")},
    {"kind": "google", "category": "artisan", "limit": 8, "label": "KVIC Kumhar Sashaktikaran",
     "url": _google_feed("site:pib.gov.in KVIC Kumhar Sashaktikaran potter")},
    {"kind": "google", "category": "artisan", "limit": 8, "label": "Artisans pottery handicraft",
     "url": _google_feed("site:pib.gov.in artisans pottery handicraft scheme")},
    {"kind": "google", "category": "artisan", "limit": 8, "label": "कुम्हार माटी कला (hi)",
     "url": _google_feed("site:gov.in कुम्हार माटी कला योजना", "hi")},

    # ---- Startups + business loans ----
    {"kind": "google", "category": "startup", "limit": 8, "label": "Startup India",
     "url": _google_feed("site:pib.gov.in Startup India")},
    {"kind": "google", "category": "startup", "limit": 8, "label": "Mudra loan",
     "url": _google_feed("site:pib.gov.in Mudra loan")},
    {"kind": "google", "category": "startup", "limit": 8, "label": "MSME credit guarantee",
     "url": _google_feed("site:pib.gov.in MSME credit guarantee CGTMSE")},
    {"kind": "google", "category": "startup", "limit": 8, "label": "PMEGP Stand-Up India",
     "url": _google_feed("site:pib.gov.in PMEGP Stand-Up India")},
    {"kind": "google", "category": "startup", "limit": 8, "label": "स्टार्टअप मुद्रा लोन (hi)",
     "url": _google_feed("site:gov.in स्टार्टअप मुद्रा लोन योजना", "hi")},

    # ---- Youth ----
    {"kind": "google", "category": "youth", "limit": 8, "label": "Skill India PMKVY",
     "url": _google_feed("site:pib.gov.in Skill India PMKVY")},
    {"kind": "google", "category": "youth", "limit": 8, "label": "PM Internship",
     "url": _google_feed("site:pib.gov.in PM Internship Scheme")},
    {"kind": "google", "category": "youth", "limit": 8, "label": "Employment linked incentive",
     "url": _google_feed("site:pib.gov.in employment linked incentive youth")},
    {"kind": "google", "category": "youth", "limit": 8, "label": "युवा कौशल रोजगार (hi)",
     "url": _google_feed("site:gov.in युवा कौशल रोजगार योजना", "hi")},

    # ---- Scholarship ----
    {"kind": "google", "category": "scholarship", "limit": 6, "label": "Scholarship",
     "url": _google_feed("site:pib.gov.in scholarship students")},
]


# ── Category classification (sirf PIB items ke liye) ──────────────────────
# Order = priority. ASCII keywords word-boundary se match hote hain
# ("nsp" ab "transport" me match nahi hoga), Devanagari plain substring.

CATEGORY_KEYWORDS = [
    ("artisan", [
        "pm vishwakarma", "vishwakarma", "artisan", "kumhar", "kumbhar", "potter",
        "pottery", "handicraft", "handloom", "khadi", "kvic", "mati kala",
        "traditional craft", "electric chaak",
        "विश्वकर्मा", "कुम्हार", "माटी कला", "मिट्टी कला", "शिल्पकार", "कारीगर",
        "खादी", "हस्तशिल्प",
    ]),
    ("startup", [
        "startup india", "startup", "seed fund", "fund of funds", "dpiit", "mudra",
        "msme", "udyam", "pmegp", "stand-up india", "standup india", "cgtmse",
        "credit guarantee", "sidbi", "business loan", "collateral-free",
        "collateral free", "svanidhi", "entrepreneur", "self-employment",
        "स्टार्टअप", "मुद्रा", "एमएसएमई", "उद्यमी", "स्वरोजगार", "लघु उद्योग",
        "क्रेडिट गारंटी",
    ]),
    ("youth", [
        "skill india", "pmkvy", "kaushal", "apprentice", "internship",
        "employment linked", "employment-linked", "rozgar", "skilling",
        "skill development", "youth employment", "yuva",
        "युवा", "कौशल", "रोजगार", "इंटर्नशिप", "प्रशिक्षुता",
    ]),
    ("scholarship", [
        "scholarship", "national scholarship", "nsp", "fellowship", "छात्रवृत्ति",
    ]),
]


def _compile(keywords):
    parts = []
    for kw in keywords:
        if kw.isascii():
            parts.append(r"\b" + re.escape(kw) + r"(?:s|es)?\b")
        else:
            parts.append(re.escape(kw))
    return re.compile("|".join(parts), re.IGNORECASE)


_PATTERNS = [(cat, _compile(kws)) for cat, kws in CATEGORY_KEYWORDS]


def _classify(text: str) -> str:
    for category, pattern in _PATTERNS:
        if pattern.search(text):
            return category
    return ""


# ── Helpers ────────────────────────────────────────────────────────────────

def _is_gov_host(url: str) -> bool:
    """Sirf .gov.in / .nic.in domains ko genuine maana jata hai."""
    host = (urlparse(url or "").hostname or "").lower()
    return host in ("gov.in", "nic.in") or host.endswith((".gov.in", ".nic.in"))


def _fetch_feed(spec: dict):
    """Timeout ke saath requests se fetch, phir feedparser. Returns (spec, entries|None)."""
    try:
        resp = requests.get(spec["url"], timeout=FEED_TIMEOUT, headers=FEED_HEADERS)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        entries = feed.entries[: spec["limit"]]
        logger.info("Scheme feed [%s] -> %d entries", spec["label"], len(entries))
        return spec, entries
    except Exception as exc:
        logger.warning("Scheme feed [%s] failed: %s", spec["label"], exc)
        return spec, None


def _build_item(entry, spec, existing_links: set, seen_titles: set, cutoff: datetime):
    link = (entry.get("link") or "").strip()
    title = _clean_html(entry.get("title", ""))
    summary = _clean_html(entry.get("summary", ""))
    if not link or not title:
        return None

    source = entry.get("source") or {}
    src_href = (source.get("href") or "").strip()
    src_title = (source.get("title") or "").strip()

    # Google News title ke end me " - Publisher" aata hai, hata do
    if src_title and title.endswith(" - " + src_title):
        title = title[: -(len(src_title) + 3)].strip()
    title = title[:500]

    if link in existing_links or title in seen_titles:
        return None

    published = _parse_date(entry)
    if published < cutoff:
        return None

    if spec["kind"] == "pib":
        if not _is_gov_host(link):
            return None
        category = _classify(f"{title} {summary}")
        if not category:
            return None
        src_verified = True
    else:
        # Google News item: source domain gov hona chahiye
        if src_href and not _is_gov_host(src_href):
            return None
        category = spec["category"]
        src_verified = bool(src_href)

    return {
        "kind": spec["kind"],
        "link": link,
        "title": title,
        "category": category,
        "date": published,
        "src_verified": src_verified,
    }


def _resolve(item: dict) -> dict:
    """Google ke encrypted link ko asli gov URL me badalta hai. item['link']=None => skip."""
    if item["kind"] != "google":
        return item

    original = item["link"]
    real = _decode_google_news_url(original)
    if real != original:
        # Decode ho gaya, final URL bhi gov hona chahiye
        item["link"] = real if _is_gov_host(real) else None
    elif not item["src_verified"]:
        item["link"] = None  # na decode hua, na source verify hua
    # else: decode fail par bhi source gov verified hai, Google redirect link rakhte hain
    return item


def _round_robin(items: list, limit: int) -> list:
    """Har category se barabar items, taaki ek category baaki ko dabaye nahi."""
    buckets = defaultdict(list)
    for item in sorted(items, key=lambda x: x["date"], reverse=True):
        buckets[item["category"]].append(item)

    picked = []
    while len(picked) < limit and any(buckets.values()):
        for category in list(buckets):
            if buckets[category] and len(picked) < limit:
                picked.append(buckets[category].pop(0))
    return picked


# ── Main entry point ───────────────────────────────────────────────────────

def fetch_scheme_updates(max_new: int = 16, time_budget: float = 12.0) -> dict:
    """
    Gov sources se naye scheme announcements fetch karke SchemeUpdate me save karta hai.

    max_new      : ek run me kitne naye items
    time_budget  : link-decode phase ke liye seconds (cron-job.org ~30s par timeout karta hai)

    Returns: {"added", "skipped", "errors", "feeds_ok", "feeds_failed"}
    """
    stats = {"added": 0, "skipped": 0, "errors": 0, "feeds_ok": 0, "feeds_failed": 0}

    recent = SchemeUpdate.objects.order_by("-published_date").values_list("source_link", "title")[:RECENT_DEDUPE_WINDOW]
    existing_links = {link for link, _ in recent}
    seen_titles = {title for _, title in recent}
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=MAX_AGE_DAYS)

    # 1) Saare feeds parallel me
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_fetch_feed, FEEDS))

    pending = []
    for spec, entries in results:
        if entries is None:
            stats["feeds_failed"] += 1
            continue
        stats["feeds_ok"] += 1
        for entry in entries:
            item = _build_item(entry, spec, existing_links, seen_titles, cutoff)
            if item:
                pending.append(item)
                existing_links.add(item["link"])
                seen_titles.add(item["title"])
            else:
                stats["skipped"] += 1

    if stats["feeds_ok"] == 0:
        logger.error("fetch_scheme_updates: koi bhi feed fetch nahi hui (network/block?)")
        stats["errors"] += 1
        return stats

    if not pending:
        logger.info("fetch_scheme_updates: kuch naya nahi mila. %s", stats)
        return stats

    pending = _round_robin(pending, max_new)
    logger.info("fetch_scheme_updates: %d items process ho rahe hain", len(pending))

    # 2) Google links decode, time budget ke andar
    executor = ThreadPoolExecutor(max_workers=6)
    futures = [executor.submit(_resolve, item) for item in pending]
    try:
        for future in as_completed(futures, timeout=time_budget):
            try:
                item = future.result()
            except Exception:
                logger.exception("Scheme item resolve failed")
                stats["errors"] += 1
                continue

            if not item["link"] or len(item["link"]) > 800:
                stats["skipped"] += 1
                continue

            try:
                _, created = SchemeUpdate.objects.get_or_create(
                    source_link=item["link"],
                    defaults={
                        "title": item["title"],
                        "category": item["category"],
                        "published_date": item["date"],
                    },
                )
                stats["added" if created else "skipped"] += 1
            except Exception:
                logger.exception("DB save error for %s", item["link"])
                stats["errors"] += 1
    except FuturesTimeout:
        unfinished = sum(1 for f in futures if not f.done())
        logger.warning("fetch_scheme_updates: time budget khatam, %d items agle run me", unfinished)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    logger.info("fetch_scheme_updates done — %s", stats)
    return stats
"""
news_fetcher.py — Prajapati Foundation
Google News RSS se India-focused Prajapati/Kumhar/mitti-kala news fetch karta hai.

Render free tier ke liye design:
  - cron-job.org ka timeout chhota hota hai, isliye ek run me max_new articles
    aur time_budget tak hi kaam hota hai. Baaki articles agle run me aate hain.
  - Har network call par timeout, response size cap, aur SSRF guard.
  - Dedupe decode se PEHLE hota hai (title + link), taaki purane articles ke
    liye dobara decode/image-fetch na ho.
"""

import ipaddress
import logging
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout, as_completed
from datetime import datetime, timezone
from urllib.parse import quote, urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from .models import News

try:
    from googlenewsdecoder import gnewsdecoder as _gnews_decode
except ImportError:
    _gnews_decode = None  # install nahi hai to decode step skip hoga

logger = logging.getLogger(__name__)

FALLBACK_IMAGE = ""  # blank -> template emoji placeholder dikhata hai

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "hi-IN,hi;q=0.9,en-IN;q=0.8",
}

FEED_TIMEOUT = 8
PAGE_TIMEOUT = 4
MAX_PAGE_BYTES = 1_000_000
MAX_REDIRECTS = 3
RECENT_DEDUPE_WINDOW = 2000  # itne latest articles ke saath dedupe check

GOOGLE_DOMAINS = ("google.com", "gstatic.com", "googleusercontent.com")

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def _feed_url(query: str) -> str:
    return f"https://news.google.com/rss/search?q={quote(query)}&hl=hi&gl=IN&ceid=IN:hi"


RSS_SOURCES = [
    {"query": "प्रजापति समाज", "category": "प्रजापति समाज", "limit": 12},
    {"query": "कुम्हार समाज भारत", "category": "कुम्हार समाज", "limit": 12},
    {"query": "मिट्टी कला भारत", "category": "मिट्टी कला", "limit": 10},
    {"query": "कुम्हार मिट्टी बर्तन", "category": "मिट्टी शिल्प", "limit": 10},
    {"query": "pottery kumhar india", "category": "मिट्टी कला", "limit": 8},
    {"query": "प्रजापति कुम्हार उत्तर प्रदेश", "category": "प्रजापति समाज", "limit": 8},
    # Raebareli (NGO ka home district)
    {"query": "रायबरेली प्रजापति समाज", "category": "रायबरेली प्रजापति समाज", "limit": 12},
    {"query": "रायबरेली कुम्हार समाज", "category": "रायबरेली कुम्हार समाज", "limit": 10},
    {"query": "site:bhaskar.com रायबरेली प्रजापति", "category": "रायबरेली प्रजापति समाज (दैनिक भास्कर)", "limit": 10},
    {"query": "site:bhaskar.com रायबरेली कुम्हार", "category": "रायबरेली कुम्हार समाज (दैनिक भास्कर)", "limit": 10},
]

RELEVANT_KEYWORDS = [
    "प्रजापति", "कुम्हार", "मिट्टी", "pottery", "मटका", "दीया", "दीपक",
    "कुलाल", "kumbhar", "kumhar", "prajapati", "मूर्ति", "शिल्प", "clay",
    "earthen", "बर्तन", "घड़ा", "कलश", "मृदभांड",
]


# ── helpers ────────────────────────────────────────────────────────────────

def _is_relevant(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    return any(kw.lower() in text for kw in RELEVANT_KEYWORDS)


def _clean_html(text: str) -> str:
    if not text:
        return ""
    return WHITESPACE_RE.sub(" ", HTML_TAG_RE.sub("", text)).strip()


def _is_google_domain(url: str) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in GOOGLE_DOMAINS)


def _is_safe_url(url: str) -> bool:
    """SSRF guard: sirf public internet ke http(s) URLs. Localhost/private/metadata IPs block."""
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            return False
        port = p.port or (443 if p.scheme == "https" else 80)
        infos = socket.getaddrinfo(p.hostname, port, proto=socket.IPPROTO_TCP)
        return bool(infos) and all(ipaddress.ip_address(i[4][0]).is_global for i in infos)
    except (OSError, ValueError):
        return False


def _safe_get(url: str):
    """
    Redirects ko manually follow karta hai (har hop par SSRF check) aur body
    MAX_PAGE_BYTES par cut kar deta hai. Returns (final_url, bytes) ya None.
    """
    for _ in range(MAX_REDIRECTS + 1):
        if not _is_safe_url(url):
            return None
        try:
            resp = requests.get(
                url, timeout=PAGE_TIMEOUT, headers=HEADERS,
                allow_redirects=False, stream=True,
            )
        except requests.RequestException as exc:
            logger.debug("GET failed %s: %s", url, exc)
            return None

        try:
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                if not location:
                    return None
                url = urljoin(url, location)
                continue
            if resp.status_code != 200:
                return None

            body = b""
            for chunk in resp.iter_content(16384):
                body += chunk
                if len(body) >= MAX_PAGE_BYTES:
                    break
            return url, body
        except requests.RequestException:
            return None
        finally:
            resp.close()
    return None


def _https(url: str) -> str:
    # Site HTTPS par hai, http images mixed-content me block ho jaati hain
    return "https://" + url[len("http://"):] if url.startswith("http://") else url


def _extract_rss_thumbnail(summary_html: str) -> str:
    if not summary_html:
        return ""
    try:
        img = BeautifulSoup(summary_html, "html.parser").find("img", src=True)
        if img and img["src"].startswith("http") and not _is_google_domain(img["src"]):
            return _https(img["src"])
    except Exception:
        logger.debug("RSS thumbnail parse failed", exc_info=True)
    return ""


def _decode_google_news_url(url: str) -> str:
    """Google ka encrypted redirect -> asli publisher URL. Fail ho to original lautata hai."""
    if _gnews_decode is None:
        return url
    try:
        result = _gnews_decode(url, interval=1)
        if isinstance(result, dict) and result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
    except Exception:
        logger.debug("Google News decode failed for %s", url, exc_info=True)
    return url


def _extract_image(url: str) -> str:
    """og:image / twitter:image / pehli badi <img>. Google domain par ho to khali."""
    fetched = _safe_get(url)
    if not fetched:
        return FALLBACK_IMAGE
    final_url, body = fetched

    if _is_google_domain(final_url):
        return FALLBACK_IMAGE

    try:
        soup = BeautifulSoup(body, "html.parser")

        for attrs in ({"property": "og:image"}, {"name": "twitter:image"}):
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                candidate = urljoin(final_url, tag["content"].strip())
                if candidate.startswith("http") and not _is_google_domain(candidate):
                    return _https(candidate)

        for img in soup.find_all("img", src=True):
            src = urljoin(final_url, img["src"])
            if not src.startswith("http") or _is_google_domain(src):
                continue
            try:
                if int(str(img.get("width", "0")).replace("px", "")) >= 200:
                    return _https(src)
            except (ValueError, TypeError):
                if src.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png", ".webp")):
                    return _https(src)
    except Exception:
        logger.debug("Image parse failed for %s", url, exc_info=True)

    return FALLBACK_IMAGE


def _parse_date(entry) -> datetime:
    try:
        if getattr(entry, "published_parsed", None):
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    except Exception:
        pass
    return datetime.now(tz=timezone.utc)


def _fetch_feed(source: dict):
    """requests se timeout ke saath fetch, phir feedparser. Returns (source, entries|None)."""
    try:
        resp = requests.get(_feed_url(source["query"]), timeout=FEED_TIMEOUT, headers=HEADERS)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        logger.info("RSS %s -> %d entries", source["category"], len(feed.entries))
        return source, feed.entries[: source["limit"]]
    except Exception as exc:
        logger.warning("RSS fetch failed for %s: %s", source["category"], exc)
        return source, None


def _process_entry(entry, category: str, existing_links: set, seen_titles: set):
    link = entry.get("link", "").strip()
    title = _clean_html(entry.get("title", ""))[:300]
    desc = _clean_html(entry.get("summary", ""))

    if not link or not title:
        return None
    # Google ke encrypted link aur decoded link alag hote hain, isliye title se bhi dedupe
    if link in existing_links or title in seen_titles:
        return None
    if not _is_relevant(title, desc):
        return None

    return {
        "link": link,
        "title": title,
        "desc": desc,
        "category": category,
        "date": _parse_date(entry),
        "rss_thumb": _extract_rss_thumbnail(entry.get("summary", "")),
    }


# ── main entry point ───────────────────────────────────────────────────────

def fetch_news(max_workers: int = 4, max_new: int = 10, time_budget: float = 20.0) -> dict:
    """
    Naye relevant articles fetch + save karta hai.

    max_new      : ek run me kitne naye articles process honge
    time_budget  : decode/image phase ke liye seconds (cron-job.org ~30s par timeout karta hai)

    Returns: {"added": int, "skipped": int, "errors": int}
    """
    stats = {"added": 0, "skipped": 0, "errors": 0}

    recent = News.objects.order_by("-published_date").values_list("source_link", "title")[:RECENT_DEDUPE_WINDOW]
    existing_links = {link for link, _ in recent}
    seen_titles = {title[:300] for _, title in recent}

    # 1) Saare feeds parallel me
    with ThreadPoolExecutor(max_workers=5) as pool:
        feed_results = list(pool.map(_fetch_feed, RSS_SOURCES))

    pending = []
    for source, entries in feed_results:
        if entries is None:
            stats["errors"] += 1
            continue
        for entry in entries:
            item = _process_entry(entry, source["category"], existing_links, seen_titles)
            if item:
                pending.append(item)
                existing_links.add(item["link"])
                seen_titles.add(item["title"])
            else:
                stats["skipped"] += 1

    if not pending:
        logger.info("fetch_news: koi naya relevant article nahi mila. %s", stats)
        return stats

    # Sabse naye pehle, baaki agle run me
    pending.sort(key=lambda x: x["date"], reverse=True)
    deferred = len(pending) - max_new
    pending = pending[:max_new]
    logger.info("fetch_news: %d articles process ho rahe hain (%d agle run ke liye)", len(pending), max(deferred, 0))

    def _with_image(item):
        real_url = _decode_google_news_url(item["link"])
        item["link"] = real_url
        item["image"] = item["rss_thumb"] or _extract_image(real_url)
        return item

    # 2) Decode + image, time budget ke andar
    executor = ThreadPoolExecutor(max_workers=max_workers)
    futures = [executor.submit(_with_image, item) for item in pending]
    try:
        for future in as_completed(futures, timeout=time_budget):
            try:
                item = future.result()
            except Exception:
                logger.exception("Article processing failed")
                stats["errors"] += 1
                continue

            try:
                _, created = News.objects.get_or_create(
                    source_link=item["link"][:800],
                    defaults={
                        "title": item["title"],
                        "description": item["desc"],
                        "category": item["category"],
                        "image": item["image"],
                        "published_date": item["date"],
                    },
                )
                stats["added" if created else "skipped"] += 1
            except Exception:
                logger.exception("DB save error for %s", item["link"])
                stats["errors"] += 1
    except FuturesTimeout:
        unfinished = sum(1 for f in futures if not f.done())
        logger.warning("fetch_news: time budget khatam, %d articles agle run me", unfinished)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    logger.info("fetch_news done — %s", stats)
    return stats
"""
news_fetcher.py — Prajapati Foundation
=======================================
SIRF Prajapati samaj ki news, kayi akhbaaron se (Dainik Bhaskar, Dainik Jagran,
Amar Ujala, Hindustan, Patrika ... + Raebareli par khaas focus).

Flow (ek run):
  1. Saari Google News RSS feeds parallel me (config: news_sources.build_feeds()).
  2. Har entry: RETENTION_DAYS (15) se purani ho to skip, duplicate ho to skip.
  3. Title me Prajapati-samaj phrase mile  -> "sure".
     Na mile par pichle 72 ghante ki ho -> "maybe": asli article page khol kar
     uski shuruaat (lede) me phrase dhoondhte hain; na mile to reject.
  4. Google ka encrypted link -> asli publisher URL (googlenewsdecoder).
  5. Page se image + short description. SSRF guard har fetch par.
  6. DB me save (source_link unique).

Cleanup (15 din se purani news delete) alag hai: main/cleanup.py.
`run_news_job()` dono ko ek saath chalata hai — cron isi ko call karta hai.
"""

import html as html_lib
import ipaddress
import logging
import re
import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout, as_completed
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from . import news_sources as ns
from .models import News

try:
    from googlenewsdecoder import gnewsdecoder as _gnews_decode
except ImportError:
    try:
        from googlenewsdecoder import new_decoderv1 as _gnews_decode
    except ImportError:
        _gnews_decode = None  # library nahi hai -> Google link hi save hoga

logger = logging.getLogger(__name__)

# ── Limits ─────────────────────────────────────────────────────────────────
FEED_TIMEOUT = 10
PAGE_TIMEOUT = 6
MAX_PAGE_BYTES = 1_500_000
MAX_REDIRECTS = 3

MAX_SURE_PER_RUN = 60        # ek run me max itne "sure" articles process honge
MAX_MAYBE_PER_RUN = 20       # aur itne "maybe" (lede-check wale)
MAYBE_WINDOW_HOURS = 72      # "maybe" sirf itne ghante tak purane articles ke liye
TIME_BUDGET = 100.0          # seconds (decode + page fetch phase)

MAX_LINK_LEN = 800           # News.source_link max_length
MAX_IMAGE_LEN = 200          # News.image (URLField default max_length)
MAX_DESC_LEN = 300

GOOGLE_DOMAINS = ("google.com", "gstatic.com", "googleusercontent.com")

FEED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "hi-IN,hi;q=0.9,en-IN;q=0.8",
}
PAGE_HEADERS = {
    "User-Agent": FEED_HEADERS["User-Agent"],
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "hi-IN,hi;q=0.9,en-IN;q=0.8",
}

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


# ── Small helpers ──────────────────────────────────────────────────────────

def _clean_html(text) -> str:
    if not text:
        return ""
    text = html_lib.unescape(HTML_TAG_RE.sub("", str(text)))
    return WHITESPACE_RE.sub(" ", text).strip()


def _norm_title(title: str) -> str:
    """Dedupe key: lowercase, spaces ek, aur aakhir ka ' - Akhbaar' hissa hata do."""
    t = WHITESPACE_RE.sub(" ", (title or "")).strip().lower()
    if " - " in t:
        head, tail = t.rsplit(" - ", 1)
        if head and len(tail) <= 40:
            t = head
    return t


def _is_google_domain(url: str) -> bool:
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return any(host == d or host.endswith("." + d) for d in GOOGLE_DOMAINS)


def _https(url: str) -> str:
    return "https://" + url[len("http://"):] if url.startswith("http://") else url


def _parse_date(entry) -> datetime:
    try:
        parsed = entry.get("published_parsed")
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
    except Exception:
        pass
    return datetime.now(tz=timezone.utc)


# ── SSRF-safe page fetch ───────────────────────────────────────────────────

def _is_safe_url(url: str) -> bool:
    """Sirf public internet ke http(s) URLs. Localhost/private/metadata IPs block."""
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
    Redirects manually follow karta hai (har hop par SSRF check), body ko
    MAX_PAGE_BYTES par kaat deta hai. Returns (final_url, bytes) ya None.
    """
    for _ in range(MAX_REDIRECTS + 1):
        if not _is_safe_url(url):
            return None
        try:
            resp = requests.get(
                url, timeout=PAGE_TIMEOUT, headers=PAGE_HEADERS,
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


def _decode_google_news_url(url: str) -> str:
    """Google ka encrypted link -> asli publisher URL. Fail ho to original lautata hai."""
    if _gnews_decode is None or not _is_google_domain(url):
        return url
    try:
        result = _gnews_decode(url, interval=1)
        if isinstance(result, dict) and result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
    except Exception:
        logger.debug("Google News decode failed for %s", url, exc_info=True)
    return url


def _parse_page(final_url: str, body: bytes) -> dict:
    """Page se image, description aur lede (shuruaati paragraphs)."""
    out = {"image": "", "description": "", "lede": ""}
    try:
        soup = BeautifulSoup(body, "html.parser")

        for attrs in (
            {"property": "og:image"},
            {"property": "og:image:secure_url"},
            {"name": "twitter:image"},
            {"property": "twitter:image"},
        ):
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                candidate = urljoin(final_url, tag["content"].strip())
                if candidate.startswith("http") and not _is_google_domain(candidate):
                    out["image"] = _https(candidate)
                    break

        for attrs in ({"property": "og:description"}, {"name": "description"}):
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                out["description"] = _clean_html(tag["content"])
                break

        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p", limit=15)]
        out["lede"] = " ".join(x for x in paras if x)[:1000]
    except Exception:
        logger.debug("Page parse failed for %s", final_url, exc_info=True)
    return out


# ── Stage 1: feeds -> candidates ───────────────────────────────────────────

def _fetch_feed(spec: dict):
    """
    Pehle 'when:15d' ke saath, khaali aaye to bina uske (Google kabhi-kabhi
    'when:' ignore/fail karta hai). Returns (spec, entries) — dono request fail
    hone par entries=None.
    """
    urls = [
        ns.google_news_rss(f"{spec['query']} when:{ns.RETENTION_DAYS}d"),
        ns.google_news_rss(spec["query"]),
    ]
    reached = False
    for url in urls:
        try:
            resp = requests.get(url, timeout=FEED_TIMEOUT, headers=FEED_HEADERS)
            resp.raise_for_status()
            entries = feedparser.parse(resp.content).entries
            reached = True
        except Exception as exc:
            logger.warning("RSS [%s] failed: %s", spec["label"], exc)
            continue
        if entries:
            logger.info("RSS [%s] -> %d entries", spec["label"], len(entries))
            return spec, list(entries)
    return spec, ([] if reached else None)


def _entry_to_candidate(entry, spec, cutoff, seen_titles, seen_links):
    link = (entry.get("link") or "").strip()
    raw_title = _clean_html(entry.get("title", ""))
    if not link or not raw_title or len(link) > MAX_LINK_LEN:
        return None

    source = entry.get("source") or {}
    src_title = (source.get("title") or "").strip() if hasattr(source, "get") else ""
    title = raw_title
    if src_title and title.endswith(" - " + src_title):
        title = title[: -(len(src_title) + 3)].strip()
    title = title[:300]
    if not title:
        return None

    published = _parse_date(entry)
    if published < cutoff:
        return None                       # 15 din se purani -> kabhi save nahi
    now = datetime.now(tz=timezone.utc)
    if published > now + timedelta(hours=6):
        published = now                   # galat future date

    key = _norm_title(title)
    if link in seen_links or key in seen_titles:
        return None

    return {
        "link": link,
        "title": title,
        "title_key": key,
        "published": published,
        "raebareli": bool(spec.get("raebareli")),
        "sure": ns.is_relevant(title),
    }


# ── Stage 2: decode + page -> final item (worker thread, DB ko haath nahi) ─

def _process_candidate(c: dict):
    link = c["link"]
    real_url = _decode_google_news_url(link)
    decoded = real_url != link and not _is_google_domain(real_url)

    page = {}
    if decoded:
        fetched = _safe_get(real_url)
        if fetched:
            final_url, body = fetched
            if not _is_google_domain(final_url):
                page = _parse_page(final_url, body)

    text = " ".join([c["title"], page.get("description", ""), page.get("lede", "")])

    if not c["sure"]:
        # Title me phrase nahi tha: article ke lede me hona ZAROORI hai
        if not page or not ns.is_relevant(text):
            return None

    final_link = real_url if decoded else link
    if len(final_link) > MAX_LINK_LEN:
        return None

    image = page.get("image", "")
    if len(image) > MAX_IMAGE_LEN:
        image = ""                        # lamba URL DB me fail karta, emoji fallback behtar

    return {
        "link": final_link,
        "title": c["title"],
        "description": page.get("description", "")[:MAX_DESC_LEN],
        "image": image,
        "category": ns.classify(text, raebareli_hint=c["raebareli"]),
        "published": c["published"],
    }


# ── Main entry points ──────────────────────────────────────────────────────

def fetch_news(max_workers: int = 4, time_budget: float = TIME_BUDGET) -> dict:
    """Returns {"added", "skipped", "errors", ...}. Kabhi crash nahi karta (feeds ke level par)."""
    stats = {"added": 0, "skipped": 0, "errors": 0}

    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=ns.RETENTION_DAYS)
    maybe_cutoff = now - timedelta(hours=MAYBE_WINDOW_HOURS)

    rows = list(News.objects.values_list("source_link", "title"))
    seen_links = {link for link, _ in rows}
    seen_titles = {_norm_title(title) for _, title in rows}

    # 1) Saari feeds parallel me
    feeds = ns.build_feeds()
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(_fetch_feed, feeds))

    candidates = []
    feeds_ok = 0
    for spec, entries in results:
        if entries is None:
            stats["errors"] += 1
            continue
        feeds_ok += 1
        for entry in entries:
            cand = _entry_to_candidate(entry, spec, cutoff, seen_titles, seen_links)
            if cand is None:
                stats["skipped"] += 1
                continue
            candidates.append(cand)
            seen_titles.add(cand["title_key"])
            seen_links.add(cand["link"])

    if feeds_ok == 0:
        logger.error("fetch_news: koi bhi feed fetch nahi hui (network/block?)")
        return stats

    def _order(c):
        return (0 if c["raebareli"] else 1, -c["published"].timestamp())

    sure = sorted((c for c in candidates if c["sure"]), key=_order)
    maybe = sorted(
        (c for c in candidates if not c["sure"] and c["published"] >= maybe_cutoff),
        key=_order,
    )
    batch = sure[:MAX_SURE_PER_RUN] + maybe[:MAX_MAYBE_PER_RUN]

    logger.info(
        "fetch_news: feeds_ok=%d/%d, candidates=%d (sure=%d, maybe=%d), processing=%d",
        feeds_ok, len(feeds), len(candidates), len(sure), len(maybe), len(batch),
    )
    if not batch:
        return stats

    # 2) Decode + page fetch (workers), DB save (is thread me)
    executor = ThreadPoolExecutor(max_workers=max_workers)
    futures = [executor.submit(_process_candidate, c) for c in batch]
    try:
        for future in as_completed(futures, timeout=time_budget):
            try:
                item = future.result()
            except Exception:
                logger.exception("Candidate processing failed")
                stats["errors"] += 1
                continue

            if item is None:
                stats["skipped"] += 1
                continue

            try:
                _, created = News.objects.get_or_create(
                    source_link=item["link"],
                    defaults={
                        "title": item["title"],
                        "description": item["description"],
                        "image": item["image"],
                        "category": item["category"],
                        "published_date": item["published"],
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


def run_news_job() -> dict:
    """Cron ka kaam: fetch + 15 din se purani news delete. Dono alag-alag protected hain."""
    from .cleanup import cleanup_old_entries

    try:
        stats = fetch_news()
    except Exception:
        logger.exception("run_news_job: fetch_news failed")
        stats = {"added": 0, "skipped": 0, "errors": 1}

    try:
        stats["cleanup"] = cleanup_old_entries()
    except Exception:
        logger.exception("run_news_job: cleanup failed")
        stats["cleanup"] = "failed"

    return stats
"""
news_sources.py — Prajapati Foundation
=======================================
Pure-python config + helpers for the news section. Koi Django import nahi hai,
isliye ise kahin bhi import/test kiya ja sakta hai.

Yahan kya hai:
  * RETENTION_DAYS      — news kitne din rakhni hai (15)
  * build_feeds()       — Google News RSS queries (Bhaskar / Jagran / Amar Ujala ... + Raebareli)
  * is_relevant(text)   — SIRF Prajapati samaj ki news pass hoti hai (strict phrase match)
  * classify(text)      — category: रायबरेली / प्रजापति समाज / कुम्हार समाज
  * publisher_name(url) — link se akhbaar ka naam
"""

import re
from urllib.parse import quote, urlparse

# ── Retention ──────────────────────────────────────────────────────────────
RETENTION_DAYS = 15   # isse purani news fetch bhi nahi hoti aur delete bhi ho jaati hai

# ── Categories (news page ke filter chips) ─────────────────────────────────
CAT_RAEBARELI = "रायबरेली"
CAT_PRAJAPATI = "प्रजापति समाज"
CAT_KUMHAR = "कुम्हार समाज"
CATEGORY_ORDER = [CAT_RAEBARELI, CAT_PRAJAPATI, CAT_KUMHAR]

# ── Publishers ─────────────────────────────────────────────────────────────
PUBLISHERS = {
    "bhaskar.com": "दैनिक भास्कर",
    "jagran.com": "दैनिक जागरण",
    "amarujala.com": "अमर उजाला",
    "livehindustan.com": "हिन्दुस्तान",
    "patrika.com": "पत्रिका",
    "navbharattimes.indiatimes.com": "नवभारत टाइम्स",
    "news18.com": "News18",
    "abplive.com": "ABP News",
    "aajtak.in": "आज तक",
    "jansatta.com": "जनसत्ता",
    "prabhatkhabar.com": "प्रभात खबर",
}

# In sab sites ke liye alag-alag "site:" queries chalti hain
SITE_DOMAINS = [
    "bhaskar.com",
    "jagran.com",
    "amarujala.com",
    "livehindustan.com",
    "patrika.com",
    "navbharattimes.indiatimes.com",
    "news18.com",
]

# Raebareli ke liye in sites par extra focus
RAEBARELI_SITE_DOMAINS = ["bhaskar.com", "jagran.com", "amarujala.com", "livehindustan.com"]


def publisher_name(url: str) -> str:
    """Link se akhbaar ka naam. Pehchaan na ho to domain, aur link na ho to ''."""
    try:
        host = (urlparse(url or "").hostname or "").lower()
    except ValueError:
        return ""
    if not host:
        return ""
    if host.startswith("www."):
        host = host[4:]
    for domain, name in PUBLISHERS.items():
        if host == domain or host.endswith("." + domain):
            return name
    if host == "google.com" or host.endswith(".google.com"):
        return "Google News"
    return host


# ── Google News RSS ────────────────────────────────────────────────────────

def google_news_rss(query: str, hl: str = "hi", gl: str = "IN", ceid: str = "IN:hi") -> str:
    """Google News RSS search URL (query apne aap URL-encode hoti hai)."""
    return f"https://news.google.com/rss/search?q={quote(query)}&hl={hl}&gl={gl}&ceid={ceid}"


def build_feeds() -> list:
    """
    Har item: {"label", "query", "raebareli"}.
    Raebareli wali feeds sabse pehle (priority), phir har akhbaar, phir open web.
    """
    feeds = []

    def add(query, raebareli=False):
        feeds.append({"label": query, "query": query, "raebareli": raebareli})

    # 1) Raebareli + Prajapati
    for dom in RAEBARELI_SITE_DOMAINS:
        add(f"site:{dom} रायबरेली प्रजापति", True)
    add("रायबरेली प्रजापति समाज", True)
    add("रायबरेली कुम्हार समाज", True)

    # 2) Har akhbaar par Prajapati / Kumhar samaj
    for dom in SITE_DOMAINS:
        add(f"site:{dom} प्रजापति समाज")
        add(f"site:{dom} कुम्हार समाज")

    # 3) Open web
    for q in (
        "प्रजापति समाज",
        "प्रजापति महासभा",
        "प्रजापति महासम्मेलन",
        "कुम्हार समाज",
        "महाराजा दक्ष जयंती",
        "Prajapati Samaj",
    ):
        add(q)

    return feeds


# ── Relevance: SIRF Prajapati samaj ki news ────────────────────────────────
# Sirf "प्रजापति" word kaafi nahi (kai logon ka surname hai: crime / politics
# ki khabrein aa jaati). Isliye "प्रजापति" ke TURANT baad samaj/sangathan wala
# shabd hona chahiye, ya "महाराजा दक्ष" jaisa samaj ka sandarbh.
#
# Devanagari par \b bharosemand nahi, isliye "agla akshar vyanjan na ho"
# wala lookahead use hota hai (taaki "समाजवादी", "सेवानिवृत्त", "संघर्ष" match na ho).

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff"), None)

_NOT_CONSONANT = r"(?![\u0915-\u0939\u0958-\u095f])"

_PRAJAPATI = r"प्रजापत[िी]"
_KUMHAR = r"(?:कुम्हार|कुम्भकार|कुंभकार|कुलाल)"

_PRAJAPATI_ORG = (
    r"(?:समाज|समुदाय|बिरादरी|महासभा|महासम्मेलन|महासंघ"
    r"|फाउंडेशन|फाउन्डेशन|फॉउंडेशन"
    r"|सेवा\s*(?:संस्थान|समिति|संघ|ट्रस्ट)"
    r"|(?:युवा|महिला)\s*(?:सभा|समिति|संगठन|मंडल|मंच|प्रकोष्ठ)"
    r"|(?:कल्याण|विकास)\s*(?:समिति|समाज|महासभा|संस्थान|ट्रस्ट))"
)

PAT_PRAJAPATI = re.compile(
    rf"{_PRAJAPATI}\s*(?:{_KUMHAR}\s*)?{_PRAJAPATI_ORG}{_NOT_CONSONANT}"
    r"|प्रजापतियों",
    re.IGNORECASE,
)

_KUMHAR_ORG = (
    r"(?:समाज|समुदाय|बिरादरी|महासभा|महासम्मेलन|महासंघ|कारीगर"
    r"|माटी\s*कला|माटीकला|मिट्टी\s*कला|शिल्पकार|सशक्तिकरण|कल्याण)"
)

PAT_KUMHAR = re.compile(
    rf"{_KUMHAR}\s*{_KUMHAR_ORG}{_NOT_CONSONANT}"
    r"|कुम्हारों|कुम्भकारों|कुंभकारों",
    re.IGNORECASE,
)

PAT_DAKSH = re.compile(
    r"महाराजा?\s*दक्ष"
    r"|दक्ष\s*प्रजापत[िी]\s*(?:जयंती|समाज|महासभा|शोभायात्रा|सम्मेलन)" + _NOT_CONSONANT,
    re.IGNORECASE,
)

PAT_EN = re.compile(
    r"prajapati\s+(?:kumhar\s+)?(?:samaj|samaaj|samuday|mahasabha|mahasangh|sangathan|foundation|biradari)(?![a-z])"
    r"|kumhar\s+(?:samaj|samaaj|samuday|community|artisans?|biradari)(?![a-z])"
    r"|kumbhar\s+(?:samaj|community)(?![a-z])",
    re.IGNORECASE,
)

PAT_RAEBARELI = re.compile(
    r"रायबरेली|रायबरेल[ीि]|raebareli|rae\s*bareli|rai\s*bareli|raibareli",
    re.IGNORECASE,
)


def _normalize(text) -> str:
    return (text or "").translate(_ZERO_WIDTH)


def is_relevant(text: str) -> bool:
    """True sirf tab jab text Prajapati / Kumhar samaj ki news lage."""
    t = _normalize(text)
    return bool(
        PAT_PRAJAPATI.search(t)
        or PAT_KUMHAR.search(t)
        or PAT_DAKSH.search(t)
        or PAT_EN.search(t)
    )


def classify(text: str, raebareli_hint: bool = False) -> str:
    """Category chip: रायबरेली > प्रजापति समाज > कुम्हार समाज."""
    t = _normalize(text)
    if raebareli_hint or PAT_RAEBARELI.search(t):
        return CAT_RAEBARELI
    if PAT_KUMHAR.search(t) and not (
        PAT_PRAJAPATI.search(t) or PAT_DAKSH.search(t) or "prajapati" in t.lower()
    ):
        return CAT_KUMHAR
    return CAT_PRAJAPATI
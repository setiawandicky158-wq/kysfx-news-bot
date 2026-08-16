import hashlib
import html
import logging
import re
import time
from calendar import timegm
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests


logger = logging.getLogger("KYSFX.NEWS")


# ============================================================
# SETTINGS
# ============================================================

REQUEST_TIMEOUT = 20
TRANSLATION_TIMEOUT = 10

MAX_NEWS_AGE_HOURS = 36
MAX_RESULTS_PER_SOURCE = 30

# Minimal score agar berita masuk engine
MIN_RELEVANCE_SCORE = 10

# Jumlah berita akhir
DEFAULT_LIMIT = 10


# ============================================================
# NEWS SOURCES
# ============================================================

NEWS_FEEDS = [
    {
        "name": "Google News - Gold",
        "url": (
            "https://news.google.com/rss/search?"
            "q=gold+XAUUSD+gold+price+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 10,
    },

    {
        "name": "Google News - Fed USD",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Federal+Reserve+Fed+USD+dollar+"
            "interest+rates+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 10,
    },

    {
        "name": "Google News - Treasury Yield",
        "url": (
            "https://news.google.com/rss/search?"
            "q=US+Treasury+yields+10-year+yield+"
            "real+yields+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 9,
    },

    {
        "name": "Google News - US Macro",
        "url": (
            "https://news.google.com/rss/search?"
            "q=US+CPI+PCE+PPI+NFP+employment+"
            "GDP+ISM+retail+sales+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 10,
    },

    {
        "name": "Google News - Oil",
        "url": (
            "https://news.google.com/rss/search?"
            "q=WTI+crude+oil+OPEC+oil+prices+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 7,
    },

    {
        "name": "Google News - Geopolitics",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Iran+Israel+Middle+East+war+"
            "geopolitics+gold+oil+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 8,
    },

    {
        "name": "InvestingLive",
        "url": "https://investinglive.com/rss/",
        "priority": 10,
    },
]


# ============================================================
# KEYWORD GROUPS
# ============================================================

GOLD_KEYWORDS = {
    "gold": 5,
    "xau": 7,
    "xauusd": 9,
    "bullion": 4,
    "gold price": 8,
    "gold prices": 8,
    "gold futures": 7,
    "spot gold": 8,
    "precious metals": 4,
    "precious metal": 4,
    "safe haven": 4,
}


USD_KEYWORDS = {
    "usd": 5,
    "us dollar": 6,
    "u.s. dollar": 6,
    "dollar index": 8,
    "dxy": 8,
    "greenback": 5,
    "dollar": 2,
}


YIELD_KEYWORDS = {
    "treasury yield": 8,
    "treasury yields": 8,
    "10-year yield": 9,
    "10 year yield": 9,
    "10-year treasury": 8,
    "10 year treasury": 8,
    "real yield": 9,
    "real yields": 9,
    "bond yield": 6,
    "bond yields": 6,
    "yields": 3,
}


FED_KEYWORDS = {
    "federal reserve": 9,
    "fed": 4,
    "fomc": 12,
    "powell": 11,
    "fed chair": 10,
    "interest rate": 5,
    "interest rates": 5,
    "rate cut": 8,
    "rate cuts": 8,
    "rate hike": 8,
    "rate hikes": 8,
    "rate decision": 10,
    "monetary policy": 7,
}


INFLATION_KEYWORDS = {
    "cpi": 12,
    "core cpi": 12,
    "pce": 12,
    "core pce": 12,
    "ppi": 10,
    "inflation": 8,
    "consumer prices": 8,
    "producer prices": 8,
}


LABOR_KEYWORDS = {
    "nonfarm payrolls": 14,
    "non-farm payrolls": 14,
    "nfp": 14,
    "payrolls": 10,
    "jobs report": 11,
    "employment report": 10,
    "employment": 5,
    "unemployment": 8,
    "unemployment rate": 10,
    "jobless claims": 10,
    "initial claims": 10,
    "continuing claims": 8,
    "jolts": 9,
    "wages": 6,
    "average hourly earnings": 10,
}


MACRO_KEYWORDS = {
    "gdp": 10,
    "ism": 9,
    "pmi": 7,
    "retail sales": 10,
    "consumer confidence": 7,
    "consumer sentiment": 7,
    "durable goods": 7,
    "industrial production": 7,
    "manufacturing": 4,
}


OIL_KEYWORDS = {
    "crude oil": 8,
    "wti": 10,
    "brent": 7,
    "opec": 9,
    "opec+": 11,
    "oil prices": 8,
    "crude prices": 8,
    "oil inventories": 10,
    "eia": 9,
    "strategic petroleum reserve": 8,
}


GEOPOLITICAL_KEYWORDS = {
    "iran": 7,
    "israel": 5,
    "gaza": 5,
    "middle east": 8,
    "war": 5,
    "conflict": 5,
    "ceasefire": 6,
    "sanctions": 6,
    "missile": 6,
    "military": 5,
    "hormuz": 12,
    "strait of hormuz": 14,
    "red sea": 8,
    "ukraine": 5,
    "russia": 5,
}


HIGH_IMPACT_KEYWORDS = {
    "fomc": 15,
    "fed decision": 15,
    "interest rate decision": 15,
    "rate decision": 13,
    "nfp": 15,
    "nonfarm payrolls": 15,
    "non-farm payrolls": 15,
    "cpi": 15,
    "pce": 15,
    "core pce": 15,
    "ppi": 12,
    "powell": 13,
    "federal reserve": 10,
    "jobless claims": 10,
    "retail sales": 9,
    "gdp": 9,
    "opec+": 12,
    "hormuz": 13,
    "strait of hormuz": 15,
}


# ============================================================
# DIRECTION KEYWORDS
# ============================================================

USD_BULLISH = [
    "dollar rises",
    "dollar rose",
    "dollar gains",
    "dollar gained",
    "dollar strengthens",
    "dollar strengthened",
    "usd rises",
    "usd gains",
    "dxy rises",
    "dxy gains",
    "dollar climbs",
    "dollar climbed",
    "dollar jumps",
    "dollar jumped",
]


USD_BEARISH = [
    "dollar falls",
    "dollar fell",
    "dollar drops",
    "dollar declined",
    "dollar weakens",
    "dollar weakened",
    "usd falls",
    "usd drops",
    "dxy falls",
    "dxy drops",
    "dollar slips",
    "dollar slipped",
]


YIELD_BULLISH = [
    "yields rise",
    "yields rose",
    "yield rises",
    "yield rose",
    "yields climb",
    "yield climbs",
    "yields higher",
    "yield higher",
    "yields jump",
    "yield jumps",
]


YIELD_BEARISH = [
    "yields fall",
    "yields fell",
    "yield falls",
    "yield fell",
    "yields decline",
    "yield declines",
    "yields lower",
    "yield lower",
    "yields drop",
    "yield drops",
]


OIL_BULLISH = [
    "oil rises",
    "oil rose",
    "oil gains",
    "oil gained",
    "oil prices rise",
    "oil prices rose",
    "crude rises",
    "crude rose",
    "wti rises",
    "wti rose",
]


OIL_BEARISH = [
    "oil falls",
    "oil fell",
    "oil drops",
    "oil declined",
    "oil prices fall",
    "oil prices fell",
    "crude falls",
    "crude fell",
    "wti falls",
    "wti fell",
]


HAWKISH_TERMS = [
    "hawkish",
    "higher for longer",
    "rate hike",
    "rate hikes",
    "raise rates",
    "raises rates",
    "raising rates",
    "tightening",
    "higher rates",
    "restrictive policy",
    "restrictive monetary",
]


DOVISH_TERMS = [
    "dovish",
    "rate cut",
    "rate cuts",
    "cut rates",
    "cuts rates",
    "cutting rates",
    "easing",
    "lower rates",
    "accommodative",
    "monetary easing",
]


# ============================================================
# BLOCKED TITLES
# ============================================================

BLOCKED_TITLE_KEYWORDS = [
    "week ahead",
    "weekly preview",
    "weekly outlook",
    "newsquawk week ahead",
    "newsquawk weekly preview",
    "newsquawk weekly outlook",
    "events next week",
    "calendar next week",
    "coming week",
    "what to watch this week",
    "week in review",
]


# ============================================================
# CATEGORY
# ============================================================

def detect_category(matches):

    priority = [
        ("Geopolitik", "geopolitics"),
        ("Bank Sentral", "fed"),
        ("Inflasi", "inflation"),
        ("Tenaga Kerja", "labor"),
        ("Energi", "oil"),
        ("Yield", "yield"),
        ("USD", "usd"),
        ("Gold", "gold"),
        ("Ekonomi AS", "macro"),
    ]

    for category, group in priority:
        if matches.get(group):
            return category

    return "Market"


# ============================================================
# NORMALIZE
# ============================================================

def normalize_text(value):

    if value is None:
        return ""

    value = html.unescape(str(value))

    value = re.sub(
        r"<[^>]+>",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# ============================================================
# DATE
# ============================================================

def parse_entry_datetime(entry):

    candidates = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created"),
    ]

    for value in candidates:

        if not value:
            continue

        try:

            parsed = parsedate_to_datetime(
                value
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                timezone.utc
            )

        except Exception:
            pass

    for field in (
        "published_parsed",
        "updated_parsed",
    ):

        value = entry.get(field)

        if value:

            try:

                return datetime.fromtimestamp(
                    timegm(value),
                    tz=timezone.utc,
                )

            except Exception:
                pass

    return datetime.now(timezone.utc)


# ============================================================
# FEED FETCH
# ============================================================

def fetch_feed(source):

    name = source["name"]
    url = source["url"]

    logger.info(
        "[NEWS] Fetching: %s",
        name,
    )

    try:

        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; KYSFX-NewsBot/2.0)"
                )
            },
        )

        response.raise_for_status()

        feed = feedparser.parse(
            response.content
        )

        entries = feed.entries[
            :MAX_RESULTS_PER_SOURCE
        ]

        logger.info(
            "[NEWS] %s entries: %s",
            name,
            len(entries),
        )

        return entries

    except Exception as exc:

        logger.warning(
            "[NEWS] Source failed: %s | %s",
            name,
            exc,
        )

        return []


# ============================================================
# KEYWORD SCORE
# ============================================================

def keyword_score(text, keywords):

    score = 0
    matched = []

    text = text.lower()

    for keyword, weight in keywords.items():

        if keyword.lower() in text:

            score += weight
            matched.append(keyword)

    return score, matched


# ============================================================
# RELEVANCE ENGINE V2
# ============================================================

def analyze_relevance(title, summary):

    text = (
        f"{title} {summary}"
    ).lower()

    groups = {
        "gold": GOLD_KEYWORDS,
        "usd": USD_KEYWORDS,
        "yield": YIELD_KEYWORDS,
        "fed": FED_KEYWORDS,
        "inflation": INFLATION_KEYWORDS,
        "labor": LABOR_KEYWORDS,
        "macro": MACRO_KEYWORDS,
        "oil": OIL_KEYWORDS,
        "geopolitics": GEOPOLITICAL_KEYWORDS,
        "high_impact": HIGH_IMPACT_KEYWORDS,
    }

    scores = {}
    matches = {}

    for name, keywords in groups.items():

        score, found = keyword_score(
            text,
            keywords,
        )

        scores[name] = score
        matches[name] = found

    # --------------------------------------------------------
    # BASE SCORE
    # --------------------------------------------------------

    score = sum(
        scores[group]
        for group in (
            "gold",
            "usd",
            "yield",
            "fed",
            "inflation",
            "labor",
            "macro",
            "oil",
            "geopolitics",
        )
    )

    # --------------------------------------------------------
    # HIGH IMPACT BONUS
    # --------------------------------------------------------

    score += scores["high_impact"]

    # --------------------------------------------------------
    # CROSS-MARKET BONUS
    #
    # Gold + USD
    # Gold + Yield
    # Gold + Fed
    # Gold + Inflation
    # Gold + Labor
    # --------------------------------------------------------

    if matches["gold"]:

        if matches["usd"]:
            score += 8

        if matches["yield"]:
            score += 10

        if matches["fed"]:
            score += 10

        if matches["inflation"]:
            score += 10

        if matches["labor"]:
            score += 10

        if matches["macro"]:
            score += 6

        if matches["geopolitics"]:
            score += 7

    # --------------------------------------------------------
    # FED + USD / YIELD
    # --------------------------------------------------------

    if matches["fed"]:

        if matches["usd"]:
            score += 7

        if matches["yield"]:
            score += 8

    # --------------------------------------------------------
    # INFLATION + USD / YIELD
    # --------------------------------------------------------

    if matches["inflation"]:

        if matches["usd"]:
            score += 7

        if matches["yield"]:
            score += 8

    # --------------------------------------------------------
    # LABOR + USD / YIELD
    # --------------------------------------------------------

    if matches["labor"]:

        if matches["usd"]:
            score += 7

        if matches["yield"]:
            score += 8

    # --------------------------------------------------------
    # GEOPOLITICS + GOLD / OIL
    # --------------------------------------------------------

    if matches["geopolitics"]:

        if matches["gold"]:
            score += 10

        if matches["oil"]:
            score += 7

    # --------------------------------------------------------
    # OIL + GOLD
    # --------------------------------------------------------

    if matches["oil"] and matches["gold"]:
        score += 5

    # --------------------------------------------------------
    # MARKET GROUP COUNT
    # --------------------------------------------------------

    market_groups = sum(
        bool(matches[group])
        for group in (
            "gold",
            "usd",
            "yield",
            "fed",
            "inflation",
            "labor",
            "macro",
            "oil",
            "geopolitics",
        )
    )

    # --------------------------------------------------------
    # RELEVANCE RULE
    # --------------------------------------------------------

    relevant = False

    if score >= MIN_RELEVANCE_SCORE:
        relevant = True

    # Single generic keyword is not enough
    if market_groups == 1:

        only_group = next(
            (
                group
                for group in (
                    "gold",
                    "usd",
                    "yield",
                    "fed",
                    "inflation",
                    "labor",
                    "macro",
                    "oil",
                    "geopolitics",
                )
                if matches[group]
            ),
            None,
        )

        # Require stronger score for isolated categories
        if only_group in (
            "usd",
            "oil",
            "macro",
        ):

            relevant = score >= 18

    return {
        "score": score,
        "relevant": relevant,
        "matches": matches,
        "scores": scores,
    }


# ============================================================
# IMPACT
# ============================================================

def impact_level(score):

    if score >= 60:
        return (
            "Critical Impact News",
            "⭐⭐⭐⭐⭐",
        )

    if score >= 40:
        return (
            "High Impact News",
            "⭐⭐⭐⭐⭐",
        )

    if score >= 28:
        return (
            "High Impact News",
            "⭐⭐⭐⭐",
        )

    if score >= 18:
        return (
            "Medium-High Impact",
            "⭐⭐⭐",
        )

    if score >= 10:
        return (
            "Market Impact",
            "⭐⭐",
        )

    return (
        "Low Impact",
        "⭐",
    )


# ============================================================
# DIRECTION ENGINE
# ============================================================

def directional_analysis(
    title,
    summary,
):

    text = (
        f"{title} {summary}"
    ).lower()

    gold = "NEUTRAL"
    usd = "NEUTRAL"
    yield_bias = "NEUTRAL"
    oil = "NEUTRAL"

    # --------------------------------------------------------
    # HAWKISH / DOVISH
    # --------------------------------------------------------

    hawkish = any(
        term in text
        for term in HAWKISH_TERMS
    )

    dovish = any(
        term in text
        for term in DOVISH_TERMS
    )

    if hawkish and not dovish:

        usd = "BULLISH"
        yield_bias = "BULLISH"
        gold = "BEARISH"

    elif dovish and not hawkish:

        usd = "BEARISH"
        yield_bias = "BEARISH"
        gold = "BULLISH"

    # --------------------------------------------------------
    # USD
    # --------------------------------------------------------

    if any(
        term in text
        for term in USD_BULLISH
    ):

        usd = "BULLISH"

        if gold == "NEUTRAL":
            gold = "BEARISH"

    elif any(
        term in text
        for term in USD_BEARISH
    ):

        usd = "BEARISH"

        if gold == "NEUTRAL":
            gold = "BULLISH"

    # --------------------------------------------------------
    # YIELD
    # --------------------------------------------------------

    if any(
        term in text
        for term in YIELD_BULLISH
    ):

        yield_bias = "BULLISH"

        if gold == "NEUTRAL":
            gold = "BEARISH"

    elif any(
        term in text
        for term in YIELD_BEARISH
    ):

        yield_bias = "BEARISH"

        if gold == "NEUTRAL":
            gold = "BULLISH"

    # --------------------------------------------------------
    # OIL
    # --------------------------------------------------------

    if any(
        term in text
        for term in OIL_BULLISH
    ):

        oil = "BULLISH"

    elif any(
        term in text
        for term in OIL_BEARISH
    ):

        oil = "BEARISH"

    # --------------------------------------------------------
    # SAFE HAVEN
    # --------------------------------------------------------

    safe_haven_terms = [
        "safe haven",
        "risk-off",
        "risk off",
        "geopolitical tensions",
        "geopolitical uncertainty",
        "war escalates",
        "conflict escalates",
        "military escalation",
    ]

    if any(
        term in text
        for term in safe_haven_terms
    ):

        if gold == "NEUTRAL":
            gold = "BULLISH"

    return {
        "gold": gold,
        "usd": usd,
        "yield": yield_bias,
        "oil": oil,
    }


# ============================================================
# SOURCE
# ============================================================

def detect_source(
    entry,
    fallback,
):

    source = entry.get("source")

    if isinstance(source, dict):

        name = source.get("title")

        if name:
            return normalize_text(name)

    if isinstance(source, str):

        return normalize_text(source)

    return fallback


# ============================================================
# TITLE CLEANING
# ============================================================

def clean_title(title):

    title = normalize_text(title)

    if not title:
        return ""

    # Google News sometimes adds " - Source"
    parts = title.split(" - ")

    if len(parts) >= 2:

        last = parts[-1].strip()

        if len(last) < 80:
            title = " - ".join(
                parts[:-1]
            )

    return title.strip()


# ============================================================
# SUMMARY
# ============================================================

def create_summary(
    title,
    summary,
):

    summary = normalize_text(summary)

    if not summary:
        return title[:600]

    sentences = re.split(
        r"(?<=[.!?])\s+",
        summary,
    )

    sentences = [
        x.strip()
        for x in sentences
        if x.strip()
    ]

    if not sentences:
        return summary[:700]

    return " ".join(
        sentences[:3]
    )[:700]


# ============================================================
# NEWS ID
# ============================================================

def make_news_id(
    title,
    url,
):

    raw = (
        normalize_text(title).lower()
        + "|"
        + normalize_text(url).lower()
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:24]


# ============================================================
# PROCESS ENTRY
# ============================================================

def process_entry(
    entry,
    source,
):

    title = clean_title(
        entry.get("title", "")
    )

    if not title:
        return None

    summary = normalize_text(
        entry.get(
            "summary",
            entry.get(
                "description",
                "",
            ),
        )
    )

    url = normalize_text(
        entry.get("link", "")
    )

    published = parse_entry_datetime(
        entry
    )

    now = datetime.now(
        timezone.utc
    )

    age = now - published

    # --------------------------------------------------------
    # AGE FILTER
    # --------------------------------------------------------

    if age > timedelta(
        hours=MAX_NEWS_AGE_HOURS
    ):
        return None

    if age < timedelta(
        minutes=-10
    ):
        return None

    # --------------------------------------------------------
    # BLOCKED TITLES
    # --------------------------------------------------------

    title_lower = title.lower()

    for blocked in BLOCKED_TITLE_KEYWORDS:

        if blocked in title_lower:

            return None

    # --------------------------------------------------------
    # RELEVANCE
    # --------------------------------------------------------

    analysis = analyze_relevance(
        title,
        summary,
    )

    if not analysis["relevant"]:
        return None

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    category = detect_category(
        analysis["matches"]
    )

    # --------------------------------------------------------
    # IMPACT
    # --------------------------------------------------------

    impact, stars = impact_level(
        analysis["score"]
    )

    # --------------------------------------------------------
    # DIRECTION
    # --------------------------------------------------------

    direction = directional_analysis(
        title,
        summary,
    )

    # --------------------------------------------------------
    # SOURCE
    # --------------------------------------------------------

    source_name = detect_source(
        entry,
        source,
    )

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    news_id = make_news_id(
        title,
        url,
    )

    return {
        "id": news_id,
        "title": title,
        "summary": summary,
        "url": url,
        "source": source_name,
        "published": published,
        "score": analysis["score"],
        "impact": impact,
        "stars": stars,
        "category": category,
        "matches": analysis["matches"],
        "direction": direction,
    }


# ============================================================
# FETCH ALL
# ============================================================

def fetch_all_news():

    collected = []

    for source in sorted(
        NEWS_FEEDS,
        key=lambda x: x["priority"],
        reverse=True,
    ):

        entries = fetch_feed(
            source
        )

        for entry in entries:

            try:

                item = process_entry(
                    entry,
                    source["name"],
                )

                if item:
                    collected.append(item)

            except Exception as exc:

                logger.warning(
                    "[NEWS] Entry error: %s",
                    exc,
                )

    return collected


# ============================================================
# DEDUPLICATION V2
# ============================================================

def normalize_title_for_dedup(
    title,
):

    title = title.lower()

    title = re.sub(
        r"[^a-z0-9]+",
        " ",
        title,
    )

    stopwords = {
        "the",
        "a",
        "an",
        "to",
        "of",
        "for",
        "and",
        "on",
        "in",
        "as",
        "with",
    }

    words = [
        word
        for word in title.split()
        if word not in stopwords
    ]

    return " ".join(words)


def title_similarity(
    title_a,
    title_b,
):

    words_a = set(
        normalize_title_for_dedup(
            title_a
        ).split()
    )

    words_b = set(
        normalize_title_for_dedup(
            title_b
        ).split()
    )

    if not words_a or not words_b:
        return 0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def deduplicate_news(
    news,
):

    unique = []

    for item in news:

        duplicate = False

        for existing in unique:

            # Same URL
            if (
                item["url"]
                and existing["url"]
                and item["url"]
                == existing["url"]
            ):

                duplicate = True
                break

            similarity = title_similarity(
                item["title"],
                existing["title"],
            )

            if similarity >= 0.72:

                duplicate = True

                # Keep stronger result
                if item["score"] > existing["score"]:

                    existing.clear()
                    existing.update(item)

                break

        if not duplicate:
            unique.append(item)

    return unique


# ============================================================
# SORT
# ============================================================

def sort_news(news):

    return sorted(
        news,
        key=lambda item: (
            item["score"],
            item["published"],
        ),
        reverse=True,
    )


# ============================================================
# PUBLIC API
# ============================================================

def get_news(
    limit=DEFAULT_LIMIT,
):

    logger.info(
        "[NEWS] Starting news scan..."
    )

    started = time.time()

    news = fetch_all_news()

    logger.info(
        "[NEWS] Relevant before dedup: %s",
        len(news),
    )

    news = deduplicate_news(
        news
    )

    news = sort_news(
        news
    )

    news = news[:limit]

    elapsed = (
        time.time() - started
    )

    logger.info(
        "[NEWS] Final results: %s | %.2fs",
        len(news),
        elapsed,
    )

    return news


# ============================================================
# TRANSLATION
# ============================================================

def translate_to_indonesian(
    text,
):

    if not text:
        return ""

    try:

        response = requests.get(
            "https://translate.googleapis.com/"
            "translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "id",
                "dt": "t",
                "q": text[:4500],
            },
            timeout=TRANSLATION_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        result = ""

        for item in data[0]:

            if item and item[0]:
                result += item[0]

        return normalize_text(
            result
        )

    except Exception as exc:

        logger.warning(
            "[NEWS] Translation failed: %s",
            exc,
        )

        return text


# ============================================================
# TELEGRAM FORMATTER
# ============================================================

def direction_text(
    direction,
):

    return {
        "BULLISH": "🟢 Bullish",
        "BEARISH": "🔴 Bearish",
        "NEUTRAL": "⚪ Neutral",
    }.get(
        direction,
        "⚪ Neutral",
    )


def gold_conclusion(
    direction,
):

    if direction == "BULLISH":

        return (
            "Cenderung <b>BULLISH</b> untuk "
            "XAUUSD berdasarkan faktor berita."
        )

    if direction == "BEARISH":

        return (
            "Cenderung <b>BEARISH</b> untuk "
            "XAUUSD berdasarkan faktor berita."
        )

    return (
        "Dampak terhadap XAUUSD "
        "belum memiliki arah yang jelas."
    )


def format_news_message(
    item,
    translate=True,
):

    title = item["title"]
    summary = create_summary(
        title,
        item["summary"],
    )

    if translate:

        title = translate_to_indonesian(
            title
        )

        summary = translate_to_indonesian(
            summary
        )

    direction = item["direction"]

    gold = direction["gold"]
    usd = direction["usd"]
    yield_bias = direction["yield"]
    oil = direction["oil"]

    message = (
        "🚨 <b>BREAKING NEWS</b>\n\n"

        f"📂 <b>{html.escape(item['category'])}</b>\n"

        f"📰 <b>{html.escape(title)}</b>\n\n"

        f"⚠️ <b>{html.escape(item['impact'])}</b> "
        f"{item['stars']}\n\n"

        f"📝 {html.escape(summary)}\n\n"

        "🥇 <b>GOLD / XAUUSD</b>\n"
        f"{direction_text(gold)}\n\n"

        "💵 <b>USD</b>\n"
        f"{direction_text(usd)}\n\n"

        "📈 <b>US YIELD</b>\n"
        f"{direction_text(yield_bias)}\n\n"

        "🛢️ <b>OIL / WTI</b>\n"
        f"{direction_text(oil)}\n\n"

        "🧠 <b>KESIMPULAN</b>\n"
        f"{gold_conclusion(gold)}\n\n"

        f"📊 <b>News Score:</b> "
        f"{item['score']}\n"

        f"📰 <b>Sumber:</b> "
        f"{html.escape(item['source'])}\n"

        f"🔗 <a href=\""
        f"{html.escape(item['url'])}"
        f"\">Baca berita</a>"
    )

    return message


# ============================================================
# DEBUG TEST
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )

    results = get_news(
        limit=10
    )

    print()
    print("=" * 80)
    print(
        f"FINAL NEWS: {len(results)}"
    )
    print("=" * 80)

    for index, item in enumerate(
        results,
        start=1,
    ):

        print()
        print(
            f"{index}. {item['title']}"
        )

        print(
            f"   SCORE : {item['score']}"
        )

        print(
            f"   IMPACT: "
            f"{item['impact']} "
            f"{item['stars']}"
        )

        print(
            f"   GOLD  : "
            f"{item['direction']['gold']}"
        )

        print(
            f"   USD   : "
            f"{item['direction']['usd']}"
        )

        print(
            f"   YIELD : "
            f"{item['direction']['yield']}"
        )

        print(
            f"   OIL   : "
            f"{item['direction']['oil']}"
        )

        print(
            f"   SOURCE: {item['source']}"
        )

        print(
            f"   URL   : {item['url']}"
        )

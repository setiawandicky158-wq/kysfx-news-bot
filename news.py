import hashlib
import html
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from config import NEWS_INTERVAL


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger("KYSFX.NEWS")


# ============================================================
# SETTINGS
# ============================================================

REQUEST_TIMEOUT = 20

MAX_NEWS_AGE_HOURS = 36

MAX_RESULTS_PER_SOURCE = 30

TRANSLATION_TIMEOUT = 10


# ============================================================
# NEWS SOURCES
# ============================================================

NEWS_FEEDS = [

    {
        "name": "InvestingLive",
        "url": "https://investinglive.com/rss/",
        "priority": 10,
    },

    {
        "name": "Google News - Gold",
        "url": (
            "https://news.google.com/rss/search?"
            "q=gold+XAUUSD+when:2d"
            "&hl=en-US"
            "&gl=US"
            "&ceid=US:en"
        ),
        "priority": 9,
    },

    {
        "name": "Google News - USD Fed",
        "url": (
            "https://news.google.com/rss/search?"
            "q=USD+Federal+Reserve+Fed+when:2d"
            "&hl=en-US"
            "&gl=US"
            "&ceid=US:en"
        ),
        "priority": 8,
    },

    {
        "name": "Google News - Treasury Yield",
        "url": (
            "https://news.google.com/rss/search?"
            "q=US+Treasury+yield+when:2d"
            "&hl=en-US"
            "&gl=US"
            "&ceid=US:en"
        ),
        "priority": 8,
    },

    {
        "name": "Google News - Oil",
        "url": (
            "https://news.google.com/rss/search?"
            "q=WTI+oil+OPEC+crude+when:2d"
            "&hl=en-US"
            "&gl=US"
            "&ceid=US:en"
        ),
        "priority": 7,
    },

    {
        "name": "Google News - US Macro",
        "url": (
            "https://news.google.com/rss/search?"
            "q=US+CPI+NFP+PCE+PPI+GDP+ISM+when:2d"
            "&hl=en-US"
            "&gl=US"
            "&ceid=US:en"
        ),
        "priority": 9,
    },

    {
        "name": "Google News - Geopolitics",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Middle+East+Iran+Israel+geopolitics+oil+gold+when:2d"
            "&hl=en-US"
            "&gl=US"
            "&ceid=US:en"
        ),
        "priority": 8,
    },
]


# ============================================================
# KEYWORDS
# ============================================================

GOLD_KEYWORDS = {
    "gold": 5,
    "xau": 6,
    "xauusd": 7,
    "bullion": 4,
    "precious metal": 3,
    "precious metals": 3,
    "gold price": 6,
    "gold prices": 6,
    "gold futures": 6,
    "spot gold": 6,
    "safe haven": 3,
}


USD_KEYWORDS = {
    "usd": 4,
    "u.s. dollar": 5,
    "us dollar": 5,
    "dollar index": 6,
    "dxy": 6,
    "greenback": 4,
    "dollar": 2,
}


YIELD_KEYWORDS = {
    "treasury yield": 6,
    "treasury yields": 6,
    "bond yield": 5,
    "bond yields": 5,
    "10-year yield": 7,
    "10 year yield": 7,
    "10-year treasury": 6,
    "10 year treasury": 6,
    "2-year yield": 5,
    "real yield": 7,
    "yields": 3,
}


FED_KEYWORDS = {
    "federal reserve": 7,
    "fed": 5,
    "fomc": 8,
    "powell": 8,
    "fed chair": 7,
    "interest rate": 4,
    "rate cut": 5,
    "rate hike": 5,
    "rate decision": 6,
    "monetary policy": 5,
}


INFLATION_KEYWORDS = {
    "cpi": 8,
    "core cpi": 8,
    "pce": 8,
    "core pce": 8,
    "ppi": 7,
    "inflation": 6,
    "consumer prices": 6,
    "producer prices": 6,
}


LABOR_KEYWORDS = {
    "nonfarm payrolls": 9,
    "non-farm payrolls": 9,
    "nfp": 9,
    "payrolls": 8,
    "jobs report": 8,
    "employment": 5,
    "unemployment": 6,
    "jobless claims": 7,
    "initial claims": 7,
    "continuing claims": 6,
    "jolts": 7,
    "wages": 5,
    "average hourly earnings": 7,
}


MACRO_KEYWORDS = {
    "gdp": 7,
    "ism": 7,
    "pmi": 6,
    "retail sales": 7,
    "consumer confidence": 5,
    "consumer sentiment": 5,
    "durable goods": 5,
    "industrial production": 5,
    "manufacturing": 4,
    "services": 3,
}


OIL_KEYWORDS = {
    "oil": 3,
    "crude oil": 6,
    "wti": 7,
    "brent": 5,
    "opec": 7,
    "opec+": 8,
    "oil prices": 6,
    "crude prices": 6,
    "oil inventories": 7,
    "eia": 7,
    "strategic petroleum reserve": 6,
}


GEOPOLITICAL_KEYWORDS = {
    "iran": 6,
    "israel": 4,
    "gaza": 4,
    "middle east": 6,
    "war": 4,
    "conflict": 4,
    "ceasefire": 5,
    "sanctions": 5,
    "missile": 5,
    "military": 4,
    "hormuz": 8,
    "strait of hormuz": 9,
    "red sea": 6,
    "ukraine": 4,
    "russia": 4,
}


HIGH_IMPACT_KEYWORDS = {
    "fomc": 10,
    "fed decision": 10,
    "interest rate decision": 10,
    "rate decision": 9,
    "nfp": 10,
    "nonfarm payrolls": 10,
    "non-farm payrolls": 10,
    "cpi": 10,
    "pce": 10,
    "core pce": 10,
    "ppi": 8,
    "powell": 9,
    "federal reserve": 8,
    "inflation": 6,
    "jobless claims": 7,
    "retail sales": 7,
    "gdp": 7,
    "opec+": 8,
    "hormuz": 9,
}


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

CATEGORY_KEYWORDS = {

    "Bank Sentral": (
        FED_KEYWORDS
    ),

    "Inflasi": (
        INFLATION_KEYWORDS
    ),

    "Tenaga Kerja": (
        LABOR_KEYWORDS
    ),

    "Ekonomi AS": (
        MACRO_KEYWORDS
    ),

    "Energi": (
        OIL_KEYWORDS
    ),

    "Geopolitik": (
        GEOPOLITICAL_KEYWORDS
    ),

    "USD": (
        USD_KEYWORDS
    ),

    "Yield": (
        YIELD_KEYWORDS
    ),

    "Gold": (
        GOLD_KEYWORDS
    ),
}


# ============================================================
# TEXT NORMALIZATION
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
# DATETIME PARSER
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

    # Feedparser fallback
    for field in (
        "published_parsed",
        "updated_parsed",
    ):

        value = entry.get(field)

        if value:

            try:

                from calendar import timegm

                timestamp = timegm(value)

                return datetime.fromtimestamp(
                    timestamp,
                    tz=timezone.utc,
                )

            except Exception:
                pass

    return datetime.now(
        timezone.utc
    )


# ============================================================
# FETCH FEED
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
                    "(compatible; KYSFX-NewsBot/1.0)"
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

def keyword_score(
    text,
    keywords,
):

    score = 0
    matched = []

    normalized = text.lower()

    for keyword, weight in keywords.items():

        if keyword.lower() in normalized:

            score += weight

            matched.append(
                keyword
            )

    return score, matched


# ============================================================
# ANALYZE RELEVANCE
# ============================================================

def analyze_relevance(
    title,
    summary,
):

    text = (
        f"{title} {summary}"
    ).lower()

    total_score = 0

    matches = {
        "gold": [],
        "usd": [],
        "yield": [],
        "fed": [],
        "inflation": [],
        "labor": [],
        "macro": [],
        "oil": [],
        "geopolitics": [],
        "high_impact": [],
    }

    # Gold
    score, found = keyword_score(
        text,
        GOLD_KEYWORDS,
    )

    total_score += score
    matches["gold"] = found

    # USD
    score, found = keyword_score(
        text,
        USD_KEYWORDS,
    )

    total_score += score
    matches["usd"] = found

    # Yield
    score, found = keyword_score(
        text,
        YIELD_KEYWORDS,
    )

    total_score += score
    matches["yield"] = found

    # Fed
    score, found = keyword_score(
        text,
        FED_KEYWORDS,
    )

    total_score += score
    matches["fed"] = found

    # Inflation
    score, found = keyword_score(
        text,
        INFLATION_KEYWORDS,
    )

    total_score += score
    matches["inflation"] = found

    # Labor
    score, found = keyword_score(
        text,
        LABOR_KEYWORDS,
    )

    total_score += score
    matches["labor"] = found

    # Macro
    score, found = keyword_score(
        text,
        MACRO_KEYWORDS,
    )

    total_score += score
    matches["macro"] = found

    # Oil
    score, found = keyword_score(
        text,
        OIL_KEYWORDS,
    )

    total_score += score
    matches["oil"] = found

    # Geopolitics
    score, found = keyword_score(
        text,
        GEOPOLITICAL_KEYWORDS,
    )

    total_score += score
    matches["geopolitics"] = found

    # High impact
    high_score, high_found = keyword_score(
        text,
        HIGH_IMPACT_KEYWORDS,
    )

    total_score += high_score
    matches["high_impact"] = high_found

    # --------------------------------------------------------
    # IMPORTANT:
    # Prevent generic "dollar" / "oil" articles from
    # being classified as strong XAUUSD news.
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

    relevant = (
        total_score >= 8
        and market_groups >= 1
    )

    # Very strong macro/high impact news
    if high_score >= 8:
        relevant = True

    return {
        "score": total_score,
        "relevant": relevant,
        "matches": matches,
    }


# ============================================================
# IMPACT LEVEL
# ============================================================

def impact_level(score):

    if score >= 30:
        return (
            "High Impact News",
            "⭐⭐⭐⭐⭐",
        )

    if score >= 20:
        return (
            "High Impact News",
            "⭐⭐⭐⭐",
        )

    if score >= 12:
        return (
            "Medium-High Impact",
            "⭐⭐⭐",
        )

    if score >= 8:
        return (
            "Market Impact",
            "⭐⭐",
        )

    return (
        "Low Impact",
        "⭐",
    )


# ============================================================
# CATEGORY DETECTION
# ============================================================

def detect_category(
    text,
    matches,
):

    priority = [
        (
            "Geopolitik",
            "geopolitics",
        ),
        (
            "Bank Sentral",
            "fed",
        ),
        (
            "Inflasi",
            "inflation",
        ),
        (
            "Tenaga Kerja",
            "labor",
        ),
        (
            "Energi",
            "oil",
        ),
        (
            "Yield",
            "yield",
        ),
        (
            "USD",
            "usd",
        ),
        (
            "Gold",
            "gold",
        ),
        (
            "Ekonomi AS",
            "macro",
        ),
    ]

    for category, group in priority:

        if matches.get(group):

            return category

    return "Market"


# ============================================================
# DIRECTIONAL ANALYSIS
# ============================================================

def directional_analysis(
    title,
    summary,
    matches,
):

    text = (
        f"{title} {summary}"
    ).lower()

    gold = "NEUTRAL"
    usd = "NEUTRAL"
    yield_bias = "NEUTRAL"
    oil = "NEUTRAL"

    # --------------------------------------------------------
    # DOVISH / HAWKISH
    # --------------------------------------------------------

    hawkish_terms = [
        "hawkish",
        "higher for longer",
        "rate hike",
        "rate hikes",
        "raise rates",
        "raises rates",
        "tightening",
        "higher rates",
        "restrictive",
    ]

    dovish_terms = [
        "dovish",
        "rate cut",
        "rate cuts",
        "cut rates",
        "cuts rates",
        "easing",
        "lower rates",
        "accommodative",
    ]

    hawkish = any(
        term in text
        for term in hawkish_terms
    )

    dovish = any(
        term in text
        for term in dovish_terms
    )

    # --------------------------------------------------------
    # USD / YIELD / GOLD RELATION
    # --------------------------------------------------------

    if hawkish and not dovish:

        usd = "BULLISH"
        yield_bias = "BULLISH"
        gold = "BEARISH"

    elif dovish and not hawkish:

        usd = "BEARISH"
        yield_bias = "BEARISH"
        gold = "BULLISH"

    # --------------------------------------------------------
    # EXPLICIT DOLLAR MOVEMENT
    # --------------------------------------------------------

    dollar_up_terms = [
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
    ]

    dollar_down_terms = [
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
    ]

    if any(
        term in text
        for term in dollar_up_terms
    ):

        usd = "BULLISH"

        if gold == "NEUTRAL":
            gold = "BEARISH"

    elif any(
        term in text
        for term in dollar_down_terms
    ):

        usd = "BEARISH"

        if gold == "NEUTRAL":
            gold = "BULLISH"

    # --------------------------------------------------------
    # YIELD MOVEMENT
    # --------------------------------------------------------

    yield_up_terms = [
        "yields rise",
        "yields rose",
        "yield rises",
        "yield rose",
        "yields climb",
        "yield climbs",
        "yields higher",
        "yield higher",
    ]

    yield_down_terms = [
        "yields fall",
        "yields fell",
        "yield falls",
        "yield fell",
        "yields decline",
        "yield declines",
        "yields lower",
        "yield lower",
    ]

    if any(
        term in text
        for term in yield_up_terms
    ):

        yield_bias = "BULLISH"

        if gold == "NEUTRAL":
            gold = "BEARISH"

    elif any(
        term in text
        for term in yield_down_terms
    ):

        yield_bias = "BEARISH"

        if gold == "NEUTRAL":
            gold = "BULLISH"

    # --------------------------------------------------------
    # OIL
    # --------------------------------------------------------

    oil_up_terms = [
        "oil rises",
        "oil rose",
        "oil gains",
        "oil gained",
        "oil prices rise",
        "crude rises",
        "crude rose",
        "wti rises",
        "wti rose",
    ]

    oil_down_terms = [
        "oil falls",
        "oil fell",
        "oil drops",
        "oil declined",
        "oil prices fall",
        "crude falls",
        "crude fell",
        "wti falls",
        "wti fell",
    ]

    if any(
        term in text
        for term in oil_up_terms
    ):

        oil = "BULLISH"

    elif any(
        term in text
        for term in oil_down_terms
    ):

        oil = "BEARISH"

    return {
        "gold": gold,
        "usd": usd,
        "yield": yield_bias,
        "oil": oil,
    }


# ============================================================
# TRANSLATION
# ============================================================

def translate_to_indonesian(
    text,
):

    if not text:
        return ""

    try:

        url = (
            "https://translate.googleapis.com/"
            "translate_a/single"
        )

        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "id",
            "dt": "t",
            "q": text[:4500],
        }

        response = requests.get(
            url,
            params=params,
            timeout=TRANSLATION_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        translated = ""

        for item in data[0]:

            if item and item[0]:

                translated += item[0]

        return normalize_text(
            translated
        )

    except Exception as exc:

        logger.warning(
            "[NEWS] Translation failed: %s",
            exc,
        )

        return text


# ============================================================
# SUMMARY
# ============================================================

def create_summary(
    title,
    summary,
):

    summary = normalize_text(
        summary
    )

    if not summary:

        return normalize_text(
            title
        )

    sentences = re.split(
        r"(?<=[.!?])\s+",
        summary,
    )

    sentences = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]

    if not sentences:

        return summary[:500]

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
        f"{normalize_text(title).lower()}"
        f"|{normalize_text(url).lower()}"
    )

    return hashlib.sha256(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()[:24]


# ============================================================
# CLEAN TITLE
# ============================================================

def clean_title(title):

    title = normalize_text(
        title
    )

    # Remove common Google News suffix
    title = re.sub(
        r"\s+-\s+[^-]{2,80}$",
        "",
        title,
    )

    return title.strip()


# ============================================================
# SOURCE NAME
# ============================================================

def detect_source(
    entry,
    fallback,
):

    source = entry.get(
        "source"
    )

    if isinstance(
        source,
        dict,
    ):

        name = source.get(
            "title"
        )

        if name:
            return normalize_text(
                name
            )

    if isinstance(
        source,
        str,
    ):

        return normalize_text(
            source
        )

    return fallback


# ============================================================
# PROCESS ENTRY
# ============================================================

def process_entry(
    entry,
    source,
):

    title = clean_title(
        entry.get(
            "title",
            "",
        )
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
        entry.get(
            "link",
            "",
        )
    )

    published = parse_entry_datetime(
        entry
    )

    now = datetime.now(
        timezone.utc
    )

    age = (
        now - published
    )

    if age > timedelta(
        hours=MAX_NEWS_AGE_HOURS
    ):

        return None

    if age < timedelta(
        minutes=-10
    ):

        return None

    title_lower = title.lower()

    # --------------------------------------------------------
    # BLOCK WEEKLY PREVIEWS
    # --------------------------------------------------------

    for blocked in (
        BLOCKED_TITLE_KEYWORDS
    ):

        if blocked in title_lower:

            logger.debug(
                "[NEWS] Blocked title: %s",
                title,
            )

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

    category = detect_category(
        f"{title} {summary}",
        analysis["matches"],
    )

    impact_text, stars = impact_level(
        analysis["score"]
    )

    direction = directional_analysis(
        title,
        summary,
        analysis["matches"],
    )

    source_name = detect_source(
        entry,
        source,
    )

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
        "impact": impact_text,
        "stars": stars,
        "category": category,
        "matches": analysis["matches"],
        "direction": direction,
    }


# ============================================================
# FETCH ALL NEWS
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
                    collected.append(
                        item
                    )

            except Exception as exc:

                logger.warning(
                    "[NEWS] Entry processing error: %s",
                    exc,
                )

    return collected


# ============================================================
# DEDUPLICATE
# ============================================================

def deduplicate_news(
    news,
):

    unique = {}
    title_index = {}

    for item in news:

        news_id = item["id"]

        title_key = re.sub(
            r"[^a-z0-9]+",
            " ",
            item["title"].lower(),
        ).strip()

        # Exact ID duplicate
        if news_id in unique:
            continue

        # Similar title duplicate
        if title_key in title_index:

            existing_id = title_index[
                title_key
            ]

            existing = unique[
                existing_id
            ]

            # Keep higher scoring article
            if item["score"] > existing["score"]:

                del unique[
                    existing_id
                ]

                unique[news_id] = item
                title_index[
                    title_key
                ] = news_id

            continue

        unique[news_id] = item

        title_index[
            title_key
        ] = news_id

    return list(
        unique.values()
    )


# ============================================================
# SORT
# ============================================================

def sort_news(
    news,
):

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
    limit=15,
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
# TELEGRAM FORMATTER
# ============================================================

def format_news_message(
    item,
    translate=True,
):

    title = item["title"]
    summary = item["summary"]

    if translate:

        translated_title = (
            translate_to_indonesian(
                title
            )
        )

        translated_summary = (
            translate_to_indonesian(
                create_summary(
                    title,
                    summary,
                )
            )
        )

    else:

        translated_title = title
        translated_summary = (
            create_summary(
                title,
                summary,
            )
        )

    direction = item[
        "direction"
    ]

    gold = direction["gold"]
    usd = direction["usd"]
    yield_bias = direction["yield"]
    oil = direction["oil"]

    gold_text = {
        "BULLISH": (
            "Berpotensi mendukung Gold "
            "jika USD/Yield melemah."
        ),
        "BEARISH": (
            "Berpotensi menekan Gold "
            "jika USD/Yield menguat."
        ),
        "NEUTRAL": (
            "Dampak langsung belum jelas."
        ),
    }[gold]

    usd_text = {
        "BULLISH": (
            "Berpotensi menguat."
        ),
        "BEARISH": (
            "Berpotensi melemah."
        ),
        "NEUTRAL": (
            "Arah USD belum jelas."
        ),
    }[usd]

    yield_text = {
        "BULLISH": (
            "Yield berpotensi naik."
        ),
        "BEARISH": (
            "Yield berpotensi turun."
        ),
        "NEUTRAL": (
            "Arah yield belum jelas."
        ),
    }[yield_bias]

    oil_text = {
        "BULLISH": (
            "Oil berpotensi menguat."
        ),
        "BEARISH": (
            "Oil berpotensi melemah."
        ),
        "NEUTRAL": (
            "Dampak Oil belum jelas."
        ),
    }[oil]

    message = (
        "🚨 <b>BREAKING NEWS</b>\n\n"

        f"📂 <b>{html.escape(item['category'])}</b>\n"

        f"📰 <b>{html.escape(translated_title)}</b>\n\n"

        f"⚠️ <b>{html.escape(item['impact'])}</b> "
        f"{item['stars']}\n\n"

        f"📝 {html.escape(translated_summary)}\n\n"

        "🥇 <b>GOLD / XAUUSD</b>\n"
        f"{gold_text}\n\n"

        "💵 <b>USD</b>\n"
        f"{usd_text}\n\n"

        "📈 <b>YIELD</b>\n"
        f"{yield_text}\n\n"

        "🛢️ <b>OIL / WTI</b>\n"
        f"{oil_text}\n\n"

        f"📰 <b>Sumber:</b> "
        f"{html.escape(item['source'])}\n"

        f"🔗 <a href=\"{html.escape(item['url'])}\">"
        "Baca berita</a>"
    )

    return message


# ============================================================
# TEST
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
    print("=" * 70)
    print(
        f"RELEVANT NEWS: {len(results)}"
    )
    print("=" * 70)

    for index, item in enumerate(
        results,
        start=1,
    ):

        print()
        print(
            f"{index}. {item['title']}"
        )

        print(
            f"   Category : {item['category']}"
        )

        print(
            f"   Score    : {item['score']}"
        )

        print(
            f"   Impact   : "
            f"{item['impact']} "
            f"{item['stars']}"
        )

        print(
            f"   Gold     : "
            f"{item['direction']['gold']}"
        )

        print(
            f"   USD      : "
            f"{item['direction']['usd']}"
        )

        print(
            f"   Yield    : "
            f"{item['direction']['yield']}"
        )

        print(
            f"   Oil      : "
            f"{item['direction']['oil']}"
        )

        print(
            f"   Source   : {item['source']}"
        )

        print(
            f"   URL      : {item['url']}"
        )

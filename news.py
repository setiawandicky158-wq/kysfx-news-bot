```python
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import hashlib


# ============================================================
# INVESTINGLIVE RSS
# ============================================================

RSS_URLS = [
    "https://investinglive.com/rss/news/",
    "https://investinglive.com/rss/",
]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}


# ============================================================
# KEYWORDS
# ============================================================

GOLD_KEYWORDS = [
    "gold",
    "xau",
    "xauusd",
    "bullion",
    "precious metal",
    "precious metals",
]

USD_KEYWORDS = [
    "usd",
    "us dollar",
    "dollar",
    "greenback",
    "dxy",
    "fed",
    "federal reserve",
    "fomc",
    "powell",
    "interest rate",
    "rate cut",
    "rate hike",
]

YIELD_KEYWORDS = [
    "yield",
    "yields",
    "treasury",
    "10-year",
    "10 year",
    "10y",
    "us10y",
    "bond yield",
]

# Oil dan WTI adalah SATU kategori
OIL_KEYWORDS = [
    "oil",
    "wti",
    "crude",
    "crude oil",
    "west texas intermediate",
    "opec",
    "opec+",
    "oil inventory",
    "oil inventories",
    "oil production",
    "oil supply",
    "oil demand",
]


# ============================================================
# HIGH IMPACT
# ============================================================

HIGH_IMPACT_KEYWORDS = [
    "nfp",
    "nonfarm",
    "non-farm",
    "payroll",
    "employment report",
    "unemployment rate",
    "cpi",
    "core cpi",
    "inflation",
    "ppi",
    "gdp",
    "fomc",
    "fed decision",
    "fed meeting",
    "powell",
    "interest rate decision",
    "rate decision",
    "rate cut",
    "rate hike",
    "opec",
    "opec+",
    "eia",
    "crude inventories",
    "oil inventories",
    "war",
    "sanctions",
    "tariff",
    "iran",
    "israel",
    "russia",
    "ukraine",
    "middle east",
    "emergency",
]


# ============================================================
# CATEGORY
# ============================================================

CATEGORY_KEYWORDS = {

    "💼 Tenaga Kerja": [
        "nfp",
        "nonfarm",
        "non-farm",
        "payroll",
        "employment",
        "unemployment",
        "jobless claims",
        "jobs",
        "jolts",
        "labor",
        "labour",
        "wages",
    ],

    "🏦 Bank Sentral": [
        "fed",
        "fomc",
        "powell",
        "federal reserve",
        "interest rate",
        "rate decision",
        "rate cut",
        "rate hike",
        "central bank",
    ],

    "📊 Inflasi": [
        "cpi",
        "inflation",
        "core inflation",
        "ppi",
        "consumer prices",
        "producer prices",
    ],

    "🛢️ Energi": [
        "oil",
        "wti",
        "crude",
        "opec",
        "opec+",
        "eia",
        "inventory",
        "inventories",
        "production",
        "energy",
    ],

    "🌍 Geopolitik": [
        "war",
        "conflict",
        "iran",
        "israel",
        "russia",
        "ukraine",
        "sanctions",
        "attack",
        "military",
        "middle east",
        "hormuz",
    ],

    "💵 Ekonomi AS": [
        "gdp",
        "retail sales",
        "ism",
        "pmi",
        "consumer confidence",
        "economic growth",
    ],
}


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    soup = BeautifulSoup(
        text,
        "html.parser"
    )

    return " ".join(
        soup.get_text(
            " ",
            strip=True
        ).split()
    )


# ============================================================
# KEYWORD CHECK
# ============================================================

def contains_keyword(text, keywords):

    text = text.lower()

    return any(
        keyword.lower() in text
        for keyword in keywords
    )


# ============================================================
# CATEGORY
# ============================================================

def detect_category(text):

    text_lower = text.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():

        if any(
            keyword.lower() in text_lower
            for keyword in keywords
        ):
            return category

    return "📰 Market"


# ============================================================
# IMPACT
# ============================================================

def calculate_impact(text):

    text_lower = text.lower()

    score = 0

    for keyword in HIGH_IMPACT_KEYWORDS:

        if keyword.lower() in text_lower:
            score += 2

    if contains_keyword(
        text,
        GOLD_KEYWORDS
    ):
        score += 2

    if contains_keyword(
        text,
        USD_KEYWORDS
    ):
        score += 1

    if contains_keyword(
        text,
        YIELD_KEYWORDS
    ):
        score += 1

    if contains_keyword(
        text,
        OIL_KEYWORDS
    ):
        score += 2

    if score >= 8:

        return (
            "High Impact News",
            "⭐⭐⭐⭐⭐"
        )

    if score >= 5:

        return (
            "Medium Impact News",
            "⭐⭐⭐⭐"
        )

    if score >= 3:

        return (
            "Market Impact",
            "⭐⭐⭐"
        )

    return (
        "Low Impact",
        "⭐⭐"
    )


# ============================================================
# GOLD ANALYSIS
# ============================================================

def gold_analysis(text):

    text_lower = text.lower()

    bullish = [
        "gold rises",
        "gold advances",
        "gold gains",
        "gold higher",
        "gold climbs",
        "gold rally",
        "gold strengthens",
        "gold up",
        "gold rises",
    ]

    bearish = [
        "gold falls",
        "gold declines",
        "gold drops",
        "gold lower",
        "gold weakens",
        "gold slides",
        "gold down",
    ]

    if any(
        x in text_lower
        for x in bullish
    ):

        return (
            "Potensi bullish. "
            "Tunggu konfirmasi harga."
        )

    if any(
        x in text_lower
        for x in bearish
    ):

        return (
            "Potensi bearish. "
            "Tunggu konfirmasi harga."
        )

    if contains_keyword(
        text,
        GOLD_KEYWORDS
    ):

        return (
            "Potensi volatilitas tinggi. "
            "Tunggu reaksi harga."
        )

    return (
        "Pantau dampaknya terhadap Gold."
    )


# ============================================================
# USD ANALYSIS
# ============================================================

def usd_analysis(text):

    text_lower = text.lower()

    bullish = [
        "dollar strengthens",
        "dollar gains",
        "dollar rises",
        "usd stronger",
        "usd rises",
        "dollar up",
    ]

    bearish = [
        "dollar weakens",
        "dollar falls",
        "dollar declines",
        "usd weaker",
        "usd falls",
        "dollar down",
    ]

    if any(
        x in text_lower
        for x in bullish
    ):

        return (
            "USD menguat dapat "
            "memberikan tekanan pada Gold."
        )

    if any(
        x in text_lower
        for x in bearish
    ):

        return (
            "USD melemah dapat "
            "mendukung Gold."
        )

    return (
        "Perhatikan arah dolar "
        "setelah rilis data/kebijakan."
    )


# ============================================================
# YIELD ANALYSIS
# ============================================================

def yield_analysis(text):

    text_lower = text.lower()

    higher = [
        "yield rises",
        "yield higher",
        "yields rise",
        "yields higher",
        "treasury yield rises",
        "10-year yield rises",
        "10-year yields rise",
    ]

    lower = [
        "yield falls",
        "yield lower",
        "yields fall",
        "yields lower",
        "treasury yield falls",
        "10-year yield falls",
        "10-year yields fall",
    ]

    if any(
        x in text_lower
        for x in higher
    ):

        return (
            "Kenaikan yield dapat "
            "menekan Gold."
        )

    if any(
        x in text_lower
        for x in lower
    ):

        return (
            "Penurunan yield dapat "
            "mendukung Gold."
        )

    return (
        "Pantau pergerakan US Treasury Yield."
    )


# ============================================================
# OIL / WTI ANALYSIS
# ============================================================

def oil_analysis(text):

    text_lower = text.lower()

    bullish = [
        "oil rises",
        "oil gains",
        "oil higher",
        "oil climbs",
        "oil rally",
        "oil up",
        "crude rises",
        "wti rises",
        "wti higher",
        "supply cut",
        "production cut",
    ]

    bearish = [
        "oil falls",
        "oil declines",
        "oil drops",
        "oil lower",
        "oil down",
        "crude falls",
        "wti falls",
        "wti lower",
        "supply increase",
        "production increase",
    ]

    if any(
        x in text_lower
        for x in bullish
    ):

        return (
            "Potensi bullish pada Oil/WTI. "
            "Tunggu konfirmasi harga."
        )

    if any(
        x in text_lower
        for x in bearish
    ):

        return (
            "Potensi bearish pada Oil/WTI. "
            "Tunggu konfirmasi harga."
        )

    if contains_keyword(
        text,
        OIL_KEYWORDS
    ):

        return (
            "Perubahan minyak dapat "
            "mempengaruhi ekspektasi inflasi."
        )

    return (
        "Pantau dampaknya terhadap Oil/WTI."
    )


# ============================================================
# RSS FETCH
# ============================================================

def fetch_feed(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        feed = feedparser.parse(
            response.content
        )

        print(
            f"[NEWS] RSS {url} -> "
            f"{len(feed.entries)} entries"
        )

        return feed

    except Exception as e:

        print(
            f"[NEWS] RSS ERROR {url}: {e}"
        )

        return None


# ============================================================
# NEWS ID
# ============================================================

def create_news_id(
    title,
    link
):

    raw = (
        f"{title}|{link}"
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        raw
    ).hexdigest()


# ============================================================
# GET NEWS
# ============================================================

def get_news(limit=20):

    results = []

    seen = set()

    for rss_url in RSS_URLS:

        feed = fetch_feed(
            rss_url
        )

        if not feed:
            continue

        for entry in feed.entries[:limit]:

            title = clean_text(
                entry.get(
                    "title",
                    ""
                )
            )

            summary = clean_text(
                entry.get(
                    "summary",
                    ""
                )
            )

            description = clean_text(
                entry.get(
                    "description",
                    ""
                )
            )

            link = entry.get(
                "link",
                ""
            ).strip()

            text = (
                f"{title} "
                f"{summary} "
                f"{description}"
            )

            if not text.strip():
                continue

            # ------------------------------------------------
            # RELEVANCE
            # ------------------------------------------------

            relevant = (
                contains_keyword(
                    text,
                    GOLD_KEYWORDS
                )
                or
                contains_keyword(
                    text,
                    USD_KEYWORDS
                )
                or
                contains_keyword(
                    text,
                    YIELD_KEYWORDS
                )
                or
                contains_keyword(
                    text,
                    OIL_KEYWORDS
                )
                or
                contains_keyword(
                    text,
                    HIGH_IMPACT_KEYWORDS
                )
            )

            if not relevant:
                continue

            news_id = create_news_id(
                title,
                link
            )

            if news_id in seen:
                continue

            seen.add(
                news_id
            )

            category = detect_category(
                text
            )

            impact, stars = calculate_impact(
                text
            )

            result = {

                "id": news_id,

                "title": title,

                "summary": summary,

                "link": link,

                "category": category,

                "impact": impact,

                "stars": stars,

                "gold": gold_analysis(
                    text
                ),

                "usd": usd_analysis(
                    text
                ),

                "yield": yield_analysis(
                    text
                ),

                "oil": oil_analysis(
                    text
                ),

                "published": entry.get(
                    "published",
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            results.append(
                result
            )

    return results


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_news(news):

    link = news.get(
        "link",
        ""
    )

    return (
        "🚨 <b>BREAKING NEWS</b>\n"
        f"📂 {news['category']}\n"
        f"📰 {news['title']}\n"
        f"⚠️ <b>{news['impact']}</b> "
        f"{news['stars']}\n\n"

        f"🟡 <b>Gold:</b>\n"
        f"{news['gold']}\n\n"

        f"💵 <b>USD:</b>\n"
        f"{news['usd']}\n\n"

        f"📈 <b>Yield:</b>\n"
        f"{news['yield']}\n\n"

        f"🛢️ <b>Oil:</b>\n"
        f"{news['oil']}\n\n"

        f"🔗 <a href=\"{link}\">"
        f"Sumber berita"
        f"</a>"
    )

```python
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from urllib.parse import urljoin

RSS_URLS = [
    "https://investinglive.com/rss",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
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
]

USD_KEYWORDS = [
    "dollar",
    "usd",
    "us dollar",
    "greenback",
    "dxy",
    "fed",
    "federal reserve",
    "fomc",
    "interest rate",
    "rate cut",
    "rate hike",
]

YIELD_KEYWORDS = [
    "yield",
    "treasury",
    "bond yield",
    "10-year",
    "10 year",
    "us10y",
]

OIL_KEYWORDS = [
    "oil",
    "wti",
    "crude",
    "crude oil",
    "brent",
    "opec",
    "opec+",
    "oil inventory",
    "oil inventories",
    "oil production",
    "oil supply",
    "oil demand",
]

HIGH_IMPACT_KEYWORDS = [
    "breaking",
    "fed",
    "fomc",
    "powell",
    "nfp",
    "nonfarm",
    "payroll",
    "cpi",
    "core cpi",
    "ppi",
    "gdp",
    "interest rate",
    "rate decision",
    "rate cut",
    "rate hike",
    "opec",
    "opec+",
    "eia",
    "crude inventories",
    "war",
    "sanctions",
    "tariff",
    "emergency",
]

CATEGORY_KEYWORDS = {
    "💼 Tenaga Kerja": [
        "nfp",
        "nonfarm",
        "payroll",
        "employment",
        "unemployment",
        "jobless claims",
        "jobs",
        "jolts",
        "labor",
        "labour",
    ],
    "🏦 Bank Sentral": [
        "fed",
        "fomc",
        "powell",
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
# HELPERS
# ============================================================

def clean_text(text):
    if not text:
        return ""

    soup = BeautifulSoup(text, "html.parser")
    return " ".join(soup.get_text(" ", strip=True).split())


def contains_keyword(text, keywords):
    text = text.lower()

    return any(
        keyword.lower() in text
        for keyword in keywords
    )


def detect_category(text):
    text_lower = text.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return category

    return "📰 Market"


def calculate_impact(text):
    text_lower = text.lower()

    score = 0

    for keyword in HIGH_IMPACT_KEYWORDS:
        if keyword.lower() in text_lower:
            score += 2

    if contains_keyword(text, GOLD_KEYWORDS):
        score += 2

    if contains_keyword(text, USD_KEYWORDS):
        score += 1

    if contains_keyword(text, YIELD_KEYWORDS):
        score += 1

    if contains_keyword(text, OIL_KEYWORDS):
        score += 2

    if score >= 8:
        return "High Impact News", "⭐⭐⭐⭐⭐"

    if score >= 5:
        return "Medium Impact News", "⭐⭐⭐⭐"

    if score >= 3:
        return "Market Impact", "⭐⭐⭐"

    return "Low Impact", "⭐⭐"


def gold_analysis(text):
    text_lower = text.lower()

    if any(
        x in text_lower
        for x in [
            "gold rises",
            "gold advances",
            "gold gains",
            "gold higher",
            "gold climbs",
            "gold rally",
            "gold strengthens",
        ]
    ):
        return "Potensi bullish. Tetap tunggu konfirmasi harga."

    if any(
        x in text_lower
        for x in [
            "gold falls",
            "gold declines",
            "gold drops",
            "gold lower",
            "gold weakens",
            "gold slides",
        ]
    ):
        return "Potensi bearish. Tunggu konfirmasi harga."

    if contains_keyword(text, GOLD_KEYWORDS):
        return "Potensi volatilitas tinggi. Tunggu reaksi harga."

    return "Pantau dampaknya terhadap Gold."


def usd_analysis(text):
    text_lower = text.lower()

    if any(
        x in text_lower
        for x in [
            "dollar strengthens",
            "dollar gains",
            "dollar rises",
            "usd stronger",
            "usd rises",
        ]
    ):
        return "USD menguat dapat memberikan tekanan pada Gold."

    if any(
        x in text_lower
        for x in [
            "dollar weakens",
            "dollar falls",
            "dollar declines",
            "usd weaker",
            "usd falls",
        ]
    ):
        return "USD melemah dapat mendukung Gold."

    return "Perhatikan arah dolar setelah rilis data/kebijakan."


def yield_analysis(text):
    text_lower = text.lower()

    if any(
        x in text_lower
        for x in [
            "yield rises",
            "yield higher",
            "yields rise",
            "yields higher",
            "treasury yield rises",
        ]
    ):
        return "Kenaikan yield dapat menekan Gold."

    if any(
        x in text_lower
        for x in [
            "yield falls",
            "yield lower",
            "yields fall",
            "yields lower",
            "treasury yield falls",
        ]
    ):
        return "Penurunan yield dapat mendukung Gold."

    return "Pantau pergerakan US Treasury Yield."


def oil_analysis(text):
    text_lower = text.lower()

    bullish_words = [
        "oil rises",
        "oil gains",
        "oil higher",
        "oil climbs",
        "oil rally",
        "crude rises",
        "wti rises",
        "supply cut",
        "production cut",
    ]

    bearish_words = [
        "oil falls",
        "oil declines",
        "oil drops",
        "oil lower",
        "crude falls",
        "wti falls",
        "supply increase",
        "production increase",
    ]

    if any(x in text_lower for x in bullish_words):
        return "Potensi bullish pada Oil/WTI. Tunggu konfirmasi harga."

    if any(x in text_lower for x in bearish_words):
        return "Potensi bearish pada Oil/WTI. Tunggu konfirmasi harga."

    if contains_keyword(text, OIL_KEYWORDS):
        return "Perubahan minyak dapat mempengaruhi ekspektasi inflasi."

    return "Pantau dampaknya terhadap Oil/WTI."


# ============================================================
# FETCH RSS
# ============================================================

def fetch_feed(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        return feedparser.parse(response.content)

    except Exception as e:
        print(f"[NEWS] RSS error: {e}")
        return None


# ============================================================
# GET NEWS
# ============================================================

def get_news(limit=10):
    results = []

    for rss_url in RSS_URLS:

        feed = fetch_feed(rss_url)

        if not feed:
            continue

        for entry in feed.entries[:limit]:

            title = clean_text(
                entry.get("title", "")
            )

            summary = clean_text(
                entry.get("summary", "")
            )

            link = entry.get("link", "")

            text = f"{title} {summary}"

            if not text.strip():
                continue

            # ------------------------------------------------
            # Only market-relevant news
            # ------------------------------------------------

            relevant = (
                contains_keyword(text, GOLD_KEYWORDS)
                or contains_keyword(text, USD_KEYWORDS)
                or contains_keyword(text, YIELD_KEYWORDS)
                or contains_keyword(text, OIL_KEYWORDS)
                or contains_keyword(text, HIGH_IMPACT_KEYWORDS)
            )

            if not relevant:
                continue

            category = detect_category(text)

            impact, stars = calculate_impact(text)

            result = {
                "title": title,
                "summary": summary,
                "link": link,
                "category": category,
                "impact": impact,
                "stars": stars,
                "gold": gold_analysis(text),
                "usd": usd_analysis(text),
                "yield": yield_analysis(text),
                "oil": oil_analysis(text),
                "published": entry.get(
                    "published",
                    datetime.now(timezone.utc).isoformat()
                ),
            }

            results.append(result)

    return results


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_news(news):

    return (
        "🚨 <b>BREAKING NEWS</b>\n"
        f"📂 {news['category']}\n"
        f"📰 {news['title']}\n"
        f"⚠️ <b>{news['impact']}</b> {news['stars']}\n\n"

        f"🟡 <b>Gold:</b>\n"
        f"{news['gold']}\n\n"

        f"💵 <b>USD:</b>\n"
        f"{news['usd']}\n\n"

        f"📈 <b>Yield:</b>\n"
        f"{news['yield']}\n\n"

        f"🛢️ <b>Oil:</b>\n"
        f"{news['oil']}\n\n"

        f"🔗 <a href=\"{news['link']}\">Sumber berita</a>"
    )
```

 import asyncio
import aiohttp
import feedparser
import re
import html


# ============================================================
# NEWS SOURCES
# ============================================================

RSS_FEEDS = {
    "CNBC Economy": [
        "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    ],

    "CNBC Energy": [
        "https://www.cnbc.com/id/19836768/device/rss/rss.html",
    ],

    "CNBC Asia": [
        "https://www.cnbc.com/id/19832390/device/rss/rss.html",
    ],

    "CNBC Earnings": [
        "https://www.cnbc.com/id/15839135/device/rss/rss.html",
    ],

    "MarketWatch": [
        "https://feeds.marketwatch.com/marketwatch/topstories/",
    ],
}


# ============================================================
# KEYWORDS
# ============================================================

KEYWORDS = {

    # GOLD / XAUUSD
    "gold": 100,
    "xauusd": 140,
    "gold price": 110,
    "gold prices": 110,
    "gold futures": 100,
    "bullion": 80,

    # FED
    "federal reserve": 120,
    "fomc": 130,
    "fed": 80,
    "interest rate": 110,
    "interest rates": 110,
    "rate cut": 120,
    "rate hike": 120,
    "hawkish": 110,
    "dovish": 110,

    # US DATA
    "nfp": 140,
    "nonfarm payroll": 140,
    "jobs report": 120,
    "employment": 80,
    "unemployment": 100,
    "jobless claims": 100,
    "cpi": 130,
    "inflation": 110,
    "pce": 130,
    "ppi": 100,
    "retail sales": 80,
    "gdp": 80,

    # USD
    "us dollar": 100,
    "dollar": 60,
    "usd": 60,
    "dxy": 120,

    # YIELD
    "treasury yield": 120,
    "treasury yields": 120,
    "10-year yield": 130,
    "10 year yield": 130,
    "bond yields": 100,

    # WTI / OIL
    "wti": 140,
    "wti crude": 140,
    "west texas intermediate": 140,
    "crude oil": 120,
    "oil price": 100,
    "oil prices": 100,
    "oil supply": 110,
    "oil inventory": 120,
    "oil inventories": 120,
    "eia": 110,
    "opec": 120,
    "opec+": 130,

    # GEOPOLITICAL
    "iran": 120,
    "israel": 100,
    "gaza": 100,
    "ukraine": 90,
    "russia": 80,
    "war": 100,
    "missile": 110,
    "attack": 100,
    "strike": 100,
    "military": 90,
    "ceasefire": 100,
    "sanctions": 100,
    "peace talks": 80,
    "geopolitical": 90,
    "hormuz": 140,
    "strait of hormuz": 150,

    # RISK
    "safe haven": 110,
    "risk off": 110,
    "risk-off": 110,
    "market turmoil": 100,
    "market volatility": 80,
}


# ============================================================
# FALSE POSITIVE FILTER
# ============================================================

EXCLUDE = [
    "football",
    "soccer",
    "basketball",
    "tennis",
    "judo",
    "taekwondo",
    "movie",
    "film",
    "music",
    "singer",
    "celebrity",
    "fashion",
    "handbag",
    "restaurant",
    "real estate",
    "housing",
    "wedding",
    "tourism",
]


# ============================================================
# SCORE
# ============================================================

def calculate_score(title):

    text = title.lower()

    score = 0

    for keyword, points in KEYWORDS.items():

        if keyword in text:
            score += points

    for word in EXCLUDE:

        if word in text:
            score -= 200

    return score


# ============================================================
# CATEGORY
# ============================================================

def get_category(title):

    text = title.lower()

    if any(x in text for x in [
        "nfp",
        "nonfarm payroll",
        "jobs report",
        "employment",
        "unemployment",
        "jobless claims",
    ]):
        return "💼 Tenaga Kerja"

    if any(x in text for x in [
        "cpi",
        "inflation",
        "pce",
        "ppi",
    ]):
        return "📊 Inflasi"

    if any(x in text for x in [
        "federal reserve",
        "fomc",
        "fed",
        "interest rate",
        "rate cut",
        "rate hike",
        "hawkish",
        "dovish",
    ]):
        return "🏦 Fed / Suku Bunga"

    if any(x in text for x in [
        "wti",
        "wti crude",
        "west texas intermediate",
        "crude oil",
        "oil price",
        "oil prices",
        "oil supply",
        "oil inventory",
        "oil inventories",
        "opec",
        "eia",
        "hormuz",
    ]):
        return "🛢️ WTI / Oil"

    if any(x in text for x in [
        "iran",
        "israel",
        "gaza",
        "ukraine",
        "russia",
        "war",
        "missile",
        "attack",
        "strike",
        "military",
        "ceasefire",
        "sanctions",
        "peace talks",
        "geopolitical",
    ]):
        return "🌍 Geopolitik"

    if any(x in text for x in [
        "treasury",
        "yield",
        "10-year",
        "10 year",
        "bond yield",
    ]):
        return "📈 US Treasury / Yield"

    if any(x in text for x in [
        "dxy",
        "dollar",
        "usd",
    ]):
        return "💵 USD"

    if any(x in text for x in [
        "gold",
        "xauusd",
        "bullion",
    ]):
        return "🥇 Gold"

    return "🌐 Makro"


# ============================================================
# IMPACT
# ============================================================

def get_impact(score):

    if score >= 220:
        return "High Impact News ⭐⭐⭐⭐⭐"

    if score >= 160:
        return "High Impact News ⭐⭐⭐⭐"

    if score >= 110:
        return "Medium Impact News ⭐⭐⭐"

    if score >= 70:
        return "Low Impact News ⭐⭐"

    return "Low Impact News ⭐"


# ============================================================
# GOLD
# ============================================================

def analyze_gold(title):

    text = title.lower()

    bullish = [
        "gold rises",
        "gold gains",
        "gold advances",
        "gold climbs",
        "rate cut",
        "dovish",
        "weak dollar",
        "dollar falls",
        "falling yields",
        "lower yields",
        "safe haven",
        "risk off",
        "risk-off",
        "war",
        "attack",
        "missile",
        "strike",
        "iran",
        "israel",
        "gaza",
        "ukraine",
        "sanctions",
        "hormuz",
    ]

    bearish = [
        "gold falls",
        "gold declines",
        "gold drops",
        "gold retreats",
        "rate hike",
        "hawkish",
        "strong dollar",
        "dollar rises",
        "higher yields",
        "rising yields",
    ]

    bull = sum(
        1 for x in bullish
        if x in text
    )

    bear = sum(
        1 for x in bearish
        if x in text
    )

    if bull > bear:
        return (
            "🟢 Gold:\n"
            "Berpotensi bullish. Faktor berita "
            "mendukung permintaan Gold."
        )

    if bear > bull:
        return (
            "🔴 Gold:\n"
            "Berpotensi bearish. Faktor berita "
            "dapat menekan Gold."
        )

    return (
        "🟡 Gold:\n"
        "Potensi volatilitas tinggi. "
        "Tunggu reaksi harga."
    )


# ============================================================
# USD
# ============================================================

def analyze_usd(title):

    text = title.lower()

    bearish = [
        "weak dollar",
        "dollar falls",
        "dollar declines",
        "rate cut",
        "dovish",
        "lower yields",
    ]

    bullish = [
        "strong dollar",
        "dollar rises",
        "rate hike",
        "hawkish",
        "higher yields",
    ]

    bear = sum(
        1 for x in bearish
        if x in text
    )

    bull = sum(
        1 for x in bullish
        if x in text
    )

    if bear > bull:
        return (
            "🟢 USD:\n"
            "Berpotensi melemah. Kondisi ini "
            "dapat mendukung Gold."
        )

    if bull > bear:
        return (
            "🔴 USD:\n"
            "Berpotensi menguat. Kondisi ini "
            "dapat menekan Gold."
        )

    return (
        "🟡 USD:\n"
        "Perhatikan arah dolar setelah "
        "rilis data/kebijakan."
    )


# ============================================================
# YIELD
# ============================================================

def analyze_yield(title):

    text = title.lower()

    if any(x in text for x in [
        "higher yields",
        "rising yields",
        "yield rises",
        "yields rise",
    ]):
        return (
            "🔴 Yield:\n"
            "Kenaikan yield dapat menekan Gold."
        )

    if any(x in text for x in [
        "lower yields",
        "falling yields",
        "yield falls",
        "yields fall",
    ]):
        return (
            "🟢 Yield:\n"
            "Penurunan yield dapat mendukung Gold."
        )

    return (
        "🟡 Yield:\n"
        "Perhatikan arah Treasury yield. "
        "Kenaikan yield dapat menekan Gold."
    )


# ============================================================
# OIL / WTI
# ============================================================

def analyze_oil(title):

    text = title.lower()

    bullish = [
        "wti rises",
        "wti gains",
        "wti climbs",
        "oil rises",
        "oil prices rise",
        "crude rises",
        "supply disruption",
        "oil supply disruption",
        "opec cut",
        "production cut",
        "strait of hormuz",
        "hormuz",
    ]

    bearish = [
        "wti falls",
        "wti declines",
        "wti drops",
        "oil falls",
        "oil prices fall",
        "crude falls",
        "oversupply",
        "production increase",
        "opec increase",
    ]

    bull = sum(
        1 for x in bullish
        if x in text
    )

    bear = sum(
        1 for x in bearish
        if x in text
    )

    if bull > bear:
        return (
            "🟢 Oil:\n"
            "WTI berpotensi menguat. Perubahan "
            "minyak dapat meningkatkan ekspektasi inflasi."
        )

    if bear > bull:
        return (
            "🔴 Oil:\n"
            "WTI berpotensi melemah. Perhatikan "
            "dampaknya terhadap ekspektasi inflasi."
        )

    return (
        "🟡 Oil:\n"
        "Perubahan WTI dapat mempengaruhi "
        "ekspektasi inflasi."
    )


# ============================================================
# DUPLICATE NORMALIZATION
# ============================================================

def normalize_title(title):

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        title.lower()
    ).strip()


# ============================================================
# FETCH ONE RSS
# ============================================================

async def fetch_feed(session, source, url):

    try:

        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=15),
            headers={
                "User-Agent":
                "XAUUSD-Assistant/1.0"
            },
        ) as response:

            if response.status != 200:
                print(
                    f"{source} RSS HTTP {response.status}"
                )
                return []

            content = await response.text()

            feed = feedparser.parse(content)

            results = []

            for entry in feed.entries:

                title = html.unescape(
                    (
                        entry.get("title")
                        or ""
                    ).strip()
                )

                url = (
                    entry.get("link")
                    or ""
                ).strip()

                published = (
                    entry.get("published")
                    or entry.get("updated")
                    or ""
                )

                if not title or not url:
                    continue

                score = calculate_score(title)

                if score < 70:
                    continue

                results.append({
                    "title": title,
                    "url": url,
                    "source": source,
                    "published": published,
                    "score": score,
                })

            return results

    except Exception as e:

        print(
            f"{source} RSS ERROR: {e}"
        )

        return []


# ============================================================
# GET NEWS
# ============================================================

async def get_news():

    articles = []

    timeout = aiohttp.ClientTimeout(
        total=30
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        tasks = []

        for source, feeds in RSS_FEEDS.items():

            for feed_url in feeds:

                tasks.append(
                    fetch_feed(
                        session,
                        source,
                        feed_url,
                    )
                )

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        for result in results:

            if isinstance(result, list):
                articles.extend(result)

    # ========================================================
    # DEDUPLICATE
    # ========================================================

    unique = {}

    for article in articles:

        key = normalize_title(
            article["title"]
        )

        if key not in unique:

            unique[key] = article

        elif (
            article["score"]
            > unique[key]["score"]
        ):

            unique[key] = article

    articles = list(
        unique.values()
    )

    articles.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return articles[:20]


# ============================================================
# FORMAT BREAKING NEWS
# ============================================================

def format_breaking_news(article):

    title = article["title"]

    category = get_category(title)

    impact = get_impact(
        article["score"]
    )

    gold = analyze_gold(title)
    usd = analyze_usd(title)
    yield_info = analyze_yield(title)
    oil = analyze_oil(title)

    return (
        "🚨 BREAKING NEWS\n\n"

        f"📂 {category}\n\n"

        f"📰 {title}\n\n"

        f"⚠️ {impact}\n"

        f"{gold}\n"

        f"{usd}\n"

        f"{yield_info}\n"

        f"{oil}\n"

        f"🔗 {article['url']}"
    )

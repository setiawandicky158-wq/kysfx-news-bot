import aiohttp
import feedparser
import re
import time


# ============================================================
# RSS SOURCES
# ============================================================

RSS_FEEDS = {
    "CNBC": [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    ],

    "MarketWatch": [
        "https://feeds.marketwatch.com/marketwatch/topstories/",
    ],
}


# ============================================================
# KEYWORDS
# ============================================================

KEYWORDS = {
    # GOLD
    "gold": 100,
    "xauusd": 120,
    "bullion": 80,
    "gold price": 100,
    "gold prices": 100,

    # FED
    "federal reserve": 120,
    "fed": 80,
    "fomc": 120,
    "interest rate": 100,
    "rate cut": 110,
    "rate hike": 110,
    "hawkish": 100,
    "dovish": 100,

    # US DATA
    "nfp": 130,
    "nonfarm payroll": 130,
    "jobs report": 120,
    "employment": 80,
    "unemployment": 90,
    "cpi": 120,
    "inflation": 100,
    "pce": 120,
    "ppi": 100,
    "retail sales": 80,
    "gdp": 70,

    # USD
    "us dollar": 90,
    "dollar": 60,
    "usd": 60,
    "dxy": 110,

    # YIELD
    "treasury yield": 110,
    "treasury yields": 110,
    "10-year yield": 120,
    "10 year yield": 120,
    "bond yields": 100,

    # WTI / OIL
    "wti": 130,
    "west texas intermediate": 130,
    "wti crude": 130,
    "crude oil": 110,
    "oil prices": 100,
    "oil price": 100,
    "oil supply": 110,
    "oil inventory": 110,
    "oil inventories": 110,
    "eia": 100,
    "opec": 110,
    "opec+": 120,

    # GEOPOLITICAL
    "iran": 110,
    "israel": 100,
    "gaza": 90,
    "ukraine": 80,
    "russia": 70,
    "war": 100,
    "missile": 100,
    "attack": 90,
    "strike": 90,
    "military": 80,
    "ceasefire": 90,
    "sanctions": 90,
    "hormuz": 120,
    "strait of hormuz": 130,

    # RISK
    "safe haven": 100,
    "risk off": 100,
    "risk-off": 100,
    "market turmoil": 90,
}


# ============================================================
# EXCLUDE
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
    "celebrity",
    "fashion",
    "handbag",
    "restaurant",
    "real estate",
    "housing",
    "wedding",
]


# ============================================================
# SCORE
# ============================================================

def score_article(title):

    text = title.lower()

    score = 0

    for keyword, points in KEYWORDS.items():

        if keyword in text:
            score += points

    for word in EXCLUDE:

        if word in text:
            score -= 150

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
# GOLD ANALYSIS
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

    bull = sum(x in text for x in bullish)
    bear = sum(x in text for x in bearish)

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
            "dapat memberi tekanan pada Gold."
        )

    return (
        "🟡 Gold:\n"
        "Potensi volatilitas tinggi. "
        "Tunggu reaksi harga."
    )


# ============================================================
# USD ANALYSIS
# ============================================================

def analyze_usd(title):

    text = title.lower()

    if any(x in text for x in [
        "weak dollar",
        "dollar falls",
        "dollar declines",
        "rate cut",
        "dovish",
        "lower yields",
    ]):
        return (
            "🟢 USD:\n"
            "Berpotensi melemah. Kondisi ini "
            "dapat mendukung Gold."
        )

    if any(x in text for x in [
        "strong dollar",
        "dollar rises",
        "rate hike",
        "hawkish",
        "higher yields",
    ]):
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
# OIL
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

    bull = sum(x in text for x in bullish)
    bear = sum(x in text for x in bearish)

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
# NORMALIZE TITLE
# ============================================================

def normalize_title(title):

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        title.lower()
    ).strip()


# ============================================================
# FETCH RSS
# ============================================================

async def fetch_feed(session, source, url):

    try:

        async with session.get(
            url,
            timeout=15,
            headers={
                "User-Agent":
                "XAUUSD-Assistant/1.0"
            },
        ) as response:

            if response.status != 200:
                return []

            content = await response.text()

            feed = feedparser.parse(content)

            results = []

            for entry in feed.entries:

                title = (
                    entry.get("title")
                    or ""
                ).strip()

                link = (
                    entry.get("link")
                    or ""
                ).strip()

                published = (
                    entry.get("published")
                    or entry.get("updated")
                    or ""
                )

                if not title or not link:
                    continue

                score = score_article(title)

                if score < 70:
                    continue

                results.append({
                    "title": title,
                    "url": link,
                    "source": source,
                    "published": published,
                    "score": score,
                })

            return results

    except Exception:

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

            for url in feeds:

                tasks.append(
                    fetch_feed(
                        session,
                        source,
                        url
                    )
                )

        results = await __import__(
            "asyncio"
        ).gather(
            *tasks,
            return_exceptions=True
        )

        for result in results:

            if isinstance(result, list):
                articles.extend(result)

    # ========================================================
    # REMOVE DUPLICATES
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
# FORMAT
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

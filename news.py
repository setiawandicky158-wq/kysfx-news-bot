 import asyncio
import aiohttp
import feedparser
import re
import html


# ============================================================
# RSS NEWS SOURCES
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

    "CNBC Markets": [
        "https://www.cnbc.com/id/15839135/device/rss/rss.html",
    ],

    "MarketWatch": [
        "https://feeds.marketwatch.com/marketwatch/topstories/",
    ],

    "MarketWatch MarketPulse": [
        "https://feeds.marketwatch.com/marketwatch/marketpulse/",
    ],
}


# ============================================================
# KEYWORDS
# ============================================================

KEYWORDS = {

    # --------------------------------------------------------
    # GOLD / XAUUSD
    # --------------------------------------------------------

    "gold": 100,
    "xauusd": 150,
    "xau/usd": 150,
    "gold price": 120,
    "gold prices": 120,
    "gold futures": 110,
    "bullion": 90,
    "precious metal": 80,
    "precious metals": 80,

    # --------------------------------------------------------
    # FED
    # --------------------------------------------------------

    "federal reserve": 130,
    "fomc": 140,
    "fed": 80,
    "interest rate": 110,
    "interest rates": 110,
    "rate cut": 130,
    "rate cuts": 130,
    "rate hike": 130,
    "rate hikes": 130,
    "hawkish": 120,
    "dovish": 120,
    "jerome powell": 130,
    "powell": 100,

    # --------------------------------------------------------
    # US ECONOMIC DATA
    # --------------------------------------------------------

    "nfp": 150,
    "nonfarm payroll": 150,
    "non-farm payroll": 150,
    "jobs report": 130,
    "employment report": 130,
    "employment": 80,
    "unemployment": 110,
    "unemployment rate": 120,
    "jobless claims": 120,
    "initial jobless claims": 120,

    "cpi": 140,
    "consumer price index": 140,
    "inflation": 120,
    "inflation data": 130,

    "pce": 140,
    "core pce": 150,
    "personal consumption expenditures": 140,

    "ppi": 120,
    "producer price index": 120,

    "retail sales": 100,
    "gdp": 90,
    "economic growth": 80,

    # --------------------------------------------------------
    # USD / DXY
    # --------------------------------------------------------

    "us dollar": 110,
    "u.s. dollar": 110,
    "dollar": 60,
    "usd": 70,
    "dxy": 130,
    "dollar index": 130,

    "dollar rises": 100,
    "dollar gains": 100,
    "dollar falls": 100,
    "dollar weakens": 100,
    "dollar strengthens": 100,

    # --------------------------------------------------------
    # TREASURY / YIELD
    # --------------------------------------------------------

    "treasury yield": 130,
    "treasury yields": 130,
    "treasury": 80,

    "10-year yield": 140,
    "10 year yield": 140,
    "10-year treasury": 130,
    "10 year treasury": 130,

    "bond yields": 110,
    "bond yield": 110,
    "yields rise": 110,
    "yields fall": 110,
    "rising yields": 120,
    "falling yields": 120,
    "higher yields": 120,
    "lower yields": 120,

    # --------------------------------------------------------
    # WTI / OIL
    # --------------------------------------------------------

    "wti": 150,
    "wti crude": 150,
    "west texas intermediate": 150,

    "crude oil": 120,
    "crude prices": 110,
    "crude price": 110,

    "oil price": 110,
    "oil prices": 110,

    "oil rises": 110,
    "oil gains": 110,
    "oil climbs": 110,
    "oil falls": 110,
    "oil drops": 110,
    "oil declines": 110,

    "oil supply": 120,
    "oil demand": 100,
    "oil inventory": 130,
    "oil inventories": 130,

    "eia": 120,
    "opec": 130,
    "opec+": 140,
    "production cut": 130,
    "production cuts": 130,
    "production increase": 100,

    # --------------------------------------------------------
    # GEOPOLITICAL
    # --------------------------------------------------------

    "iran": 130,
    "israel": 110,
    "gaza": 110,
    "hamas": 100,

    "ukraine": 100,
    "russia": 90,

    "war": 110,
    "war risk": 120,

    "missile": 120,
    "missiles": 120,

    "attack": 110,
    "attacks": 110,

    "strike": 110,
    "strikes": 110,

    "military": 100,
    "military action": 120,

    "ceasefire": 110,
    "peace talks": 90,
    "peace deal": 100,

    "sanctions": 110,

    "geopolitical": 100,
    "geopolitical tensions": 120,

    "middle east": 110,
    "west asia": 110,

    "hormuz": 150,
    "strait of hormuz": 160,

    # --------------------------------------------------------
    # RISK SENTIMENT
    # --------------------------------------------------------

    "safe haven": 120,
    "safe-haven": 120,

    "risk off": 120,
    "risk-off": 120,

    "market turmoil": 110,
    "market volatility": 90,

    "global markets": 60,
}


# ============================================================
# EXCLUDE IRRELEVANT CONTENT
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
    "cinema",
    "music",
    "singer",
    "celebrity",
    "actor",
    "actress",

    "fashion",
    "handbag",
    "luxury",

    "restaurant",
    "food",
    "cooking",

    "real estate",
    "housing",
    "property market",

    "wedding",
    "tourism",
    "travel",

    "video game",
    "gaming",
]


# ============================================================
# SCORE ARTICLE
# ============================================================

def calculate_score(text):

    text = text.lower()

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

    # Employment
    if any(x in text for x in [
        "nfp",
        "nonfarm payroll",
        "non-farm payroll",
        "jobs report",
        "employment report",
        "employment",
        "unemployment",
        "jobless claims",
    ]):
        return "💼 Tenaga Kerja"

    # Inflation
    if any(x in text for x in [
        "cpi",
        "consumer price index",
        "inflation",
        "pce",
        "core pce",
        "ppi",
        "producer price index",
    ]):
        return "📊 Inflasi"

    # Fed
    if any(x in text for x in [
        "federal reserve",
        "fomc",
        "fed",
        "interest rate",
        "interest rates",
        "rate cut",
        "rate cuts",
        "rate hike",
        "rate hikes",
        "hawkish",
        "dovish",
        "jerome powell",
        "powell",
    ]):
        return "🏦 Fed / Suku Bunga"

    # Oil
    if any(x in text for x in [
        "wti",
        "wti crude",
        "west texas intermediate",
        "crude oil",
        "crude price",
        "crude prices",
        "oil price",
        "oil prices",
        "oil supply",
        "oil demand",
        "oil inventory",
        "oil inventories",
        "opec",
        "eia",
        "hormuz",
        "strait of hormuz",
    ]):
        return "🛢️ WTI / Oil"

    # Geopolitical
    if any(x in text for x in [
        "iran",
        "israel",
        "gaza",
        "hamas",
        "ukraine",
        "russia",
        "war",
        "missile",
        "missiles",
        "attack",
        "attacks",
        "strike",
        "strikes",
        "military",
        "ceasefire",
        "peace talks",
        "peace deal",
        "sanctions",
        "geopolitical",
        "middle east",
        "west asia",
        "hormuz",
        "strait of hormuz",
    ]):
        return "🌍 Geopolitik"

    # Yield
    if any(x in text for x in [
        "treasury",
        "yield",
        "yields",
        "10-year",
        "10 year",
        "bond yield",
        "bond yields",
    ]):
        return "📈 US Treasury / Yield"

    # USD
    if any(x in text for x in [
        "dxy",
        "dollar index",
        "dollar",
        "usd",
        "u.s. dollar",
        "us dollar",
    ]):
        return "💵 USD"

    # Gold
    if any(x in text for x in [
        "gold",
        "xauusd",
        "xau/usd",
        "bullion",
        "precious metal",
        "precious metals",
    ]):
        return "🥇 Gold"

    return "🌐 Makro"


# ============================================================
# IMPACT
# ============================================================

def get_impact(score):

    if score >= 300:
        return "High Impact News ⭐⭐⭐⭐⭐"

    if score >= 220:
        return "High Impact News ⭐⭐⭐⭐"

    if score >= 140:
        return "Medium Impact News ⭐⭐⭐"

    if score >= 80:
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
        "rate cuts",

        "dovish",

        "weak dollar",
        "dollar falls",
        "dollar weakens",

        "falling yields",
        "lower yields",

        "safe haven",
        "safe-haven",

        "risk off",
        "risk-off",

        "war",
        "attack",
        "attacks",
        "missile",
        "missiles",
        "strike",
        "strikes",

        "iran",
        "israel",
        "gaza",
        "ukraine",

        "sanctions",

        "hormuz",
        "strait of hormuz",
    ]

    bearish = [

        "gold falls",
        "gold declines",
        "gold drops",
        "gold retreats",

        "rate hike",
        "rate hikes",

        "hawkish",

        "strong dollar",
        "dollar rises",
        "dollar strengthens",

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
# USD ANALYSIS
# ============================================================

def analyze_usd(title):

    text = title.lower()

    bearish = [

        "weak dollar",
        "dollar falls",
        "dollar declines",
        "dollar weakens",

        "rate cut",
        "rate cuts",

        "dovish",

        "lower yields",
        "falling yields",
    ]

    bullish = [

        "strong dollar",
        "dollar rises",
        "dollar gains",
        "dollar strengthens",

        "rate hike",
        "rate hikes",

        "hawkish",

        "higher yields",
        "rising yields",
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
# YIELD ANALYSIS
# ============================================================

def analyze_yield(title):

    text = title.lower()

    if any(x in text for x in [
        "higher yields",
        "rising yields",
        "yield rises",
        "yields rise",
        "yield climbs",
        "yields climb",
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
        "yield declines",
        "yields decline",
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
# WTI / OIL ANALYSIS
# ============================================================

def analyze_oil(title):

    text = title.lower()

    bullish = [

        "wti rises",
        "wti gains",
        "wti climbs",

        "oil rises",
        "oil gains",
        "oil climbs",

        "oil prices rise",
        "oil price rises",

        "crude rises",
        "crude gains",
        "crude climbs",

        "supply disruption",
        "supply disruptions",

        "oil supply disruption",

        "opec cut",
        "opec cuts",

        "production cut",
        "production cuts",

        "strait of hormuz",
        "hormuz",
    ]

    bearish = [

        "wti falls",
        "wti declines",
        "wti drops",

        "oil falls",
        "oil declines",
        "oil drops",

        "oil prices fall",
        "oil price falls",

        "crude falls",
        "crude declines",
        "crude drops",

        "oversupply",

        "production increase",
        "production increases",

        "opec increase",
        "opec increases",
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

async def fetch_feed(
    session,
    source,
    feed_url
):

    try:

        async with session.get(
            feed_url,
            timeout=aiohttp.ClientTimeout(
                total=15
            ),
            headers={
                "User-Agent":
                "Mozilla/5.0 "
                "(XAUUSD Assistant)"
            },
        ) as response:

            if response.status != 200:

                print(
                    f"[RSS] {source}: "
                    f"HTTP {response.status}"
                )

                return []

            content = await response.text()

            feed = feedparser.parse(
                content
            )

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

                description = html.unescape(
                    (
                        entry.get("summary")
                        or entry.get("description")
                        or ""
                    ).strip()
                )

                published = (
                    entry.get("published")
                    or entry.get("updated")
                    or ""
                )

                if not title or not url:
                    continue

                # --------------------------------------------
                # ANALYZE TITLE + DESCRIPTION
                # --------------------------------------------

                searchable_text = (
                    f"{title} "
                    f"{description}"
                )

                score = calculate_score(
                    searchable_text
                )

                # Minimum relevance
                if score < 70:
                    continue

                results.append({
                    "title": title,
                    "url": url,
                    "source": source,
                    "published": published,
                    "description": description,
                    "score": score,
                })

            print(
                f"[RSS] {source}: "
                f"{len(results)} relevant"
            )

            return results

    except Exception as e:

        print(
            f"[RSS ERROR] {source}: {e}"
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

            if isinstance(
                result,
                list
            ):

                articles.extend(
                    result
                )

    # ========================================================
    # DEDUPLICATE
    # ========================================================

    unique = {}

    for article in articles:

        key = normalize_title(
            article["title"]
        )

        if not key:
            continue

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

    # ========================================================
    # SORT BY IMPACT
    # ========================================================

    articles.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    # Maximum 20
    return articles[:20]


# ============================================================
# FORMAT BREAKING NEWS
# ============================================================

def format_breaking_news(article):

    title = article["title"]

    category = get_category(
        title
    )

    impact = get_impact(
        article["score"]
    )

    gold = analyze_gold(
        title
    )

    usd = analyze_usd(
        title
    )

    yield_info = analyze_yield(
        title
    )

    oil = analyze_oil(
        title
    )

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

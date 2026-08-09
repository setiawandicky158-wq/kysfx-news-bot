import asyncio
import aiohttp
import feedparser
import re
import html
from urllib.parse import quote


# ============================================================
# XAUUSD NEWS ENGINE
# No GDELT
# ============================================================


# ============================================================
# DIRECT RSS SOURCES
# ============================================================

RSS_FEEDS = {

    "CNBC Economy":
        "https://www.cnbc.com/id/20910258/device/rss/rss.html",

    "CNBC Energy":
        "https://www.cnbc.com/id/19836768/device/rss/rss.html",

    "CNBC Asia":
        "https://www.cnbc.com/id/19832390/device/rss/rss.html",

    "CNBC Markets":
        "https://www.cnbc.com/id/15839135/device/rss/rss.html",

    "MarketWatch":
        "https://feeds.marketwatch.com/marketwatch/topstories/",

    "MarketWatch MarketPulse":
        "https://feeds.marketwatch.com/marketwatch/marketpulse/",
}


# ============================================================
# GOOGLE NEWS RSS SEARCH
# ============================================================

GOOGLE_NEWS_QUERIES = [

    "XAUUSD gold price",

    "gold Federal Reserve",

    "gold Fed FOMC",

    "gold CPI inflation",

    "gold NFP employment",

    "gold US dollar DXY",

    "gold Treasury yield",

    "gold interest rates",

    "WTI crude oil",

    "WTI oil OPEC",

    "oil prices",

    "oil inventory EIA",

    "Iran Israel",

    "Middle East tensions",

    "Strait of Hormuz",

    "geopolitical gold",

]


def google_news_url(query):

    encoded = quote(query)

    return (
        "https://news.google.com/rss/search?"
        f"q={encoded}"
        "&hl=en-US"
        "&gl=US"
        "&ceid=US:en"
    )


# ============================================================
# KEYWORDS
# ============================================================

KEYWORDS = {

    # --------------------------------------------------------
    # GOLD
    # --------------------------------------------------------

    "gold": 100,
    "xauusd": 180,
    "xau/usd": 180,
    "gold price": 130,
    "gold prices": 130,
    "gold futures": 120,
    "gold market": 100,
    "bullion": 90,
    "precious metal": 90,
    "precious metals": 90,

    # --------------------------------------------------------
    # FED
    # --------------------------------------------------------

    "federal reserve": 140,
    "fomc": 150,
    "fed": 80,
    "fed minutes": 140,
    "fed meeting": 140,

    "interest rate": 120,
    "interest rates": 120,

    "rate cut": 140,
    "rate cuts": 140,

    "rate hike": 140,
    "rate hikes": 140,

    "hawkish": 130,
    "dovish": 130,

    "jerome powell": 140,
    "powell": 100,

    # --------------------------------------------------------
    # US DATA
    # --------------------------------------------------------

    "nfp": 160,
    "nonfarm payroll": 160,
    "non-farm payroll": 160,

    "jobs report": 140,
    "employment report": 140,

    "unemployment": 120,
    "unemployment rate": 130,

    "jobless claims": 130,
    "initial jobless claims": 130,

    "cpi": 150,
    "consumer price index": 150,

    "inflation": 120,
    "inflation data": 130,

    "pce": 150,
    "core pce": 160,
    "personal consumption expenditures": 150,

    "ppi": 130,
    "producer price index": 130,

    "retail sales": 100,
    "gdp": 100,

    # --------------------------------------------------------
    # USD
    # --------------------------------------------------------

    "dxy": 140,
    "dollar index": 140,

    "us dollar": 110,
    "u.s. dollar": 110,

    "dollar rises": 100,
    "dollar gains": 100,
    "dollar strengthens": 100,

    "dollar falls": 100,
    "dollar declines": 100,
    "dollar weakens": 100,

    # --------------------------------------------------------
    # TREASURY / YIELD
    # --------------------------------------------------------

    "treasury yield": 140,
    "treasury yields": 140,

    "10-year yield": 150,
    "10 year yield": 150,

    "10-year treasury": 140,
    "10 year treasury": 140,

    "bond yield": 120,
    "bond yields": 120,

    "rising yields": 130,
    "falling yields": 130,

    "higher yields": 130,
    "lower yields": 130,

    "yield rises": 120,
    "yield falls": 120,

    # --------------------------------------------------------
    # WTI / OIL
    # --------------------------------------------------------

    "wti": 160,
    "wti crude": 160,
    "west texas intermediate": 160,

    "crude oil": 130,
    "crude price": 120,
    "crude prices": 120,

    "oil price": 120,
    "oil prices": 120,

    "oil rises": 120,
    "oil gains": 120,
    "oil climbs": 120,

    "oil falls": 120,
    "oil drops": 120,
    "oil declines": 120,

    "oil supply": 130,
    "oil demand": 110,

    "oil inventory": 140,
    "oil inventories": 140,

    "eia": 130,

    "opec": 140,
    "opec+": 150,

    "production cut": 140,
    "production cuts": 140,

    "supply disruption": 140,
    "supply disruptions": 140,

    # --------------------------------------------------------
    # GEOPOLITICAL
    # --------------------------------------------------------

    "iran": 140,
    "israel": 120,
    "gaza": 120,
    "hamas": 110,

    "ukraine": 110,
    "russia": 100,

    "war": 110,
    "war risk": 130,

    "missile": 130,
    "missiles": 130,

    "attack": 120,
    "attacks": 120,

    "strike": 120,
    "strikes": 120,

    "military": 100,
    "military action": 130,

    "ceasefire": 120,
    "peace talks": 100,
    "peace deal": 110,

    "sanctions": 120,

    "geopolitical": 110,
    "geopolitical tensions": 130,

    "middle east": 120,
    "west asia": 120,

    "hormuz": 160,
    "strait of hormuz": 180,

    # --------------------------------------------------------
    # MARKET RISK
    # --------------------------------------------------------

    "safe haven": 130,
    "safe-haven": 130,

    "risk off": 130,
    "risk-off": 130,

    "market turmoil": 120,
    "market volatility": 100,

    "global markets": 60,
}


# ============================================================
# IRRELEVANT NEWS
# ============================================================

EXCLUDE = [

    "football",
    "soccer",
    "basketball",
    "tennis",
    "judo",
    "taekwondo",
    "badminton",

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
    "luxury handbag",

    "restaurant",
    "food",
    "cooking",
    "recipe",

    "real estate",
    "housing",
    "property market",
    "apartment",

    "wedding",
    "tourism",
    "travel",

    "video game",
    "gaming",
    "game review",

    "smartphone",
    "iphone",
    "android",
]


# ============================================================
# SCORE
# ============================================================

def calculate_score(text):

    text = text.lower()

    score = 0

    for keyword, points in KEYWORDS.items():

        if keyword in text:
            score += points

    for word in EXCLUDE:

        if word in text:
            score -= 250

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

    # Geopolitics
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
        1
        for x in bullish
        if x in text
    )

    bear = sum(
        1
        for x in bearish
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
        1
        for x in bearish
        if x in text
    )

    bull = sum(
        1
        for x in bullish
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
# OIL / WTI ANALYSIS
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
        1
        for x in bullish
        if x in text
    )

    bear = sum(
        1
        for x in bearish
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
# NORMALIZE
# ============================================================

def normalize_title(title):

    return re.sub(
        r"[^a-z0-9]+",
        " ",
        title.lower()
    ).strip()


# ============================================================
# FETCH RSS FEED
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
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/151.0 Safari/537.36"
            },
        ) as response:

            if response.status != 200:

                print(
                    f"[RSS] {source} "
                    f"HTTP {response.status}"
                )

                return []

            content = await response.read()

            feed = feedparser.parse(
                content
            )

            if not feed.entries:

                print(
                    f"[RSS] {source}: "
                    f"0 entries"
                )

                return []

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

                searchable_text = (
                    f"{title} "
                    f"{description}"
                )

                score = calculate_score(
                    searchable_text
                )

                if score < 60:
                    continue

                results.append({

                    "title": title,

                    "url": url,

                    "source": source,

                    "published": published,

                    "description":
                        description,

                    "score": score,
                })

            print(
                f"[RSS] {source}: "
                f"{len(feed.entries)} entries / "
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
        total=40
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        tasks = []

        # ----------------------------------------------------
        # DIRECT RSS
        # ----------------------------------------------------

        for source, url in RSS_FEEDS.items():

            tasks.append(
                fetch_feed(
                    session,
                    source,
                    url
                )
            )

        # ----------------------------------------------------
        # GOOGLE NEWS RSS
        # ----------------------------------------------------

        for query in GOOGLE_NEWS_QUERIES:

            tasks.append(
                fetch_feed(
                    session,
                    f"Google News: {query}",
                    google_news_url(query)
                )
            )

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True
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

        else:

            if (
                article["score"]
                > unique[key]["score"]
            ):

                unique[key] = article

    articles = list(
        unique.values()
    )

    # ========================================================
    # SORT
    # ========================================================

    articles.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    print(
        f"[NEWS] Total relevant articles: "
        f"{len(articles)}"
    )

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
        "🚨 BREAKING NEWS\n"

        "📂 "
        f"{category}\n"

        "📰 "
        f"{title}\n"

        "⚠️ "
        f"{impact}\n"

        f"{gold}\n"

        f"{usd}\n"

        f"{yield_info}\n"

        f"{oil}\n"

        "🔗 "
        f"{article['url']}"
    )


# ============================================================
# SIMPLE NEWS FORMAT
# ============================================================

def format_news(article):

    title = article["title"]

    category = get_category(
        title
    )

    impact = get_impact(
        article["score"]
    )

    return (
        "🥇 XAUUSD NEWS\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📂 {category}\n"
        f"📰 {title}\n"
        f"🏢 {article['source']}\n"
        f"⚠️ {impact}\n"
        f"🔗 {article['url']}\n"
        "━━━━━━━━━━━━━━━━━━"
    )

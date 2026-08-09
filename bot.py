import os
import logging
import re
import aiohttp

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


# ============================================================
# CONFIG
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


# ============================================================
# KEYWORDS
# ============================================================

KEYWORDS = {

    # GOLD
    "xauusd": 100,
    "gold price": 90,
    "gold prices": 90,
    "gold rises": 80,
    "gold falls": 80,
    "gold futures": 80,
    "bullion": 60,

    # FED
    "federal reserve": 100,
    "fomc": 100,
    "fed": 80,
    "interest rate": 80,
    "interest rates": 80,
    "rate cut": 90,
    "rate hike": 90,
    "hawkish": 80,
    "dovish": 80,

    # ECONOMIC DATA
    "cpi": 90,
    "inflation": 80,
    "nonfarm payroll": 100,
    "nfp": 100,
    "jobs report": 90,
    "unemployment": 80,
    "pce": 90,
    "ppi": 80,
    "retail sales": 60,
    "gdp": 60,

    # USD / YIELD
    "us dollar": 70,
    "usd": 60,
    "dollar": 45,
    "dxy": 90,
    "treasury yield": 90,
    "treasury yields": 90,
    "10-year yield": 100,
    "10 year yield": 100,
    "bond yields": 70,

    # WTI
    "wti": 120,
    "west texas intermediate": 120,
    "wti crude": 120,
    "us crude": 100,
    "crude oil": 90,
    "oil price": 80,
    "oil prices": 80,
    "oil supply": 90,
    "oil production": 70,
    "oil inventory": 100,
    "oil inventories": 100,
    "eia": 80,
    "api inventories": 80,
    "opec": 90,
    "opec+": 100,
    "saudi arabia": 60,
    "strait of hormuz": 100,

    # GEOPOLITICAL
    "iran": 90,
    "israel": 70,
    "gaza": 60,
    "ukraine": 60,
    "russia": 50,
    "war": 80,
    "missile": 80,
    "attack": 70,
    "strike": 70,
    "military": 60,
    "ceasefire": 70,
    "sanctions": 70,
    "peace talks": 60,
    "geopolitical": 60,

    # RISK
    "safe haven": 90,
    "risk off": 80,
    "risk-off": 80,
    "market turmoil": 70,
}


NEGATIVE_WORDS = {
    "football",
    "soccer",
    "basketball",
    "tennis",
    "judo",
    "taekwondo",
    "actor",
    "actress",
    "movie",
    "film",
    "music",
    "singer",
    "celebrity",
    "restaurant",
    "fashion",
    "handbag",
    "real estate",
    "property",
    "housing",
    "wedding",
    "recipe",
    "tourism",
    "festival",
    "school",
}


# ============================================================
# SCORE
# ============================================================

def calculate_score(title):

    text = title.lower()
    score = 0

    for keyword, points in KEYWORDS.items():

        if keyword in text:
            score += points

    for keyword in NEGATIVE_WORDS:

        if keyword in text:
            score -= 100

    return score


def get_stars(score):

    if score >= 180:
        return "⭐⭐⭐⭐⭐"

    if score >= 130:
        return "⭐⭐⭐⭐"

    if score >= 90:
        return "⭐⭐⭐"

    if score >= 60:
        return "⭐⭐"

    return "⭐"


# ============================================================
# CATEGORY
# ============================================================

def get_category(title):

    text = title.lower()

    if any(word in text for word in [
        "nfp",
        "nonfarm payroll",
        "jobs report",
        "unemployment",
        "jobless",
        "employment",
    ]):
        return "💼 Tenaga Kerja"

    if any(word in text for word in [
        "cpi",
        "inflation",
        "pce",
        "ppi",
    ]):
        return "📊 Inflasi"

    if any(word in text for word in [
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

    if any(word in text for word in [
        "wti",
        "west texas intermediate",
        "wti crude",
        "us crude",
        "crude oil",
        "oil price",
        "oil prices",
        "oil supply",
        "oil inventory",
        "oil inventories",
        "opec",
        "eia",
        "strait of hormuz",
    ]):
        return "🛢️ WTI / Oil"

    if any(word in text for word in [
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
    ]):
        return "🌍 Geopolitik"

    if any(word in text for word in [
        "treasury",
        "yield",
        "10-year yield",
        "10 year yield",
        "bond yields",
    ]):
        return "📈 US Treasury / Yield"

    if any(word in text for word in [
        "dxy",
        "dollar",
        "usd",
    ]):
        return "💵 USD"

    if any(word in text for word in [
        "gold",
        "xauusd",
        "bullion",
    ]):
        return "🥇 Gold"

    return "🌐 Makro"


# ============================================================
# XAUUSD ANALYSIS
# ============================================================

def analyze_gold(title):

    text = title.lower()

    bullish_words = [
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
        "escalation",
        "iran",
        "israel",
        "gaza",
        "ukraine",
        "sanctions",
    ]

    bearish_words = [
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

    bullish = sum(
        1 for word in bullish_words
        if word in text
    )

    bearish = sum(
        1 for word in bearish_words
        if word in text
    )

    if bullish > bearish:
        return (
            "🟢 Gold:\n"
            "Berpotensi bullish. "
            "Faktor berita mendukung permintaan Gold."
        )

    if bearish > bullish:
        return (
            "🔴 Gold:\n"
            "Berpotensi bearish. "
            "Faktor berita dapat memberi tekanan pada Gold."
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
        "rate cut",
        "dovish",
        "lower yields",
        "falling yields",
    ]

    bullish = [
        "strong dollar",
        "dollar rises",
        "rate hike",
        "hawkish",
        "higher yields",
        "rising yields",
    ]

    bull = sum(
        1 for word in bullish
        if word in text
    )

    bear = sum(
        1 for word in bearish
        if word in text
    )

    if bear > bull:
        return (
            "🟢 USD:\n"
            "Berpotensi melemah. "
            "Kondisi ini dapat mendukung Gold."
        )

    if bull > bear:
        return (
            "🔴 USD:\n"
            "Berpotensi menguat. "
            "Kondisi ini dapat menekan Gold."
        )

    return (
        "🟡 USD:\n"
        "Perhatikan arah dolar "
        "setelah rilis data/kebijakan."
    )


# ============================================================
# YIELD ANALYSIS
# ============================================================

def analyze_yield(title):

    text = title.lower()

    if any(word in text for word in [
        "higher yields",
        "rising yields",
        "10-year yield rises",
        "treasury yield rises",
    ]):
        return (
            "🔴 Yield:\n"
            "Kenaikan yield dapat menekan Gold."
        )

    if any(word in text for word in [
        "lower yields",
        "falling yields",
        "10-year yield falls",
        "treasury yield falls",
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
# OIL ANALYSIS
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
        1 for word in bullish
        if word in text
    )

    bear = sum(
        1 for word in bearish
        if word in text
    )

    if bull > bear:
        return (
            "🟢 Oil:\n"
            "WTI berpotensi menguat. "
            "Perubahan minyak dapat meningkatkan "
            "ekspektasi inflasi."
        )

    if bear > bull:
        return (
            "🔴 Oil:\n"
            "WTI berpotensi melemah. "
            "Perhatikan dampaknya terhadap ekspektasi inflasi."
        )

    return (
        "🟡 Oil:\n"
        "Perubahan WTI dapat mempengaruhi "
        "ekspektasi inflasi."
    )


# ============================================================
# ARTICLE FETCH
# ============================================================

async def get_news():

    queries = [
        "gold XAUUSD",
        "Federal Reserve gold",
        "FOMC gold",
        "CPI inflation gold",
        "NFP gold",
        "Treasury yield gold",
        "DXY dollar gold",

        "WTI crude oil",
        "West Texas Intermediate",
        "OPEC WTI",
        "EIA oil inventory",

        "Iran Israel gold",
        "West Asia oil",
        "geopolitical gold",
    ]

    articles = []

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        for query in queries:

            params = {
                "query": query,
                "mode": "artlist",
                "format": "json",
                "maxrecords": 20,
                "timespan": "24h",
                "sort": "DateDesc",
            }

            try:

                async with session.get(
                    GDELT_URL,
                    params=params,
                ) as response:

                    if response.status != 200:
                        continue

                    data = await response.json(
                        content_type=None
                    )

                    for article in data.get(
                        "articles",
                        []
                    ):

                        title = (
                            article.get("title")
                            or ""
                        ).strip()

                        url = (
                            article.get("url")
                            or ""
                        ).strip()

                        domain = (
                            article.get("domain")
                            or ""
                        ).strip()

                        date = (
                            article.get("seendate")
                            or ""
                        ).strip()

                        if not title or not url:
                            continue

                        score = calculate_score(title)

                        if score < 60:
                            continue

                        articles.append({
                            "title": title,
                            "url": url,
                            "domain": domain,
                            "date": date,
                            "score": score,
                        })

            except Exception:
                logging.exception(
                    "GDELT ERROR"
                )

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    unique = {}

    for article in articles:

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            article["title"].lower(),
        ).strip()

        if normalized not in unique:
            unique[normalized] = article

        elif (
            article["score"]
            > unique[normalized]["score"]
        ):
            unique[normalized] = article

    articles = list(unique.values())

    articles.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return articles[:10]


# ============================================================
# FORMAT BREAKING NEWS
# ============================================================

def format_breaking_news(article):

    title = article["title"]
    score = article["score"]

    category = get_category(title)
    stars = get_stars(score)

    gold = analyze_gold(title)
    usd = analyze_usd(title)
    yield_info = analyze_yield(title)
    oil = analyze_oil(title)

    message = (
        "🚨 BREAKING NEWS\n\n"

        f"📂 {category}\n\n"

        f"📰 {title}\n\n"

        f"⚠️ High Impact News {stars}\n"

        f"{gold}\n"

        f"{usd}\n"

        f"{yield_info}\n"

        f"{oil}\n"

        f"🔗 {article['url']}"
    )

    return message


# ============================================================
# TELEGRAM COMMANDS
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🥇 XAUUSD Assistant aktif!\n\n"
        "/news — Breaking News XAUUSD\n"
        "/status — status bot"
    )


async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🟢 BOT ONLINE\n\n"
        "News Engine: OK\n"
        "XAUUSD: ACTIVE\n"
        "WTI: ACTIVE\n"
        "USD: ACTIVE\n"
        "Yield: ACTIVE"
    )


async def news(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🔎 Mencari breaking news..."
    )

    try:

        articles = await get_news()

        if not articles:

            await update.message.reply_text(
                "❌ Tidak ada berita relevan."
            )

            return

        # Kirim berita paling relevan
        message = format_breaking_news(
            articles[0]
        )

        await update.message.reply_text(
            message,
            disable_web_page_preview=True,
        )

    except Exception as e:

        logging.exception(
            "NEWS ERROR"
        )

        await update.message.reply_text(
            f"❌ News Engine Error\n\n{str(e)[:500]}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN belum diatur di Railway."
        )

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("status", status)
    )

    app.add_handler(
        CommandHandler("news", news)
    )

    print(
        "🥇 XAUUSD Assistant sedang berjalan..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()

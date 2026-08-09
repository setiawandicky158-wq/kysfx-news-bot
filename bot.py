import os
import logging
import re
import aiohttp

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


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
    "xauusd": 120,
    "gold price": 100,
    "gold prices": 100,
    "gold rises": 90,
    "gold falls": 90,
    "gold futures": 90,
    "bullion": 70,

    # FED / USD
    "federal reserve": 100,
    "fomc": 100,
    "fed": 80,
    "interest rate": 80,
    "interest rates": 80,
    "rate cut": 90,
    "rate hike": 90,
    "monetary policy": 70,

    # US DATA
    "cpi": 90,
    "inflation": 80,
    "nonfarm payroll": 100,
    "nfp": 100,
    "jobs report": 90,
    "pce": 90,
    "ppi": 80,
    "unemployment": 70,

    # USD / YIELDS
    "us dollar": 70,
    "usd": 60,
    "dollar": 45,
    "dxy": 90,
    "treasury yield": 90,
    "treasury yields": 90,
    "10-year yield": 100,
    "10 year yield": 100,
    "bond yields": 70,

    # ========================================================
    # WTI / OIL
    # ========================================================

    "wti": 120,
    "west texas intermediate": 120,
    "wti crude": 120,
    "us crude": 100,
    "crude oil": 90,
    "oil price": 80,
    "oil prices": 80,
    "oil supply": 100,
    "oil production": 70,
    "oil inventory": 100,
    "oil inventories": 100,
    "eia": 80,
    "api inventories": 80,
    "opec": 90,
    "opec+": 100,
    "saudi arabia": 60,
    "strait of hormuz": 100,

    # GEOPOLITICS
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

    # MARKET SENTIMENT
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


def classify(score):

    if score >= 120:
        return "🔴 HIGH"

    if score >= 70:
        return "🟠 MEDIUM"

    return "🟢 LOW"


# ============================================================
# CATEGORY
# ============================================================

def get_category(title):

    text = title.lower()

    # WTI FIRST
    if any(
        word in text
        for word in [
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
        ]
    ):
        return "🛢️ WTI / OIL"

    # GEOPOLITICAL
    if any(
        word in text
        for word in [
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
        ]
    ):
        return "🌍 GEOPOLITICAL"

    # FED / USD
    if any(
        word in text
        for word in [
            "fed",
            "federal reserve",
            "fomc",
            "interest rate",
            "rate cut",
            "rate hike",
            "cpi",
            "nfp",
            "nonfarm payroll",
            "pce",
            "ppi",
            "treasury",
            "yield",
            "dxy",
            "dollar",
        ]
    ):
        return "🇺🇸 FED / USD"

    # GOLD
    if any(
        word in text
        for word in [
            "gold",
            "xauusd",
            "bullion",
        ]
    ):
        return "🥇 GOLD"

    return "📰 MACRO"


# ============================================================
# IMPACT ANALYSIS
# ============================================================

def analyze_xauusd(title):

    text = title.lower()

    bullish = [
        "rate cut",
        "lower yields",
        "falling yields",
        "weak dollar",
        "safe haven",
        "risk off",
        "war",
        "attack",
        "missile",
        "escalation",
        "sanctions",
        "geopolitical",
        "iran",
        "israel",
        "gaza",
        "ukraine",
    ]

    bearish = [
        "rate hike",
        "higher yields",
        "rising yields",
        "strong dollar",
        "hawkish fed",
        "hawkish",
        "strong jobs",
        "hot cpi",
        "higher inflation",
    ]

    bullish_score = sum(
        1 for word in bullish if word in text
    )

    bearish_score = sum(
        1 for word in bearish if word in text
    )

    if bullish_score > bearish_score:
        return "🟢 BULLISH"

    if bearish_score > bullish_score:
        return "🔴 BEARISH"

    return "🟡 MIXED"


def why_it_matters(title):

    text = title.lower()

    if any(
        word in text
        for word in [
            "iran",
            "israel",
            "gaza",
            "war",
            "missile",
            "attack",
            "strike",
            "sanctions",
            "geopolitical",
        ]
    ):
        return (
            "Higher geopolitical risk can increase "
            "safe-haven demand for Gold."
        )

    if any(
        word in text
        for word in [
            "fed",
            "federal reserve",
            "fomc",
            "rate cut",
            "rate hike",
            "interest rate",
        ]
    ):
        return (
            "Changes in Fed expectations can affect "
            "USD, Treasury yields and the opportunity "
            "cost of holding Gold."
        )

    if any(
        word in text
        for word in [
            "cpi",
            "inflation",
            "pce",
            "ppi",
            "nfp",
            "nonfarm payroll",
        ]
    ):
        return (
            "US macro data can change rate expectations, "
            "USD and Treasury yields, which can strongly "
            "affect Gold."
        )

    if any(
        word in text
        for word in [
            "wti",
            "crude oil",
            "oil price",
            "oil prices",
            "opec",
            "oil supply",
            "oil inventory",
            "eia",
        ]
    ):
        return (
            "WTI can influence inflation expectations "
            "and risk sentiment, which can indirectly "
            "affect Gold through USD and Treasury yields."
        )

    return (
        "The event may affect risk sentiment, USD "
        "or macro expectations relevant to Gold."
    )


# ============================================================
# GDELT
# ============================================================

async def get_news():

    queries = [
        "gold XAUUSD",
        '"Federal Reserve" gold',
        "FOMC gold",
        "CPI inflation gold",
        "NFP gold",
        "Treasury yield gold",
        "DXY dollar gold",

        # WTI
        "WTI crude oil",
        '"West Texas Intermediate"',
        "OPEC WTI",
        "EIA oil inventory",

        # GEO
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

                        logging.warning(
                            f"GDELT {response.status}: {query}"
                        )

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

                        if score < 50:
                            continue

                        articles.append({
                            "title": title,
                            "url": url,
                            "domain": domain,
                            "date": date,
                            "score": score,
                            "impact": classify(score),
                            "category": get_category(title),
                            "xau": analyze_xauusd(title),
                            "why": why_it_matters(title),
                        })

            except Exception:

                logging.exception(
                    f"GDELT error: {query}"
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

    # Sort by score
    articles.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return articles[:10]


# ============================================================
# TELEGRAM COMMANDS
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🥇 XAUUSD Assistant aktif!\n\n"
        "/news — berita XAUUSD + WTI\n"
        "/status — status bot"
    )


async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🟢 BOT ONLINE\n\n"
        "Railway: OK\n"
        "News Engine: OK\n"
        "XAUUSD Filter: ACTIVE\n"
        "WTI Filter: ACTIVE"
    )


async def news(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🔎 Menganalisis XAUUSD + WTI..."
    )

    try:

        articles = await get_news()

        if not articles:

            await update.message.reply_text(
                "❌ Tidak menemukan berita "
                "yang relevan."
            )

            return

        message = (
            "🥇 XAUUSD NEWS\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )

        for article in articles:

            message += (
                f"{article['impact']} "
                f"{article['category']}\n\n"

                f"📰 {article['title']}\n\n"

                f"🥇 XAUUSD: "
                f"{article['xau']}\n\n"

                f"💡 WHY IT MATTERS\n"
                f"{article['why']}\n\n"

                f"🏢 {article['domain']}\n"
                f"🕐 {article['date']}\n"
                f"📊 Relevance: "
                f"{article['score']}\n\n"

                f"🔗 {article['url']}\n\n"

                "━━━━━━━━━━━━━━━━━━\n\n"
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
            "❌ News Engine Error\n\n"
            f"{str(e)[:500]}"
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

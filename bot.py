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

HIGH_IMPACT = {
    "xauusd": 100,
    "gold price": 90,
    "gold prices": 90,
    "gold rises": 80,
    "gold falls": 80,

    "federal reserve": 80,
    "fed": 70,
    "fomc": 80,
    "interest rate": 70,
    "interest rates": 70,
    "rate cut": 75,
    "rate hike": 75,

    "cpi": 80,
    "inflation": 70,
    "nonfarm payroll": 85,
    "nfp": 85,
    "jobs report": 75,
    "pce": 80,
    "ppi": 70,

    "treasury yield": 70,
    "treasury yields": 70,
    "10-year yield": 75,
    "10 year yield": 75,

    "us dollar": 65,
    "usd": 55,
    "dollar": 45,
    "dxy": 70,

    "iran": 60,
    "israel": 60,
    "gaza": 50,
    "ukraine": 60,
    "russia": 50,
    "china": 35,
    "taiwan": 45,

    "war": 65,
    "missile": 70,
    "attack": 55,
    "strike": 55,
    "military": 45,
    "ceasefire": 55,
    "sanctions": 55,

    "opec": 55,
    "oil price": 50,
    "oil prices": 50,
    "crude oil": 50,
    "wti": 50,
    "brent": 50,
    "oil supply": 60,
    "oil production": 45,

    "safe haven": 65,
    "risk off": 65,
    "risk-off": 65,
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

    for keyword, points in HIGH_IMPACT.items():

        if keyword in text:
            score += points

    for keyword in NEGATIVE_WORDS:

        if keyword in text:
            score -= 100

    return score


def classify(score):

    if score >= 100:
        return "🔴 HIGH"

    if score >= 60:
        return "🟠 MEDIUM"

    return "🟢 LOW"


def get_category(title):

    text = title.lower()

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
            "military",
            "sanctions",
        ]
    ):
        return "🌍 GEOPOLITICAL"

    if any(
        word in text
        for word in [
            "fed",
            "federal reserve",
            "fomc",
            "interest rate",
            "cpi",
            "nfp",
            "nonfarm",
            "pce",
            "ppi",
            "treasury",
            "yield",
            "dxy",
            "dollar",
        ]
    ):
        return "🇺🇸 FED / USD"

    if any(
        word in text
        for word in [
            "oil",
            "crude",
            "wti",
            "brent",
            "opec",
        ]
    ):
        return "🛢️ OIL"

    if any(
        word in text
        for word in [
            "gold",
            "xauusd",
        ]
    ):
        return "🥇 GOLD"

    return "📰 MACRO"


# ============================================================
# GDELT
# ============================================================

async def get_news():

    queries = [
        "gold",
        "XAUUSD",
        '"Federal Reserve"',
        "FOMC",
        "CPI inflation",
        "NFP jobs",
        "Treasury yield",
        "DXY dollar",
        "Iran Israel",
        "Russia Ukraine",
        "OPEC oil",
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
                            article.get(
                                "title"
                            )
                            or ""
                        ).strip()

                        url = (
                            article.get(
                                "url"
                            )
                            or ""
                        ).strip()

                        domain = (
                            article.get(
                                "domain"
                            )
                            or ""
                        ).strip()

                        date = (
                            article.get(
                                "seendate"
                            )
                            or ""
                        ).strip()

                        if not title or not url:
                            continue

                        score = calculate_score(
                            title
                        )

                        # Minimum relevance
                        if score < 50:
                            continue

                        articles.append(
                            {
                                "title": title,
                                "url": url,
                                "domain": domain,
                                "date": date,
                                "score": score,
                                "impact": classify(
                                    score
                                ),
                                "category": get_category(
                                    title
                                ),
                            }
                        )

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

        else:

            if (
                article["score"]
                > unique[normalized]["score"]
            ):

                unique[normalized] = article

    articles = list(unique.values())

    # ========================================================
    # SORT BY RELEVANCE
    # ========================================================

    articles.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return articles[:10]


# ============================================================
# TELEGRAM
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🥇 XAUUSD Assistant aktif!\n\n"
        "/news — berita XAUUSD\n"
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
        "XAUUSD Filter: ACTIVE"
    )


async def news(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🔎 Menganalisis berita XAUUSD..."
    )

    try:

        articles = await get_news()

        if not articles:

            await update.message.reply_text(
                "❌ Tidak ada berita XAUUSD "
                "yang cukup relevan dalam 24 jam terakhir."
            )

            return

        message = (
            "🥇 XAUUSD NEWS\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )

        for i, article in enumerate(
            articles,
            1,
        ):

            message += (
                f"{article['impact']} "
                f"{article['category']}\n\n"

                f"📰 {article['title']}\n"

                f"🏢 {article['domain']}\n"

                f"🕐 {article['date']}\n"

                f"📊 Relevance: "
                f"{article['score']}\n"

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
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "status",
            status,
        )
    )

    app.add_handler(
        CommandHandler(
            "news",
            news,
        )
    )

    print(
        "🥇 XAUUSD Assistant sedang berjalan..."
    )

    app.run_polling()


if __name__ == "__main__":

    main()

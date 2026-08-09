import os
import logging
import aiohttp

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


async def get_news():

    queries = [
        "gold",
        "XAUUSD",
        "Federal Reserve gold",
        "gold USD",
        "gold oil",
        "gold Iran",
    ]

    articles = []

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:

        for query in queries:

            params = {
                "query": query,
                "mode": "artlist",
                "format": "json",
                "maxrecords": 10,
                "timespan": "24h",
                "sort": "DateDesc",
            }

            try:

                logging.info(f"GDELT query: {query}")

                async with session.get(
                    GDELT_URL,
                    params=params
                ) as response:

                    logging.info(
                        f"GDELT status: {response.status}"
                    )

                    if response.status != 200:
                        logging.warning(
                            f"GDELT error {response.status}"
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

                        articles.append({
                            "title": title,
                            "url": url,
                            "domain": domain,
                            "date": date,
                        })

            except Exception:

                logging.exception(
                    f"Error query: {query}"
                )

    # Remove duplicate articles
    unique = {}

    for article in articles:

        key = article["url"]

        if key not in unique:
            unique[key] = article

    return list(unique.values())[:15]


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🥇 XAUUSD Assistant aktif!\n\n"
        "Gunakan:\n"
        "/news — berita Gold\n"
        "/status — status bot"
    )


async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🟢 BOT ONLINE\n"
        "Railway: OK\n"
        "News Engine: OK"
    )


async def news(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🔎 Mengambil berita XAUUSD terbaru..."
    )

    try:

        articles = await get_news()

        logging.info(
            f"Articles found: {len(articles)}"
        )

        if not articles:

            await update.message.reply_text(
                "❌ Tidak ada berita ditemukan.\n\n"
                "Cek Railway Logs untuk melihat "
                "respon GDELT."
            )

            return

        message = (
            "🥇 XAUUSD NEWS\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )

        for i, article in enumerate(
            articles[:10],
            1
        ):

            message += (
                f"📰 {i}. "
                f"{article['title']}\n\n"
                f"🏢 {article['domain']}\n"
                f"🕐 {article['date']}\n"
                f"🔗 {article['url']}\n\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
            )

        await update.message.reply_text(
            message,
            disable_web_page_preview=True
        )

    except Exception as e:

        logging.exception(
            "NEWS ERROR"
        )

        await update.message.reply_text(
            "❌ News Engine Error\n\n"
            f"{str(e)[:500]}"
        )


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
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "status",
            status
        )
    )

    app.add_handler(
        CommandHandler(
            "news",
            news
        )
    )

    print(
        "🥇 XAUUSD Assistant sedang berjalan..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()

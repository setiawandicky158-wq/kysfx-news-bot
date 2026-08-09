import os
import logging
import aiohttp

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")


GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


async def get_news():
    query = (
        '(gold OR XAUUSD OR "gold price" OR '
        'Federal Reserve OR Fed OR CPI OR NFP OR PCE OR '
        'USD OR dollar OR Treasury OR yields OR '
        'oil OR crude OR OPEC OR Iran OR Israel OR Ukraine)'
    )

    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": 10,
        "timespan": "6h",
        "sort": "datedesc",
    }

    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(GDELT_URL, params=params) as response:

            if response.status != 200:
                return []

            data = await response.json(content_type=None)

    articles = []

    for article in data.get("articles", []):

        title = article.get("title", "").strip()
        url = article.get("url", "").strip()
        domain = article.get("domain", "").strip()
        date = article.get("seendate", "").strip()

        if not title or not url:
            continue

        articles.append({
            "title": title,
            "url": url,
            "domain": domain,
            "date": date,
        })

    return articles


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🥇 XAUUSD Assistant aktif!\n\n"
        "Bot berhasil terhubung ke Telegram.\n\n"
        "Gunakan:\n"
        "/news — berita yang memengaruhi XAUUSD\n"
        "/status — status bot"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🟢 BOT ONLINE\n"
        "Railway connection: OK\n"
        "News engine: READY"
    )


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🔎 Mencari berita XAUUSD terbaru..."
    )

    try:
        articles = await get_news()

        if not articles:
            await update.message.reply_text(
                "❌ Tidak menemukan berita terbaru."
            )
            return

        message = "🥇 XAUUSD NEWS\n"
        message += "━━━━━━━━━━━━━━━━━━\n\n"

        for i, article in enumerate(articles[:8], 1):

            message += (
                f"📰 {i}. {article['title']}\n"
                f"🏢 {article['domain']}\n"
                f"🔗 {article['url']}\n\n"
            )

        await update.message.reply_text(
            message,
            disable_web_page_preview=True
        )

    except Exception as e:

        logging.exception("News error")

        await update.message.reply_text(
            "❌ Gagal mengambil berita.\n"
            f"Error: {str(e)[:300]}"
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
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("status", status)
    )

    app.add_handler(
        CommandHandler("news", news)
    )

    print("🥇 XAUUSD Assistant sedang berjalan...")

    app.run_polling()


if __name__ == "__main__":
    main()

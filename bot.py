import os
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🥇 XAUUSD Assistant aktif!\n\n"
        "Bot berhasil terhubung ke Telegram.\n"
        "Fitur news akan kita tambahkan berikutnya."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟢 BOT ONLINE\n"
        "Railway connection: OK"
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN belum diatur di Railway.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))

    print("Bot Telegram sedang berjalan...")

    app.run_polling()


if __name__ == "__main__":
    main()

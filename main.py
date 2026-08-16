import logging
import sys
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import (
    BOT_TOKEN,
    BOT_NAME,
    WITA,
    validate_config,
)

from state import state

from news import (
    get_news,
    format_news_message,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
)

logger = logging.getLogger("KYSFX")


# ============================================================
# /START
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    now = datetime.now(WITA)

    message = (
        "🤖 <b>KYSFX XAUUSD NEWS BOT</b>\n\n"
        "Bot berhasil aktif. 🟢\n\n"
        f"🕐 WITA: "
        f"<code>{now:%d-%m-%Y %H:%M:%S}</code>\n\n"
        "Gunakan /help untuk melihat command."
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
    )

    logger.info(
        "[TELEGRAM] /start from user=%s",
        update.effective_user.id
        if update.effective_user
        else "unknown",
    )


# ============================================================
# /HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = (
        "📚 <b>KYSFX BOT COMMAND</b>\n\n"

        "🤖 <b>GENERAL</b>\n"
        "/start — Memulai bot\n"
        "/status — Status bot\n"
        "/state — Database & memory bot\n"
        "/news — Scan berita XAUUSD\n"
        "/help — Daftar command\n\n"

        "🚧 <b>ENGINE STATUS</b>\n"
        "🚨 News Engine: 🟢 ACTIVE\n"
        "📅 Calendar Engine: ⏳ BUILDING\n"
        "🧠 Market Engine: ⏳ BUILDING\n"
        "🌏 Session Engine: ⏳ BUILDING\n"
        "📊 Market Brief: ⏳ BUILDING"
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
    )


# ============================================================
# /STATUS
# ============================================================

async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    now = datetime.now(WITA)

    try:

        total_records = state.total()
        database_status = "🟢 OK"

    except Exception as exc:

        logger.error(
            "[STATE] Database error: %s",
            exc,
            exc_info=True,
        )

        total_records = 0
        database_status = "🔴 ERROR"

    message = (
        "🟢 <b>BOT STATUS</b>\n\n"

        f"Bot: <b>{BOT_NAME}</b>\n"
        "Telegram: 🟢 CONNECTED\n"
        "Polling: 🟢 ACTIVE\n"
        f"Database: {database_status}\n"
        f"Records: <b>{total_records}</b>\n\n"

        f"🕐 WITA:\n"
        f"<code>{now:%d-%m-%Y %H:%M:%S}</code>\n\n"

        "🚨 News Engine: 🟢 ACTIVE\n"
        "📅 Calendar Engine: ⏳ BUILDING\n"
        "🧠 Market Engine: ⏳ BUILDING\n"
        "🌏 Session Engine: ⏳ BUILDING\n"
        "📊 Market Brief: ⏳ BUILDING"
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
    )


# ============================================================
# /STATE
# ============================================================

async def state_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    try:

        stats = state.stats()
        total = state.total()

        lines = [
            "💾 <b>KYSFX BOT STATE</b>",
            "",
            "Database: 🟢 SQLite",
            f"Total records: <b>{total}</b>",
            "",
        ]

        if stats:

            lines.append(
                "📊 <b>RECORDS BY TYPE</b>"
            )

            for item_type, count in stats:

                lines.append(
                    f"• {item_type}: "
                    f"<b>{count}</b>"
                )

        else:

            lines.append(
                "Belum ada data tersimpan."
            )

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="HTML",
        )

        logger.info(
            "[STATE] /state requested | total=%s",
            total,
        )

    except Exception as exc:

        logger.error(
            "[STATE] Failed to read state: %s",
            exc,
            exc_info=True,
        )

        await update.message.reply_text(
            "🔴 <b>STATE ERROR</b>\n\n"
            "Database tidak dapat dibaca.\n"
            "Periksa log Railway.",
            parse_mode="HTML",
        )


# ============================================================
# /NEWS
# ============================================================

async def news_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.info(
        "[NEWS] Manual /news requested"
    )

    await update.message.reply_text(
        "🔎 <b>SCANNING NEWS...</b>\n\n"
        "Sedang mencari berita relevan "
        "untuk Gold, XAUUSD, USD, Yield, "
        "dan Oil.\n\n"
        "⏳ Mohon tunggu...",
        parse_mode="HTML",
    )

    try:

        results = get_news(
            limit=10
        )

        logger.info(
            "[NEWS] Scan completed | results=%s",
            len(results),
        )

        if not results:

            await update.message.reply_text(
                "📰 <b>NEWS SCAN</b>\n\n"
                "Tidak ditemukan berita relevan "
                "untuk XAUUSD/USD/Gold/Yield/Oil "
                "dalam periode scan.",
                parse_mode="HTML",
            )

            return

        await update.message.reply_text(
            "📰 <b>NEWS ENGINE RESULT</b>\n\n"
            f"Ditemukan "
            f"<b>{len(results)}</b> berita relevan.",
            parse_mode="HTML",
        )

        # Kirim maksimal 5 berita pada manual scan
        for item in results[:5]:

            try:

                message = format_news_message(
                    item,
                    translate=False,
                )

                await update.message.reply_text(
                    message,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )

            except Exception as exc:

                logger.warning(
                    "[NEWS] Failed formatting item: %s",
                    exc,
                )

        logger.info(
            "[NEWS] /news completed successfully"
        )

    except Exception as exc:

        logger.error(
            "[NEWS] /news failed: %s",
            exc,
            exc_info=True,
        )

        await update.message.reply_text(
            "🔴 <b>NEWS ENGINE ERROR</b>\n\n"
            "News Engine mengalami error.\n\n"
            f"<code>{str(exc)[:1500]}</code>",
            parse_mode="HTML",
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    error = context.error

    logger.error(
        "[TELEGRAM ERROR] %s",
        error,
        exc_info=error,
    )


# ============================================================
# DATABASE TEST
# ============================================================

def test_database():

    try:

        total = state.total()

        logger.info(
            "[STATE] SQLite initialized successfully"
        )

        logger.info(
            "[STATE] Existing records: %s",
            total,
        )

        return True

    except Exception as exc:

        logger.error(
            "[STATE] SQLite initialization failed: %s",
            exc,
            exc_info=True,
        )

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "=================================================="
    )

    logger.info(
        "Starting %s",
        BOT_NAME,
    )

    logger.info(
        "=================================================="
    )

    # --------------------------------------------------------
    # CONFIGURATION
    # --------------------------------------------------------

    try:

        validate_config()

    except Exception as exc:

        logger.critical(
            "[CONFIG] Configuration error: %s",
            exc,
        )

        raise

    logger.info(
        "[CONFIG] Configuration OK"
    )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    if not test_database():

        raise RuntimeError(
            "SQLite database initialization failed"
        )

    # --------------------------------------------------------
    # TELEGRAM APPLICATION
    # --------------------------------------------------------

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "status",
            status_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "state",
            state_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "news",
            news_command,
        )
    )

    # --------------------------------------------------------
    # ERROR HANDLER
    # --------------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    # --------------------------------------------------------
    # POLLING
    # --------------------------------------------------------

    logger.info(
        "[TELEGRAM] Polling starting..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()

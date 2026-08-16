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
# COMMAND /START
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    now = datetime.now(WITA)

    message = (
        "🤖 <b>KYSFX XAUUSD NEWS BOT</b>\n\n"
        "Bot berhasil aktif.\n\n"
        f"🕐 WITA: "
        f"<code>{now:%d-%m-%Y %H:%M:%S}</code>\n\n"
        "Gunakan /help untuk melihat command."
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
    )


# ============================================================
# COMMAND /HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = (
        "📚 <b>COMMAND BOT</b>\n\n"
        "/start — Memulai bot\n"
        "/status — Status bot\n"
        "/help — Daftar command\n\n"
        "🚧 News, Calendar, Market Brief, "
        "dan Session Engine sedang dibangun."
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
    )


# ============================================================
# COMMAND /STATUS
# ============================================================

async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    now = datetime.now(WITA)

    message = (
        "🟢 <b>BOT STATUS</b>\n\n"
        f"Bot: <b>{BOT_NAME}</b>\n"
        "Status: 🟢 ONLINE\n"
        "Telegram: 🟢 CONNECTED\n"
        f"WITA: <code>{now:%d-%m-%Y %H:%M:%S}</code>\n\n"
        "News Engine: ⏳ BUILDING\n"
        "Calendar Engine: ⏳ BUILDING\n"
        "Market Engine: ⏳ BUILDING\n"
        "Session Engine: ⏳ BUILDING"
    )

    await update.message.reply_text(
        message,
        parse_mode="HTML",
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Telegram error: %s",
        context.error,
        exc_info=context.error,
    )


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
    # CONFIG VALIDATION
    # --------------------------------------------------------

    try:
        validate_config()

    except Exception as exc:

        logger.critical(
            "Configuration error: %s",
            exc,
        )

        raise

    logger.info(
        "Configuration OK"
    )

    # --------------------------------------------------------
    # APPLICATION
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

    application.add_error_handler(
        error_handler
    )

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    logger.info(
        "Telegram polling starting..."
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

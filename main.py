import os
import time
import logging
import requests

from news import get_news, format_news


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

CHECK_INTERVAL = int(
    os.getenv("CHECK_INTERVAL", "60")
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# VALIDATE CONFIG
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN belum diset di Railway Variables."
    )

if not CHAT_ID:
    raise RuntimeError(
        "CHAT_ID belum diset di Railway Variables."
    )


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):

            logger.error(
                "Telegram error: %s",
                data
            )

            return False

        return True

    except requests.exceptions.RequestException as e:

        logger.error(
            "Telegram request error: %s",
            e
        )

        return False

    except Exception as e:

        logger.error(
            "Telegram unexpected error: %s",
            e
        )

        return False


# ============================================================
# NEWS ID
# ============================================================

def get_news_id(news):

    link = news.get(
        "link",
        ""
    ).strip()

    if link:
        return link

    title = news.get(
        "title",
        ""
    ).strip().lower()

    return title


# ============================================================
# MAIN LOOP
# ============================================================

def run():

    logger.info(
        "======================================"
    )

    logger.info(
        "XAUUSD + OIL NEWS ASSISTANT STARTING"
    )

    logger.info(
        "Check interval: %s seconds",
        CHECK_INTERVAL
    )

    logger.info(
        "======================================"
    )

    sent_news = set()

    while True:

        try:

            logger.info(
                "Checking breaking news..."
            )

            news_list = get_news(
                limit=15
            )

            logger.info(
                "Relevant news found: %s",
                len(news_list)
            )

            # ====================================================
            # SEND ONLY NEW NEWS
            # ====================================================

            for news in reversed(news_list):

                news_id = get_news_id(
                    news
                )

                if not news_id:
                    continue

                # Jangan kirim berita yang sudah pernah dikirim
                if news_id in sent_news:
                    continue

                try:

                    message = format_news(
                        news
                    )

                except Exception as e:

                    logger.error(
                        "Format news error: %s",
                        e
                    )

                    continue

                success = send_telegram(
                    message
                )

                if success:

                    sent_news.add(
                        news_id
                    )

                    logger.info(
                        "News sent: %s",
                        news.get("title", "")
                    )

                else:

                    logger.error(
                        "Failed to send news: %s",
                        news.get("title", "")
                    )

            # ====================================================
            # MEMORY LIMIT
            # ====================================================

            if len(sent_news) > 1000:

                sent_news = set(
                    list(sent_news)[-500:]
                )

        except Exception as e:

            logger.exception(
                "Main loop error: %s",
                e
            )

        # ========================================================
        # WAIT
        # ========================================================

        time.sleep(
            CHECK_INTERVAL
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run()

import os
import time
import logging
import requests

from news import get_news, format_news
from calendar import get_calendar_events, format_calendar_event


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

CHECK_INTERVAL = int(
    os.getenv("CHECK_INTERVAL", "60")
)

EVENT_ALERT_HOURS = float(
    os.getenv("EVENT_ALERT_HOURS", "2")
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

        logger.exception(
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

    return (
        news.get(
            "title",
            ""
        )
        .strip()
        .lower()
    )


# ============================================================
# EVENT ID
# ============================================================

def get_event_id(event):

    return "|".join(
        [
            event.get("event", ""),
            event.get("currency", ""),
            str(
                event.get("datetime", "")
            ),
        ]
    )


# ============================================================
# CHECK NEWS
# ============================================================

def check_news(sent_news):

    logger.info(
        "[NEWS] Checking breaking news..."
    )

    try:

        news_list = get_news(
            limit=15
        )

        logger.info(
            "[NEWS] Relevant news found: %s",
            len(news_list)
        )

        for news in reversed(news_list):

            news_id = get_news_id(
                news
            )

            if not news_id:
                continue

            if news_id in sent_news:
                continue

            try:

                message = format_news(
                    news
                )

            except Exception as e:

                logger.error(
                    "[NEWS] Format error: %s",
                    e
                )

                continue

            if send_telegram(message):

                sent_news.add(
                    news_id
                )

                logger.info(
                    "[NEWS] News sent: %s",
                    news.get("title", "")
                )

            else:

                logger.error(
                    "[NEWS] Failed to send: %s",
                    news.get("title", "")
                )

    except Exception as e:

        logger.exception(
            "[NEWS] Check error: %s",
            e
        )


# ============================================================
# CHECK GOLD EVENTS
# ============================================================

def check_calendar(sent_events):

    logger.info(
        "[CALENDAR] Checking Gold events..."
    )

    try:

        events = get_calendar_events(
            hours_ahead=48
        )

        logger.info(
            "[CALENDAR] Gold events found: %s",
            len(events)
        )

        for event in events:

            event_datetime = event.get(
                "datetime"
            )

            if not event_datetime:
                continue

            # ------------------------------------------------
            # CALCULATE TIME TO EVENT
            # ------------------------------------------------

            from datetime import datetime
            from zoneinfo import ZoneInfo

            now = datetime.now(
                ZoneInfo("Asia/Makassar")
            )

            seconds_to_event = (
                event_datetime - now
            ).total_seconds()

            hours_to_event = (
                seconds_to_event / 3600
            )

            # ------------------------------------------------
            # ONLY ALERT WITHIN 2 HOURS
            # ------------------------------------------------

            if hours_to_event < 0:
                continue

            if hours_to_event > EVENT_ALERT_HOURS:
                continue

            event_id = get_event_id(
                event
            )

            if not event_id:
                continue

            if event_id in sent_events:
                continue

            # ------------------------------------------------
            # FORMAT EVENT
            # ------------------------------------------------

            try:

                message = format_calendar_event(
                    event,
                    result=False
                )

            except Exception as e:

                logger.error(
                    "[CALENDAR] Format error: %s",
                    e
                )

                continue

            # ------------------------------------------------
            # SEND TELEGRAM
            # ------------------------------------------------

            if send_telegram(message):

                sent_events.add(
                    event_id
                )

                logger.info(
                    "[CALENDAR] Event alert sent: %s",
                    event.get("event", "")
                )

            else:

                logger.error(
                    "[CALENDAR] Failed to send: %s",
                    event.get("event", "")
                )

    except Exception as e:

        # Calendar error tidak boleh
        # menghentikan news bot.

        logger.exception(
            "[CALENDAR] Check error: %s",
            e
        )


# ============================================================
# MEMORY CLEANUP
# ============================================================

def cleanup_memory(
    sent_news,
    sent_events
):

    if len(sent_news) > 1000:

        old_news = list(
            sent_news
        )

        sent_news.clear()

        sent_news.update(
            old_news[-500:]
        )

    if len(sent_events) > 500:

        old_events = list(
            sent_events
        )

        sent_events.clear()

        sent_events.update(
            old_events[-250:]
        )


# ============================================================
# MAIN
# ============================================================

def run():

    logger.info(
        "======================================"
    )

    logger.info(
        "XAUUSD + GOLD NEWS ASSISTANT STARTING"
    )

    logger.info(
        "Check interval: %s seconds",
        CHECK_INTERVAL
    )

    logger.info(
        "Event alert window: %s hours",
        EVENT_ALERT_HOURS
    )

    logger.info(
        "======================================"
    )

    sent_news = set()
    sent_events = set()

    while True:

        try:

            # =================================================
            # BREAKING NEWS
            # =================================================

            check_news(
                sent_news
            )

            # =================================================
            # GOLD ECONOMIC EVENTS
            # =================================================

            check_calendar(
                sent_events
            )

            # =================================================
            # MEMORY
            # =================================================

            cleanup_memory(
                sent_news,
                sent_events
            )

        except Exception as e:

            logger.exception(
                "[MAIN] Main loop error: %s",
                e
            )

        logger.info(
            "Next check in %s seconds...",
            CHECK_INTERVAL
        )

        time.sleep(
            CHECK_INTERVAL
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run()

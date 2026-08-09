import os
import time
import logging
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from news import get_news, format_news
from ff_calendar import (
    get_calendar_events,
    format_calendar_event,
)

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

WITA = ZoneInfo("Asia/Makassar")

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# ============================================================
# VALIDATE
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
                "[TELEGRAM] API error: %s",
                data
            )
            return False

        return True

    except requests.exceptions.RequestException as e:
        logger.error(
            "[TELEGRAM] Request error: %s",
            e
        )
        return False

    except Exception as e:
        logger.exception(
            "[TELEGRAM] Unexpected error: %s",
            e
        )
        return False


# ============================================================
# NEWS ID
# ============================================================

def get_news_id(news):
    link = (
        news.get("link", "")
        .strip()
    )

    if link:
        return link

    return (
        news.get("title", "")
        .strip()
        .lower()
    )


# ============================================================
# EVENT ID
# ============================================================

def get_event_id(event):
    event_name = (
        event.get("event", "")
        .strip()
        .lower()
    )

    currency = (
        event.get("currency", "")
        .strip()
        .upper()
    )

    event_datetime = event.get(
        "datetime"
    )

    if event_datetime:
        event_time = event_datetime.isoformat()
    else:
        event_time = (
            f"{event.get('date', '')}|"
            f"{event.get('time', '')}"
        )

    return (
        f"{event_name}|"
        f"{currency}|"
        f"{event_time}"
    )


# ============================================================
# NEWS CHECK
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

    except Exception as e:
        logger.exception(
            "[NEWS] Check error: %s",
            e
        )


# ============================================================
# CALENDAR CHECK
# ============================================================

def check_calendar(
    alerted_events,
    result_events
):
    logger.info(
        "[CALENDAR] Checking Gold events..."
    )

    try:

        events = get_calendar_events(
            hours_ahead=48
        )

        logger.info(
            "[CALENDAR] Total upcoming Gold events: %s",
            len(events)
        )

        now = datetime.now(WITA)

        for event in events:

            event_datetime = event.get(
                "datetime"
            )

            if not event_datetime:
                continue

            event_id = get_event_id(
                event
            )

            seconds_until = (
                event_datetime - now
            ).total_seconds()

            hours_until = (
                seconds_until / 3600
            )

            # =================================================
            # H-2 HOURS ALERT
            # =================================================

            if (
                0
                <= hours_until
                <= EVENT_ALERT_HOURS
            ):

                if event_id in alerted_events:
                    continue

                # Update countdown tepat saat dikirim
                event["countdown"] = (
                    f"{max(0, int(seconds_until)) // 3600:02d}:"
                    f"{(max(0, int(seconds_until)) % 3600) // 60:02d}:"
                    f"{max(0, int(seconds_until)) % 60:02d}"
                )

                message = format_calendar_event(
                    event,
                    result=False
                )

                if send_telegram(message):

                    alerted_events.add(
                        event_id
                    )

                    logger.info(
                        "[CALENDAR] H-2 alert sent: %s | %s",
                        event.get("event"),
                        event_datetime
                    )

            # =================================================
            # EVENT RESULT
            # =================================================

            actual = (
                event.get("actual", "")
                or ""
            ).strip()

            if actual:

                result_id = (
                    f"RESULT|{event_id}"
                )

                if result_id not in result_events:

                    message = format_calendar_event(
                        event,
                        result=True
                    )

                    if send_telegram(message):

                        result_events.add(
                            result_id
                        )

                        logger.info(
                            "[CALENDAR] Result sent: %s",
                            event.get("event")
                        )

    except Exception as e:

        logger.exception(
            "[CALENDAR] Check error: %s",
            e
        )


# ============================================================
# MEMORY CLEANUP
# ============================================================

def cleanup_memory(
    sent_news,
    alerted_events,
    result_events
):

    if len(sent_news) > 1000:

        old_items = list(
            sent_news
        )[-500:]

        sent_news.clear()

        sent_news.update(
            old_items
        )

    if len(alerted_events) > 1000:

        old_items = list(
            alerted_events
        )[-500:]

        alerted_events.clear()

        alerted_events.update(
            old_items
        )

    if len(result_events) > 1000:

        old_items = list(
            result_events
        )[-500:]

        result_events.clear()

        result_events.update(
            old_items
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
        "Event alert window: %.1f hours",
        EVENT_ALERT_HOURS
    )

    logger.info(
        "Timezone: WITA (Asia/Makassar)"
    )

    logger.info(
        "======================================"
    )

    sent_news = set()

    alerted_events = set()

    result_events = set()

    while True:

        try:

            # =================================================
            # NEWS
            # =================================================

            check_news(
                sent_news
            )

            # =================================================
            # GOLD CALENDAR
            # =================================================

            check_calendar(
                alerted_events,
                result_events
            )

            # =================================================
            # MEMORY
            # =================================================

            cleanup_memory(
                sent_news,
                alerted_events,
                result_events
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

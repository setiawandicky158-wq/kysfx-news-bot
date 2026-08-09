import os
import time
import logging
import requests

from datetime import datetime
from zoneinfo import ZoneInfo

from news import (
    get_news,
    format_news
)

from ff_calendar import (
    get_calendar_events,
    get_event_id,
    format_calendar_event
)


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN"
)

CHAT_ID = os.getenv(
    "CHAT_ID"
)

CHECK_INTERVAL = int(
    os.getenv(
        "CHECK_INTERVAL",
        "60"
    )
)

# Berapa jam sebelum event alert dikirim
EVENT_ALERT_HOURS = float(
    os.getenv(
        "EVENT_ALERT_HOURS",
        "2"
    )
)

# Berapa menit setelah event untuk menunggu Actual
EVENT_RESULT_MINUTES = int(
    os.getenv(
        "EVENT_RESULT_MINUTES",
        "10"
    )
)

WITA = ZoneInfo(
    "Asia/Makassar"
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    )
)

logger = logging.getLogger(
    __name__
)


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
        "https://api.telegram.org/"
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
# EVENT DATETIME
# ============================================================

def get_event_datetime(event):

    event_datetime = event.get(
        "datetime"
    )

    if not event_datetime:
        return None

    if event_datetime.tzinfo is None:

        event_datetime = event_datetime.replace(
            tzinfo=WITA
        )

    return event_datetime


# ============================================================
# CHECK PRE-EVENT
# ============================================================

def is_pre_event(event):

    event_datetime = get_event_datetime(
        event
    )

    if not event_datetime:
        return False

    now = datetime.now(
        WITA
    )

    seconds = (
        event_datetime - now
    ).total_seconds()

    return (
        seconds > 0
        and seconds <= (
            EVENT_ALERT_HOURS * 3600
        )
    )


# ============================================================
# CHECK POST-EVENT
# ============================================================

def is_result_event(event):

    event_datetime = get_event_datetime(
        event
    )

    if not event_datetime:
        return False

    now = datetime.now(
        WITA
    )

    seconds = (
        now - event_datetime
    ).total_seconds()

    return (
        seconds >= 0
        and seconds <= (
            EVENT_RESULT_MINUTES * 60
        )
    )


# ============================================================
# ACTUAL AVAILABLE
# ============================================================

def has_actual(event):

    actual = event.get(
        "actual",
        ""
    )

    if actual is None:
        return False

    actual = str(
        actual
    ).strip()

    if not actual:
        return False

    if actual in (
        "-",
        "—",
        "–"
    ):
        return False

    return True


# ============================================================
# EVENT ID
# ============================================================

def event_key(event):

    try:

        return get_event_id(
            event
        )

    except Exception:

        return "|".join(
            [
                str(
                    event.get(
                        "event",
                        ""
                    )
                ),
                str(
                    event.get(
                        "currency",
                        ""
                    )
                ),
                str(
                    event.get(
                        "datetime",
                        ""
                    )
                )
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

    except Exception as e:

        logger.exception(
            "[NEWS] Get news error: %s",
            e
        )

        return

    logger.info(
        "[NEWS] Relevant news found: %s",
        len(news_list)
    )

    for news in reversed(
        news_list
    ):

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

        success = send_telegram(
            message
        )

        if success:

            sent_news.add(
                news_id
            )

            logger.info(
                "[NEWS] News sent: %s",
                news.get(
                    "title",
                    ""
                )
            )


# ============================================================
# CHECK FOREX FACTORY GOLD EVENTS
# ============================================================

def check_calendar(
    sent_event_alerts,
    sent_event_results
):

    logger.info(
        "[CALENDAR] Checking Gold events..."
    )

    try:

        events = get_calendar_events(
            hours_ahead=48,
            minutes_after=EVENT_RESULT_MINUTES
        )

    except TypeError:

        # Kompatibel jika ff_calendar.py
        # belum menerima minutes_after

        try:

            events = get_calendar_events(
                hours_ahead=48
            )

        except Exception as e:

            logger.exception(
                "[CALENDAR] Get events error: %s",
                e
            )

            return

    except Exception as e:

        logger.exception(
            "[CALENDAR] Get events error: %s",
            e
        )

        return

    logger.info(
        "[CALENDAR] Gold events found: %s",
        len(events)
    )

    for event in events:

        try:

            key = event_key(
                event
            )

            if not key:
                continue

            event_name = event.get(
                "event",
                ""
            )

            # ==================================================
            # PRE-EVENT
            # ==================================================

            if is_pre_event(
                event
            ):

                if key in sent_event_alerts:
                    continue

                message = format_calendar_event(
                    event,
                    result=False
                )

                if send_telegram(
                    message
                ):

                    sent_event_alerts.add(
                        key
                    )

                    logger.info(
                        "[CALENDAR] "
                        "Pre-event sent: %s",
                        event_name
                    )

                continue

            # ==================================================
            # POST-EVENT RESULT
            # ==================================================

            if is_result_event(
                event
            ):

                if not has_actual(
                    event
                ):

                    logger.info(
                        "[CALENDAR] "
                        "Actual not available yet: %s",
                        event_name
                    )

                    continue

                if key in sent_event_results:
                    continue

                message = format_calendar_event(
                    event,
                    result=True
                )

                if send_telegram(
                    message
                ):

                    sent_event_results.add(
                        key
                    )

                    logger.info(
                        "[CALENDAR] "
                        "RESULT sent: %s",
                        event_name
                    )

        except Exception as e:

            logger.exception(
                "[CALENDAR] "
                "Event processing error: %s",
                e
            )


# ============================================================
# MEMORY CLEANUP
# ============================================================

def cleanup_memory(memory):

    if len(memory) <= 1000:
        return memory

    return set(
        list(memory)[-500:]
    )


# ============================================================
# MAIN LOOP
# ============================================================

def run():

    logger.info(
        "======================================"
    )

    logger.info(
        "XAUUSD NEWS + GOLD CALENDAR ASSISTANT"
    )

    logger.info(
        "Check interval: %s seconds",
        CHECK_INTERVAL
    )

    logger.info(
        "Event alert: %s hours before",
        EVENT_ALERT_HOURS
    )

    logger.info(
        "Event result window: %s minutes",
        EVENT_RESULT_MINUTES
    )

    logger.info(
        "Timezone: WITA"
    )

    logger.info(
        "======================================"
    )

    sent_news = set()

    sent_event_alerts = set()

    sent_event_results = set()

    while True:

        try:

            logger.info(
                "======================================"
            )

            logger.info(
                "Checking market data..."
            )

            # ==================================================
            # INVESTINGLIVE NEWS
            # ==================================================

            check_news(
                sent_news
            )

            # ==================================================
            # FOREX FACTORY GOLD EVENTS
            # ==================================================

            check_calendar(
                sent_event_alerts,
                sent_event_results
            )

            # ==================================================
            # MEMORY CLEANUP
            # ==================================================

            sent_news = cleanup_memory(
                sent_news
            )

            sent_event_alerts = cleanup_memory(
                sent_event_alerts
            )

            sent_event_results = cleanup_memory(
                sent_event_results
            )

        except Exception as e:

            logger.exception(
                "Main loop error: %s",
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

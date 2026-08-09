import os
import time
import logging
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from news import get_news, format_news
from ff_calendar import (
    get_calendar_events,
    get_event_id,
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

# 2 JAM SEBELUM EVENT
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
# EVENT IS IN ALERT WINDOW
# ============================================================

def is_event_in_alert_window(event):

    event_datetime = event.get(
        "datetime"
    )

    if not event_datetime:
        return False

    now = datetime.now(WITA)

    # Past event
    if event_datetime <= now:
        return False

    # Event harus berada dalam 2 jam ke depan
    alert_limit = (
        now
        + timedelta(
            hours=EVENT_ALERT_HOURS
        )
    )

    if event_datetime <= alert_limit:
        return True

    return False


# ============================================================
# EVENT COUNTDOWN
# ============================================================

def calculate_event_countdown(event):

    event_datetime = event.get(
        "datetime"
    )

    if not event_datetime:
        return "-"

    now = datetime.now(WITA)

    seconds = int(
        (
            event_datetime - now
        ).total_seconds()
    )

    if seconds <= 0:
        return "EVENT SUDAH BERLANGSUNG"

    hours = seconds // 3600

    minutes = (
        seconds % 3600
    ) // 60

    secs = seconds % 60

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


# ============================================================
# PREPARE CALENDAR EVENT
# ============================================================

def prepare_calendar_event(event):

    event = dict(event)

    event["countdown"] = (
        calculate_event_countdown(
            event
        )
    )

    return event


# ============================================================
# CHECK GOLD EVENTS
# ============================================================

def check_gold_events(sent_events):

    logger.info(
        "[CALENDAR] Checking Gold economic events..."
    )

    try:

        # Ambil event 48 jam ke depan
        events = get_calendar_events(
            hours_ahead=48
        )

    except Exception as e:

        logger.exception(
            "[CALENDAR] Failed to get events: %s",
            e
        )

        return

    logger.info(
        "[CALENDAR] Gold events found: %s",
        len(events)
    )

    for event in events:

        try:

            # ------------------------------------------------
            # FILTER 2 JAM
            # ------------------------------------------------

            if not is_event_in_alert_window(
                event
            ):

                continue

            event = prepare_calendar_event(
                event
            )

            event_id = get_event_id(
                event
            )

            if not event_id:
                continue

            # ------------------------------------------------
            # JANGAN KIRIM ULANG
            # ------------------------------------------------

            if event_id in sent_events:

                logger.info(
                    "[CALENDAR] Already sent: %s",
                    event.get(
                        "event",
                        ""
                    )
                )

                continue

            # ------------------------------------------------
            # LOG
            # ------------------------------------------------

            logger.info(
                "[CALENDAR] Alert window: %s | %s",
                event.get(
                    "event",
                    ""
                ),
                event.get(
                    "countdown",
                    ""
                )
            )

            # ------------------------------------------------
            # FORMAT
            # ------------------------------------------------

            message = format_calendar_event(
                event,
                result=False
            )

            # ------------------------------------------------
            # SEND TELEGRAM
            # ------------------------------------------------

            success = send_telegram(
                message
            )

            if success:

                sent_events.add(
                    event_id
                )

                logger.info(
                    "[CALENDAR] Event sent: %s",
                    event.get(
                        "event",
                        ""
                    )
                )

            else:

                logger.error(
                    "[CALENDAR] Failed sending: %s",
                    event.get(
                        "event",
                        ""
                    )
                )

        except Exception as e:

            logger.exception(
                "[CALENDAR] Event processing error: %s",
                e
            )


# ============================================================
# CLEAN OLD EVENT MEMORY
# ============================================================

def cleanup_event_memory(
    sent_events
):

    if len(sent_events) <= 1000:
        return sent_events

    logger.info(
        "[CALENDAR] Cleaning event memory..."
    )

    return set(
        list(sent_events)[-500:]
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

    except Exception as e:

        logger.exception(
            "[NEWS] Failed to get news: %s",
            e
        )

        return

    # oldest -> newest
    for news in reversed(
        news_list
    ):

        news_id = get_news_id(
            news
        )

        if not news_id:
            continue

        # Jangan kirim berita yang sama
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

        else:

            logger.error(
                "[NEWS] Failed to send: %s",
                news.get(
                    "title",
                    ""
                )
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
        "Event alert window: %s hours",
        EVENT_ALERT_HOURS
    )

    logger.info(
        "Timezone: WITA"
    )

    logger.info(
        "======================================"
    )

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    sent_news = set()

    sent_events = set()

    # --------------------------------------------------------
    # LOOP
    # --------------------------------------------------------

    while True:

        try:

            logger.info(
                "======================================"
            )

            logger.info(
                "Checking market data..."
            )

            # =================================================
            # 1. INVESTINGLIVE NEWS
            # =================================================

            check_news(
                sent_news
            )

            # =================================================
            # 2. FOREX FACTORY GOLD EVENTS
            # =================================================

            check_gold_events(
                sent_events
            )

            # =================================================
            # 3. MEMORY CLEANUP
            # =================================================

            sent_news = (
                sent_news
                if len(sent_news) <= 1000
                else set(
                    list(sent_news)[-500:]
                )
            )

            sent_events = (
                cleanup_event_memory(
                    sent_events
                )
            )

        except Exception as e:

            logger.exception(
                "Main loop error: %s",
                e
            )

        # =====================================================
        # WAIT
        # =====================================================

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

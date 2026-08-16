import os
from zoneinfo import ZoneInfo


# ============================================================
# TIMEZONE
# ============================================================

TIMEZONE_NAME = os.getenv(
    "TIMEZONE",
    "Asia/Makassar"
)

WITA = ZoneInfo(TIMEZONE_NAME)


# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    ""
).strip()

CHAT_ID = os.getenv(
    "CHAT_ID",
    ""
).strip()


# ============================================================
# BOT
# ============================================================

BOT_NAME = os.getenv(
    "BOT_NAME",
    "KYSFX XAUUSD NEWS BOT"
)

CHECK_INTERVAL = int(
    os.getenv(
        "CHECK_INTERVAL",
        "60"
    )
)


# ============================================================
# NEWS
# ============================================================

NEWS_ENABLED = os.getenv(
    "NEWS_ENABLED",
    "true"
).lower() == "true"

NEWS_INTERVAL = int(
    os.getenv(
        "NEWS_INTERVAL",
        "300"
    )
)


# ============================================================
# ECONOMIC CALENDAR
# ============================================================

CALENDAR_ENABLED = os.getenv(
    "CALENDAR_ENABLED",
    "true"
).lower() == "true"

CALENDAR_INTERVAL = int(
    os.getenv(
        "CALENDAR_INTERVAL",
        "300"
    )
)

CALENDAR_HOURS_AHEAD = int(
    os.getenv(
        "CALENDAR_HOURS_AHEAD",
        "48"
    )
)

CALENDAR_RECENT_HOURS = int(
    os.getenv(
        "CALENDAR_RECENT_HOURS",
        "6"
    )
)


# ============================================================
# CALENDAR SOURCE
# ============================================================

CALENDAR_URL = os.getenv(
    "CALENDAR_URL",
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
)


# ============================================================
# SESSION
# ============================================================

SESSIONS_ENABLED = os.getenv(
    "SESSIONS_ENABLED",
    "true"
).lower() == "true"


# ============================================================
# DATABASE
# ============================================================

DATABASE_FILE = os.getenv(
    "DATABASE_FILE",
    "bot_state.db"
)


# ============================================================
# VALIDATION
# ============================================================

def validate_config():
    """
    Validasi konfigurasi penting.
    """

    errors = []

    if not BOT_TOKEN:
        errors.append(
            "BOT_TOKEN belum diisi"
        )

    if not CHAT_ID:
        errors.append(
            "CHAT_ID belum diisi"
        )

    if errors:
        raise RuntimeError(
            " | ".join(errors)
        )

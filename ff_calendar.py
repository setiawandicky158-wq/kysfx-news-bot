import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from html import unescape
from zoneinfo import ZoneInfo

import requests


# ============================================================
# CONFIG
# ============================================================

WITA = ZoneInfo("Asia/Makassar")

CHECK_TIMEOUT = int(os.getenv("CALENDAR_TIMEOUT", "20"))
MAX_RETRIES = int(os.getenv("CALENDAR_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("CALENDAR_RETRY_DELAY", "3"))

# Endpoint JSON yang sebelumnya berhasil digunakan bot
FOREX_FACTORY_URL = os.getenv(
    "FOREX_FACTORY_JSON_URL",
    "https://www.forexfactory.com/calendar"
)

EVENT_WINDOW_HOURS = float(
    os.getenv("EVENT_WINDOW_HOURS", "2")
)

CACHE_HOURS = float(
    os.getenv("CALENDAR_CACHE_HOURS", "48")
)


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/json,text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.forexfactory.com/",
    "Connection": "keep-alive",
})


# ============================================================
# CACHE
# ============================================================

_cached_events = []
_cache_time = None


# ============================================================
# GOLD RELEVANT EVENTS
# ============================================================

GOLD_KEYWORDS = [
    # Inflation
    "cpi",
    "core cpi",
    "ppi",
    "core ppi",
    "pce",
    "core pce",
    "inflation",

    # Employment
    "non-farm",
    "nonfarm",
    "payroll",
    "employment",
    "unemployment",
    "jobless claims",
    "initial jobless claims",
    "jolts",
    "average hourly earnings",
    "adp",

    # Fed
    "federal funds",
    "fed interest rate",
    "interest rate decision",
    "fomc",
    "fed chair",
    "powell",
    "fed press conference",

    # US economy
    "retail sales",
    "core retail sales",
    "gdp",
    "ism",
    "manufacturing pmi",
    "services pmi",
    "consumer confidence",
    "consumer sentiment",

    # China
    "china cpi",
    "chinese cpi",
    "china ppi",
    "chinese ppi",

    # Major central banks
    "ecb interest rate",
    "ecb press conference",
    "boj interest rate",
    "boe interest rate",
    "rba interest rate",
]


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    text = unescape(str(value))
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_number(value):
    if value is None:
        return None

    value = clean_text(value)

    if not value:
        return None

    value = (
        value
        .replace(",", "")
        .replace("%", "")
        .replace("$", "")
        .replace("K", "")
        .replace("M", "")
        .replace("B", "")
    )

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value
    )

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


# ============================================================
# EVENT NORMALIZATION
# ============================================================

def normalize_event_name(name):

    name = clean_text(name)

    lower = name.lower()

    if (
        "non-farm payroll" in lower
        or "nonfarm payroll" in lower
        or "non-farm employment change" in lower
        or "nonfarm employment change" in lower
    ):
        return "NFP"

    if (
        "federal funds rate" in lower
        or "fed interest rate decision" in lower
    ):
        return "Federal Funds Rate"

    if "core cpi" in lower:
        return "Core CPI"

    if lower == "cpi":
        return "CPI"

    if "core pce" in lower:
        return "Core PCE"

    if lower == "pce":
        return "PCE"

    return name


# ============================================================
# IMPACT
# ============================================================

def impact_stars(impact):

    value = clean_text(impact).lower()

    if "high" in value:
        return "⭐⭐⭐⭐⭐"

    if "medium" in value:
        return "⭐⭐⭐"

    return "⭐"


def is_high_impact(impact):

    value = clean_text(impact).lower()

    return "high" in value


# ============================================================
# GOLD FILTER
# ============================================================

def is_gold_event(event_name, currency, impact):

    name = clean_text(event_name).lower()
    currency = clean_text(currency).upper()

    # Hanya high impact
    if not is_high_impact(impact):
        return False

    # USD adalah prioritas utama
    if currency == "USD":

        return any(
            keyword in name
            for keyword in GOLD_KEYWORDS
        )

    # China
    if currency in ("CNY", "CNH"):

        return any(
            keyword in name
            for keyword in [
                "cpi",
                "ppi",
                "inflation",
            ]
        )

    # ECB / BOJ / BOE / RBA
    if currency in (
        "EUR",
        "JPY",
        "GBP",
        "AUD",
    ):

        return any(
            keyword in name
            for keyword in [
                "interest rate",
                "rate decision",
                "monetary policy",
                "press conference",
                "policy statement",
            ]
        )

    return False


# ============================================================
# DATETIME PARSER
# ============================================================

def parse_datetime(date_value, time_value):

    date_text = clean_text(date_value)
    time_text = clean_text(time_value)

    if not date_text:
        return None

    if not time_text:
        return None

    now = datetime.now(WITA)

    date_lower = date_text.lower()

    # --------------------------------------------------------
    # RELATIVE DATE
    # --------------------------------------------------------

    if date_lower == "today":

        event_date = now.date()

    elif date_lower == "tomorrow":

        event_date = (
            now + timedelta(days=1)
        ).date()

    else:

        event_date = None

        date_formats = [
            "%Y-%m-%d",
            "%m-%d-%Y",
            "%m/%d/%Y",
            "%Y/%m/%d",
            "%b %d",
            "%B %d",
            "%b %d, %Y",
            "%B %d, %Y",
        ]

        for fmt in date_formats:

            try:

                parsed = datetime.strptime(
                    date_text,
                    fmt
                )

                if "%Y" not in fmt:

                    parsed = parsed.replace(
                        year=now.year
                    )

                event_date = parsed.date()

                break

            except ValueError:
                continue

        if event_date is None:
            return None

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    time_text = (
        time_text
        .lower()
        .replace(" ", "")
    )

    if time_text in (
        "all-day",
        "allday",
        "tentative",
        "day",
    ):
        return None

    time_formats = [
        "%I:%M%p",
        "%I%p",
        "%H:%M",
    ]

    parsed_time = None

    for fmt in time_formats:

        try:

            parsed_time = datetime.strptime(
                time_text,
                fmt
            ).time()

            break

        except ValueError:
            continue

    if parsed_time is None:
        return None

    return datetime.combine(
        event_date,
        parsed_time,
        tzinfo=WITA
    )


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(response):

    try:
        return response.json()

    except Exception:

        text = response.text.strip()

        if not text:
            return None

        try:
            return json.loads(text)

        except Exception:

            # Cari JSON object / array
            match = re.search(
                r"(\[.*\]|\{.*\})",
                text,
                re.DOTALL
            )

            if not match:
                return None

            try:
                return json.loads(
                    match.group(1)
                )
            except Exception:
                return None


# ============================================================
# NORMALIZE JSON EVENTS
# ============================================================

def normalize_raw_events(data):

    if data is None:
        return []

    # --------------------------------------------------------
    # Jika langsung list
    # --------------------------------------------------------

    if isinstance(data, list):

        return data

    # --------------------------------------------------------
    # Jika dictionary
    # --------------------------------------------------------

    if isinstance(data, dict):

        possible_keys = [
            "events",
            "calendar",
            "data",
            "results",
            "items",
        ]

        for key in possible_keys:

            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


# ============================================================
# GET JSON FIELD
# ============================================================

def get_field(item, *keys):

    if not isinstance(item, dict):
        return ""

    for key in keys:

        if key in item:

            value = item.get(key)

            if value is not None:
                return value

    return ""


# ============================================================
# PARSE JSON EVENTS
# ============================================================

def parse_json_events(data):

    raw_events = normalize_raw_events(
        data
    )

    logger.info(
        "[CALENDAR] Raw events received: %s",
        len(raw_events)
    )

    events = []

    for item in raw_events:

        if not isinstance(item, dict):
            continue

        try:

            # ------------------------------------------------
            # EVENT
            # ------------------------------------------------

            event_name = clean_text(
                get_field(
                    item,
                    "event",
                    "title",
                    "name",
                    "description",
                )
            )

            if not event_name:
                continue

            # ------------------------------------------------
            # CURRENCY
            # ------------------------------------------------

            currency = clean_text(
                get_field(
                    item,
                    "currency",
                    "country",
                    "ccy",
                )
            ).upper()

            # ------------------------------------------------
            # IMPACT
            # ------------------------------------------------

            impact = clean_text(
                get_field(
                    item,
                    "impact",
                    "importance",
                    "impact_name",
                )
            )

            # ------------------------------------------------
            # DATE
            # ------------------------------------------------

            date_value = clean_text(
                get_field(
                    item,
                    "date",
                    "event_date",
                    "day",
                )
            )

            # ------------------------------------------------
            # TIME
            # ------------------------------------------------

            time_value = clean_text(
                get_field(
                    item,
                    "time",
                    "event_time",
                )
            )

            # ------------------------------------------------
            # DATETIME DIRECT
            # ------------------------------------------------

            event_datetime = None

            direct_datetime = get_field(
                item,
                "datetime",
                "dateTime",
                "timestamp",
                "start",
            )

            if direct_datetime:

                try:

                    if isinstance(
                        direct_datetime,
                        (int, float)
                    ):

                        event_datetime = (
                            datetime.fromtimestamp(
                                direct_datetime,
                                tz=WITA
                            )
                        )

                    else:

                        dt_string = clean_text(
                            direct_datetime
                        )

                        dt_string = (
                            dt_string
                            .replace("Z", "+00:00")
                        )

                        parsed = datetime.fromisoformat(
                            dt_string
                        )

                        if parsed.tzinfo is None:

                            parsed = parsed.replace(
                                tzinfo=WITA
                            )

                        event_datetime = parsed.astimezone(
                            WITA
                        )

                except Exception:
                    event_datetime = None

            # ------------------------------------------------
            # PARSE DATE + TIME
            # ------------------------------------------------

            if event_datetime is None:

                event_datetime = parse_datetime(
                    date_value,
                    time_value
                )

            # ------------------------------------------------
            # FILTER GOLD
            # ------------------------------------------------

            if not is_gold_event(
                event_name,
                currency,
                impact
            ):
                continue

            # ------------------------------------------------
            # VALUES
            # ------------------------------------------------

            forecast = clean_text(
                get_field(
                    item,
                    "forecast",
                    "consensus",
                    "expected",
                )
            )

            previous = clean_text(
                get_field(
                    item,
                    "previous",
                    "prior",
                )
            )

            actual = clean_text(
                get_field(
                    item,
                    "actual",
                    "result",
                )
            )

            normalized_name = normalize_event_name(
                event_name
            )

            events.append({
                "event": normalized_name,
                "original_event": event_name,
                "currency": currency,
                "impact": impact,
                "stars": impact_stars(impact),
                "date": date_value,
                "time": time_value,
                "datetime": event_datetime,
                "forecast": forecast,
                "previous": previous,
                "actual": actual,
            })

        except Exception as e:

            logger.warning(
                "[CALENDAR] Event parse error: %s",
                e
            )

            continue

    logger.info(
        "[CALENDAR] Gold events after filter: %s",
        len(events)
    )

    return events


# ============================================================
# FETCH CALENDAR
# ============================================================

def fetch_calendar():

    global _cached_events
    global _cache_time

    logger.info(
        "[CALENDAR] Checking Forex Factory JSON feed..."
    )

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = session.get(
                FOREX_FACTORY_URL,
                timeout=CHECK_TIMEOUT
            )

            logger.info(
                "[CALENDAR] HTTP Status: %s",
                response.status_code
            )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            if response.status_code == 200:

                data = extract_json(
                    response
                )

                if data is None:

                    logger.error(
                        "[CALENDAR] Invalid JSON response"
                    )

                    continue

                events = parse_json_events(
                    data
                )

                # Cache hanya jika benar-benar
                # berhasil mendapatkan data
                _cached_events = events
                _cache_time = datetime.now(
                    WITA
                )

                return events

            # ------------------------------------------------
            # RATE LIMIT / FORBIDDEN
            # ------------------------------------------------

            if response.status_code in (
                403,
                429,
            ):

                logger.warning(
                    "[CALENDAR] HTTP %s "
                    "(attempt %s/%s)",
                    response.status_code,
                    attempt,
                    MAX_RETRIES
                )

                last_error = (
                    f"HTTP {response.status_code}"
                )

                if attempt < MAX_RETRIES:

                    time.sleep(
                        RETRY_DELAY * attempt
                    )

                continue

            # ------------------------------------------------
            # OTHER HTTP ERROR
            # ------------------------------------------------

            logger.error(
                "[CALENDAR] HTTP error: %s",
                response.status_code
            )

            last_error = (
                f"HTTP {response.status_code}"
            )

        except requests.exceptions.RequestException as e:

            last_error = str(e)

            logger.warning(
                "[CALENDAR] Request error "
                "(attempt %s/%s): %s",
                attempt,
                MAX_RETRIES,
                e
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    RETRY_DELAY * attempt
                )

        except Exception as e:

            last_error = str(e)

            logger.exception(
                "[CALENDAR] Unexpected error: %s",
                e
            )

            break

    # ========================================================
    # CACHE FALLBACK
    # ========================================================

    if _cached_events:

        cache_age = None

        if _cache_time:

            cache_age = (
                datetime.now(WITA)
                - _cache_time
            )

        if (
            cache_age is None
            or cache_age.total_seconds()
            <= CACHE_HOURS * 3600
        ):

            logger.warning(
                "[CALENDAR] Forex Factory unavailable "
                "(%s). Using cached events: %s",
                last_error,
                len(_cached_events)
            )

            return _cached_events

    logger.error(
        "[CALENDAR] No usable calendar data. "
        "Last error: %s",
        last_error
    )

    return []


# ============================================================
# FUNDAMENTAL COMPARISON
# ============================================================

def compare_actual_forecast(
    actual,
    forecast
):

    a = clean_number(actual)
    f = clean_number(forecast)

    if a is None or f is None:
        return "unknown"

    if a > f:
        return "above"

    if a < f:
        return "below"

    return "inline"


# ============================================================
# FUNDAMENTAL ANALYSIS
# ============================================================

def fundamental_analysis(event):

    name = clean_text(
        event.get("event", "")
    )

    lower = name.lower()

    actual = event.get(
        "actual",
        ""
    )

    forecast = event.get(
        "forecast",
        ""
    )

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    if (
        "cpi" in lower
        or "ppi" in lower
        or "pce" in lower
        or "inflation" in lower
    ):
        category = "inflation"

    elif (
        "nfp" in lower
        or "payroll" in lower
        or "employment" in lower
        or "unemployment" in lower
        or "jobless" in lower
        or "jolts" in lower
        or "wage" in lower
        or "adp" in lower
    ):
        category = "employment"

    elif (
        "federal funds" in lower
        or "fomc" in lower
        or "fed chair" in lower
        or "powell" in lower
        or "interest rate" in lower
        or "rate decision" in lower
    ):
        category = "fed"

    elif (
        "gdp" in lower
        or "retail" in lower
        or "ism" in lower
        or "consumer confidence" in lower
        or "consumer sentiment" in lower
    ):
        category = "growth"

    else:
        category = "other"

    # --------------------------------------------------------
    # PRE EVENT
    # --------------------------------------------------------

    if not actual:

        if category == "inflation":

            return {
                "gold": (
                    "Data inflasi menjadi fokus utama. "
                    "Actual di bawah Forecast cenderung "
                    "mendukung Gold."
                ),
                "usd": (
                    "Inflasi lebih rendah dapat meningkatkan "
                    "ekspektasi pelonggaran Fed dan menekan USD."
                ),
                "yield": (
                    "Inflasi lebih rendah berpotensi "
                    "menekan Treasury Yield."
                ),
                "bias": (
                    "🟡 NEUTRAL — MENUNGGU DATA"
                ),
            }

        if category == "employment":

            return {
                "gold": (
                    "Data tenaga kerja menjadi katalis "
                    "utama. Data lebih lemah dari Forecast "
                    "cenderung mendukung Gold."
                ),
                "usd": (
                    "Employment lemah dapat meningkatkan "
                    "ekspektasi rate cut dan menekan USD."
                ),
                "yield": (
                    "Employment lemah berpotensi "
                    "menekan Treasury Yield."
                ),
                "bias": (
                    "🟡 NEUTRAL — MENUNGGU DATA"
                ),
            }

        if category == "fed":

            return {
                "gold": (
                    "Fokus pada keputusan suku bunga, "
                    "guidance dan perubahan ekspektasi "
                    "kebijakan Fed."
                ),
                "usd": (
                    "Fed hawkish cenderung bullish USD; "
                    "Fed dovish cenderung bearish USD."
                ),
                "yield": (
                    "Fed hawkish cenderung menaikkan "
                    "Treasury Yield."
                ),
                "bias": (
                    "🟡 NEUTRAL — MENUNGGU FED"
                ),
            }

        if category == "growth":

            return {
                "gold": (
                    "Data pertumbuhan dapat mengubah "
                    "ekspektasi kebijakan Fed."
                ),
                "usd": (
                    "Growth kuat cenderung mendukung USD."
                ),
                "yield": (
                    "Growth kuat dapat meningkatkan Yield."
                ),
                "bias": (
                    "🟡 NEUTRAL — MENUNGGU DATA"
                ),
            }

        return {
            "gold": (
                "Potensi volatilitas Gold meningkat. "
                "Tunggu reaksi harga setelah data."
            ),
            "usd": "Pantau arah USD.",
            "yield": "Pantau Treasury Yield.",
            "bias": "🟡 NEUTRAL",
        }

    # --------------------------------------------------------
    # POST EVENT
    # --------------------------------------------------------

    comparison = compare_actual_forecast(
        actual,
        forecast
    )

    # --------------------------------------------------------
    # INFLATION
    # --------------------------------------------------------

    if category == "inflation":

        if comparison == "below":

            return {
                "gold": (
                    f"Actual {actual} di bawah "
                    f"Forecast {forecast}. "
                    "Tekanan inflasi lebih rendah "
                    "cenderung mendukung Gold."
                ),
                "usd": (
                    "Ekspektasi rate cut dapat meningkat "
                    "sehingga USD berpotensi melemah."
                ),
                "yield": (
                    "Treasury Yield berpotensi turun."
                ),
                "bias": "🟢 BULLISH GOLD",
            }

        if comparison == "above":

            return {
                "gold": (
                    f"Actual {actual} di atas "
                    f"Forecast {forecast}. "
                    "Tekanan inflasi lebih tinggi "
                    "cenderung menekan Gold."
                ),
                "usd": (
                    "Ekspektasi higher-for-longer "
                    "dapat meningkat sehingga USD "
                    "berpotensi menguat."
                ),
                "yield": (
                    "Treasury Yield berpotensi naik."
                ),
                "bias": "🔴 BEARISH GOLD",
            }

    # --------------------------------------------------------
    # EMPLOYMENT
    # --------------------------------------------------------

    if category == "employment":

        if comparison == "below":

            return {
                "gold": (
                    f"Actual {actual} di bawah "
                    f"Forecast {forecast}. "
                    "Pasar tenaga kerja lebih lemah."
                ),
                "usd": (
                    "USD berpotensi melemah karena "
                    "ekspektasi rate cut dapat meningkat."
                ),
                "yield": (
                    "Treasury Yield berpotensi turun."
                ),
                "bias": "🟢 BULLISH GOLD",
            }

        if comparison == "above":

            return {
                "gold": (
                    f"Actual {actual} di atas "
                    f"Forecast {forecast}. "
                    "Data tenaga kerja lebih kuat."
                ),
                "usd": (
                    "USD berpotensi menguat."
                ),
                "yield": (
                    "Treasury Yield berpotensi naik."
                ),
                "bias": "🔴 BEARISH GOLD",
            }

    # --------------------------------------------------------
    # GROWTH
    # --------------------------------------------------------

    if category == "growth":

        if comparison == "above":

            return {
                "gold": (
                    "Data growth lebih kuat dari "
                    "Forecast. Ekspektasi Fed hawkish "
                    "dapat menekan Gold."
                ),
                "usd": "USD berpotensi menguat.",
                "yield": (
                    "Treasury Yield berpotensi naik."
                ),
                "bias": "🔴 BEARISH GOLD",
            }

        if comparison == "below":

            return {
                "gold": (
                    "Data growth lebih lemah dari "
                    "Forecast. Ekspektasi Fed dovish "
                    "dapat mendukung Gold."
                ),
                "usd": "USD berpotensi melemah.",
                "yield": (
                    "Treasury Yield berpotensi turun."
                ),
                "bias": "🟢 BULLISH GOLD",
            }

    # --------------------------------------------------------
    # FED
    # --------------------------------------------------------

    if category == "fed":

        return {
            "gold": (
                "Reaksi Gold bergantung pada keputusan "
                "Fed, guidance dan perubahan rate expectations."
            ),
            "usd": (
                "Hawkish Fed → USD cenderung bullish. "
                "Dovish Fed → USD cenderung bearish."
            ),
            "yield": (
                "Hawkish Fed → Yield cenderung naik. "
                "Dovish Fed → Yield cenderung turun."
            ),
            "bias": (
                "🟡 ANALISIS GUIDANCE FED"
            ),
        }

    return {
        "gold": (
            "Reaksi Gold bergantung pada detail data "
            "dan reaksi USD/Yield."
        ),
        "usd": "Pantau USD.",
        "yield": "Pantau Treasury Yield.",
        "bias": "🟡 NEUTRAL",
    }


# ============================================================
# COUNTDOWN
# ============================================================

def countdown(event_datetime):

    if not event_datetime:
        return None

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
# GET UPCOMING EVENTS
# ============================================================

def get_calendar_events(
    hours_ahead=48
):

    events = fetch_calendar()

    now = datetime.now(WITA)

    end = (
        now
        + timedelta(
            hours=hours_ahead
        )
    )

    valid_events = []

    for event in events:

        event_datetime = event.get(
            "datetime"
        )

        if not event_datetime:
            continue

        if event_datetime < now:
            continue

        if event_datetime > end:
            continue

        event["countdown"] = countdown(
            event_datetime
        )

        valid_events.append(
            event
        )

    valid_events.sort(
        key=lambda x: x["datetime"]
    )

    logger.info(
        "[CALENDAR] Gold events within %.1f "
        "hours: %s",
        hours_ahead,
        len(valid_events)
    )

    for event in valid_events:

        logger.info(
            "[CALENDAR] Upcoming: %s | %s | %s WITA",
            event.get("event"),
            event.get("currency"),
            event["datetime"].strftime(
                "%d-%m-%Y %H:%M"
            )
        )

    return valid_events


# ============================================================
# EVENT ID
# ============================================================

def get_event_id(event):

    return "|".join([
        clean_text(
            event.get("event", "")
        ),
        clean_text(
            event.get("currency", "")
        ),
        str(
            event.get("datetime", "")
        ),
    ])


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_calendar_event(
    event,
    result=False
):

    event_datetime = event.get(
        "datetime"
    )

    if event_datetime:

        event_time = (
            event_datetime
            .astimezone(WITA)
            .strftime(
                "%d-%m-%Y %H:%M"
            )
        )

    else:

        event_time = (
            f"{event.get('date', '')} "
            f"{event.get('time', '')}"
        )

    analysis = fundamental_analysis(
        event
    )

    if result:

        header = (
            "🚨 <b>GOLD EVENT RESULT</b>"
        )

    else:

        header = (
            "⏰ <b>GOLD ECONOMIC EVENT</b>"
        )

    actual = (
        event.get("actual")
        or "-"
    )

    forecast = (
        event.get("forecast")
        or "-"
    )

    previous = (
        event.get("previous")
        or "-"
    )

    countdown_text = (
        event.get("countdown")
        or "-"
    )

    message = (
        f"{header}\n\n"

        f"📊 <b>{event.get('event', '')}</b>\n"
        f"🌎 Currency: "
        f"{event.get('currency', '')}\n"
        f"🕐 {event_time} WITA\n\n"

        f"⚠️ <b>HIGH IMPACT</b> "
        f"{event.get('stars', '⭐⭐⭐⭐⭐')}\n\n"
    )

    if not result:

        message += (
            f"⏳ <b>COUNTDOWN:</b> "
            f"{countdown_text}\n\n"
        )

    message += (
        "━━━━━━━━━━━━━━━━━━\n\n"

        "📌 <b>DATA EVENT</b>\n\n"

        f"Forecast: <b>{forecast}</b>\n"
        f"Previous: <b>{previous}</b>\n"
        f"Actual: <b>{actual}</b>\n\n"

        "━━━━━━━━━━━━━━━━━━\n\n"

        "🧠 <b>FUNDAMENTAL ANALYSIS</b>\n\n"

        f"🟡 <b>GOLD</b>\n"
        f"{analysis['gold']}\n\n"

        f"💵 <b>USD</b>\n"
        f"{analysis['usd']}\n\n"

        f"📈 <b>TREASURY YIELD</b>\n"
        f"{analysis['yield']}\n\n"

        f"🎯 <b>FUNDAMENTAL BIAS</b>\n"
        f"{analysis['bias']}\n\n"

        "━━━━━━━━━━━━━━━━━━\n\n"

        "⚠️ <b>TRADING PLAN</b>\n"
        "Jangan entry hanya berdasarkan forecast. "
        "Tunggu actual, reaksi USD/Yield dan "
        "konfirmasi price action XAUUSD."
    )

    return message

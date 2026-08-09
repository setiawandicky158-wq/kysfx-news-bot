import re
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

# ============================================================
# CONFIG
# ============================================================

FOREX_FACTORY_JSON_URL = (
    "https://www.forexfactory.com/calendar"
)

WITA = ZoneInfo("Asia/Makassar")

REQUEST_TIMEOUT = 30

# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)

# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "application/json,text/html,"
        "application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.forexfactory.com/",
})


# ============================================================
# GOLD EVENT KEYWORDS
# ============================================================

GOLD_USD_KEYWORDS = [

    # --------------------------------------------------------
    # INFLATION
    # --------------------------------------------------------

    "cpi",
    "core cpi",
    "consumer price index",

    "ppi",
    "core ppi",
    "producer price index",

    "pce",
    "core pce",
    "personal consumption expenditures",

    "inflation",

    # --------------------------------------------------------
    # EMPLOYMENT
    # --------------------------------------------------------

    "non-farm",
    "nonfarm",
    "payroll",
    "non-farm payroll",
    "nonfarm payroll",

    "unemployment",
    "jobless claims",
    "initial jobless claims",
    "continuing jobless claims",

    "jolts",
    "job openings",

    "average hourly earnings",
    "hourly earnings",

    "adp non-farm",
    "adp nonfarm",
    "adp employment",

    # --------------------------------------------------------
    # FED
    # --------------------------------------------------------

    "federal funds",
    "fed interest rate",
    "interest rate decision",

    "fomc",
    "fomc statement",
    "fomc press conference",

    "fed chair",
    "powell",
    "fed speaks",

    # --------------------------------------------------------
    # US GROWTH
    # --------------------------------------------------------

    "retail sales",
    "core retail sales",

    "gdp",
    "gross domestic product",

    "ism manufacturing",
    "ism services",
    "ism manufacturing pmi",
    "ism services pmi",

    "consumer confidence",
    "cb consumer confidence",

    "michigan consumer sentiment",
    "michigan inflation expectations",
]


# ============================================================
# CHINA KEYWORDS
# ============================================================

CHINA_GOLD_KEYWORDS = [
    "cpi",
    "ppi",
    "inflation",
]


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    value = str(value)

    value = (
        value
        .replace("\xa0", " ")
        .replace("&nbsp;", " ")
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# NUMBER CLEANER
# ============================================================

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
        return float(
            match.group(0)
        )
    except ValueError:
        return None


# ============================================================
# GOLD FILTER
# ============================================================

def is_gold_event(
    event_name,
    currency,
    impact
):

    name = clean_text(
        event_name
    )

    lower = name.lower()

    currency = clean_text(
        currency
    ).upper()

    impact = clean_text(
        impact
    ).lower()

    # ========================================================
    # ONLY HIGH IMPACT
    # ========================================================

    if "high" not in impact:
        return False

    # ========================================================
    # USD = PRIMARY XAUUSD DRIVER
    # ========================================================

    if currency == "USD":

        for keyword in GOLD_USD_KEYWORDS:

            if keyword in lower:
                return True

        return False

    # ========================================================
    # CHINA = SECONDARY GOLD DRIVER
    # ========================================================

    if currency in (
        "CNY",
        "CNH",
    ):

        for keyword in CHINA_GOLD_KEYWORDS:

            if keyword in lower:
                return True

        return False

    # ========================================================
    # EVERYTHING ELSE = IGNORE
    # ========================================================

    return False


# ============================================================
# IMPACT
# ============================================================

def impact_stars(impact):

    value = clean_text(
        impact
    ).lower()

    if "high" in value:
        return "⭐⭐⭐⭐⭐"

    if "medium" in value:
        return "⭐⭐⭐"

    return "⭐"


# ============================================================
# NORMALIZE EVENT
# ============================================================

def normalize_event_name(name):

    name = clean_text(
        name
    )

    lower = name.lower()

    if (
        "non-farm" in lower
        or "nonfarm" in lower
    ) and "payroll" in lower:

        return "NFP"

    if "non-farm employment" in lower:
        return "NFP"

    if "federal funds rate" in lower:
        return "Federal Funds Rate"

    if (
        "fed interest rate" in lower
        or "interest rate decision" in lower
    ) and "fed" in lower:

        return "Federal Funds Rate"

    return name


# ============================================================
# DATETIME PARSER
# ============================================================

def parse_datetime(
    date_value,
    time_value
):

    date_text = clean_text(
        date_value
    )

    time_text = clean_text(
        time_value
    )

    if not date_text:
        return None

    if not time_text:
        return None

    lower_time = (
        time_text
        .lower()
        .replace(" ", "")
    )

    # --------------------------------------------------------
    # INVALID TIME
    # --------------------------------------------------------

    if lower_time in (
        "",
        "all-day",
        "all-dayevent",
        "allday",
        "tentative",
        "day",
    ):
        return None

    now = datetime.now(
        WITA
    )

    # ========================================================
    # DATE
    # ========================================================

    event_date = None

    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%b %d %Y",
        "%B %d %Y",
        "%b %d",
        "%B %d",
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

            event_date = (
                parsed.date()
            )

            break

        except ValueError:
            continue

    # --------------------------------------------------------
    # TODAY
    # --------------------------------------------------------

    if not event_date:

        if date_text.lower() == "today":

            event_date = now.date()

    # --------------------------------------------------------
    # TOMORROW
    # --------------------------------------------------------

    if not event_date:

        if date_text.lower() == "tomorrow":

            event_date = (
                now + timedelta(
                    days=1
                )
            ).date()

    if not event_date:
        return None

    # ========================================================
    # TIME
    # ========================================================

    parsed_time = None

    time_formats = [
        "%I:%M%p",
        "%I%p",
        "%H:%M",
        "%H:%M:%S",
    ]

    for fmt in time_formats:

        try:

            parsed_time = datetime.strptime(
                lower_time,
                fmt
            ).time()

            break

        except ValueError:
            continue

    if not parsed_time:
        return None

    return datetime.combine(
        event_date,
        parsed_time,
        tzinfo=WITA
    )


# ============================================================
# JSON VALUE HELPER
# ============================================================

def get_value(
    item,
    *keys
):

    if not isinstance(
        item,
        dict
    ):
        return ""

    for key in keys:

        if key in item:

            value = item.get(
                key
            )

            if value is not None:
                return value

    return ""


# ============================================================
# FETCH FOREX FACTORY
# ============================================================

def fetch_calendar():

    logger.info(
        "[CALENDAR] Checking Forex Factory JSON feed..."
    )

    try:

        response = session.get(
            FOREX_FACTORY_JSON_URL,
            timeout=REQUEST_TIMEOUT
        )

        logger.info(
            "[CALENDAR] HTTP Status: %s",
            response.status_code
        )

        if response.status_code != 200:

            logger.error(
                "[CALENDAR] HTTP error: %s",
                response.status_code
            )

            return []

        # ====================================================
        # TRY JSON
        # ====================================================

        try:

            data = response.json()

            if isinstance(
                data,
                list
            ):

                logger.info(
                    "[CALENDAR] Raw events received: %s",
                    len(data)
                )

                return data

            if isinstance(
                data,
                dict
            ):

                for key in (
                    "events",
                    "calendar",
                    "data",
                ):

                    if isinstance(
                        data.get(key),
                        list
                    ):

                        events = data.get(
                            key
                        )

                        logger.info(
                            "[CALENDAR] Raw events received: %s",
                            len(events)
                        )

                        return events

        except ValueError:
            pass

        logger.error(
            "[CALENDAR] Response is not valid JSON."
        )

        return []

    except requests.exceptions.RequestException as e:

        logger.error(
            "[CALENDAR] Request error: %s",
            e
        )

        return []

    except Exception as e:

        logger.exception(
            "[CALENDAR] Unexpected error: %s",
            e
        )

        return []


# ============================================================
# PARSE JSON EVENTS
# ============================================================

def parse_events(
    raw_events
):

    events = []

    for item in raw_events:

        try:

            if not isinstance(
                item,
                dict
            ):
                continue

            # ------------------------------------------------
            # EVENT
            # ------------------------------------------------

            event_name = clean_text(
                get_value(
                    item,
                    "event",
                    "title",
                    "name"
                )
            )

            if not event_name:
                continue

            # ------------------------------------------------
            # CURRENCY
            # ------------------------------------------------

            currency = clean_text(
                get_value(
                    item,
                    "currency",
                    "country",
                    "ccy"
                )
            ).upper()

            # ------------------------------------------------
            # IMPACT
            # ------------------------------------------------

            impact = clean_text(
                get_value(
                    item,
                    "impact",
                    "importance"
                )
            )

            # ------------------------------------------------
            # DATE
            # ------------------------------------------------

            date_value = get_value(
                item,
                "date",
                "event_date"
            )

            # ------------------------------------------------
            # TIME
            # ------------------------------------------------

            time_value = get_value(
                item,
                "time",
                "event_time"
            )

            # ------------------------------------------------
            # DATETIME
            # ------------------------------------------------

            event_datetime = None

            raw_datetime = get_value(
                item,
                "datetime",
                "timestamp"
            )

            if raw_datetime:

                if isinstance(
                    raw_datetime,
                    (int, float)
                ):

                    try:

                        event_datetime = (
                            datetime.fromtimestamp(
                                raw_datetime,
                                tz=WITA
                            )
                        )

                    except Exception:
                        event_datetime = None

                elif isinstance(
                    raw_datetime,
                    str
                ):

                    raw_datetime = (
                        raw_datetime
                        .strip()
                    )

                    try:

                        event_datetime = (
                            datetime.fromisoformat(
                                raw_datetime
                            )
                        )

                        if event_datetime.tzinfo is None:

                            event_datetime = (
                                event_datetime.replace(
                                    tzinfo=WITA
                                )
                            )

                        else:

                            event_datetime = (
                                event_datetime.astimezone(
                                    WITA
                                )
                            )

                    except ValueError:
                        event_datetime = None

            if not event_datetime:

                event_datetime = parse_datetime(
                    date_value,
                    time_value
                )

            # ------------------------------------------------
            # FORECAST
            # ------------------------------------------------

            forecast = clean_text(
                get_value(
                    item,
                    "forecast",
                    "consensus"
                )
            )

            # ------------------------------------------------
            # PREVIOUS
            # ------------------------------------------------

            previous = clean_text(
                get_value(
                    item,
                    "previous",
                    "prev"
                )
            )

            # ------------------------------------------------
            # ACTUAL
            # ------------------------------------------------

            actual = clean_text(
                get_value(
                    item,
                    "actual",
                    "result"
                )
            )

            # ------------------------------------------------
            # GOLD FILTER
            # ------------------------------------------------

            if not is_gold_event(
                event_name,
                currency,
                impact
            ):
                continue

            events.append({
                "event": normalize_event_name(
                    event_name
                ),
                "original_event": event_name,
                "currency": currency,
                "impact": impact,
                "stars": impact_stars(
                    impact
                ),
                "date": clean_text(
                    date_value
                ),
                "time": clean_text(
                    time_value
                ),
                "datetime": event_datetime,
                "forecast": forecast,
                "previous": previous,
                "actual": actual,
            })

        except Exception as e:

            logger.warning(
                "[CALENDAR] Parse event error: %s",
                e
            )

            continue

    return events


# ============================================================
# FUNDAMENTAL COMPARISON
# ============================================================

def compare_actual_forecast(
    actual,
    forecast
):

    a = clean_number(
        actual
    )

    f = clean_number(
        forecast
    )

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

def fundamental_analysis(
    event
):

    name = clean_text(
        event.get(
            "event",
            ""
        )
    )

    lower = name.lower()

    actual = clean_text(
        event.get(
            "actual",
            ""
        )
    )

    forecast = clean_text(
        event.get(
            "forecast",
            ""
        )
    )

    # ========================================================
    # CATEGORY
    # ========================================================

    if any(
        x in lower
        for x in [
            "cpi",
            "ppi",
            "pce",
            "inflation",
        ]
    ):

        category = "inflation"

    elif any(
        x in lower
        for x in [
            "nfp",
            "payroll",
            "employment",
            "unemployment",
            "jobless",
            "jolts",
            "earnings",
        ]
    ):

        category = "employment"

    elif any(
        x in lower
        for x in [
            "federal funds",
            "fomc",
            "fed chair",
            "powell",
            "fed interest",
        ]
    ):

        category = "fed"

    elif any(
        x in lower
        for x in [
            "retail",
            "gdp",
            "ism",
            "consumer confidence",
            "michigan",
        ]
    ):

        category = "growth"

    else:

        category = "other"

    # ========================================================
    # PRE-EVENT
    # ========================================================

    if not actual:

        if category == "inflation":

            return {
                "gold": (
                    "Data inflasi menjadi katalis utama "
                    "XAUUSD. Actual di bawah Forecast "
                    "umumnya mendukung Gold."
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
                    "Data tenaga kerja penting untuk ekspektasi "
                    "kebijakan Fed. Employment lebih lemah "
                    "dari ekspektasi cenderung bullish Gold."
                ),
                "usd": (
                    "Employment lemah dapat meningkatkan "
                    "ekspektasi rate cut dan menekan USD."
                ),
                "yield": (
                    "Data tenaga kerja lemah berpotensi "
                    "menekan Treasury Yield."
                ),
                "bias": (
                    "🟡 NEUTRAL — MENUNGGU DATA"
                ),
            }

        if category == "fed":

            return {
                "gold": (
                    "Fokus pada perubahan ekspektasi suku bunga "
                    "dan guidance Fed."
                ),
                "usd": (
                    "Fed hawkish cenderung bullish USD. "
                    "Fed dovish cenderung bearish USD."
                ),
                "yield": (
                    "Fed hawkish cenderung menaikkan Yield."
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
                    "Growth kuat dapat mendorong Yield naik."
                ),
                "bias": (
                    "🟡 NEUTRAL — MENUNGGU DATA"
                ),
            }

        return {
            "gold": (
                "Event berpotensi meningkatkan volatilitas "
                "XAUUSD."
            ),
            "usd": (
                "Pantau reaksi USD."
            ),
            "yield": (
                "Pantau Treasury Yield."
            ),
            "bias": (
                "🟡 NEUTRAL"
            ),
        }

    # ========================================================
    # POST EVENT
    # ========================================================

    comparison = compare_actual_forecast(
        actual,
        forecast
    )

    # ========================================================
    # INFLATION
    # ========================================================

    if category == "inflation":

        if comparison == "below":

            return {
                "gold": (
                    f"Actual {actual} di bawah Forecast "
                    f"{forecast}. Tekanan inflasi lebih rendah "
                    "dan dapat meningkatkan ekspektasi dovish Fed."
                ),
                "usd": (
                    "USD berpotensi melemah karena peluang "
                    "pelonggaran kebijakan dapat meningkat."
                ),
                "yield": (
                    "Treasury Yield berpotensi turun."
                ),
                "bias": (
                    "🟢 BULLISH GOLD"
                ),
            }

        if comparison == "above":

            return {
                "gold": (
                    f"Actual {actual} di atas Forecast "
                    f"{forecast}. Tekanan inflasi lebih tinggi "
                    "dapat mempertahankan kebijakan Fed ketat."
                ),
                "usd": (
                    "USD berpotensi menguat."
                ),
                "yield": (
                    "Treasury Yield berpotensi naik."
                ),
                "bias": (
                    "🔴 BEARISH GOLD"
                ),
            }

    # ========================================================
    # EMPLOYMENT
    # ========================================================

    if category == "employment":

        if comparison == "below":

            return {
                "gold": (
                    f"Actual {actual} di bawah Forecast "
                    f"{forecast}. Data tenaga kerja lebih lemah "
                    "dan dapat meningkatkan rate-cut expectations."
                ),
                "usd": (
                    "USD berpotensi melemah."
                ),
                "yield": (
                    "Treasury Yield berpotensi turun."
                ),
                "bias": (
                    "🟢 BULLISH GOLD"
                ),
            }

        if comparison == "above":

            return {
                "gold": (
                    f"Actual {actual} di atas Forecast "
                    f"{forecast}. Data tenaga kerja lebih kuat "
                    "dan dapat meningkatkan ekspektasi Fed hawkish."
                ),
                "usd": (
                    "USD berpotensi menguat."
                ),
                "yield": (
                    "Treasury Yield berpotensi naik."
                ),
                "bias": (
                    "🔴 BEARISH GOLD"
                ),
            }

    # ========================================================
    # GROWTH
    # ========================================================

    if category == "growth":

        if comparison == "above":

            return {
                "gold": (
                    f"Actual {actual} lebih kuat dari Forecast "
                    f"{forecast}. Growth kuat dapat mengurangi "
                    "ekspektasi pelonggaran Fed."
                ),
                "usd": (
                    "USD berpotensi menguat."
                ),
                "yield": (
                    "Treasury Yield berpotensi naik."
                ),
                "bias": (
                    "🔴 BEARISH GOLD"
                ),
            }

        if comparison == "below":

            return {
                "gold": (
                    f"Actual {actual} lebih lemah dari Forecast "
                    f"{forecast}. Growth lemah dapat meningkatkan "
                    "ekspektasi pelonggaran Fed."
                ),
                "usd": (
                    "USD berpotensi melemah."
                ),
                "yield": (
                    "Treasury Yield berpotensi turun."
                ),
                "bias": (
                    "🟢 BULLISH GOLD"
                ),
            }

    # ========================================================
    # FED
    # ========================================================

    if category == "fed":

        return {
            "gold": (
                "Reaksi Gold bergantung pada perubahan "
                "rate expectations dan guidance Fed."
            ),
            "usd": (
                "Hawkish Fed cenderung bullish USD; "
                "dovish Fed cenderung bearish USD."
            ),
            "yield": (
                "Hawkish Fed cenderung menaikkan Yield; "
                "dovish Fed cenderung menurunkannya."
            ),
            "bias": (
                "🟡 ANALISIS GUIDANCE FED"
            ),
        }

    return {
        "gold": (
            "Reaksi XAUUSD bergantung pada detail "
            "Actual versus ekspektasi pasar."
        ),
        "usd": (
            "Pantau reaksi USD."
        ),
        "yield": (
            "Pantau Treasury Yield."
        ),
        "bias": (
            "🟡 NEUTRAL"
        ),
    }


# ============================================================
# COUNTDOWN
# ============================================================

def countdown(
    event_datetime
):

    if not event_datetime:
        return None

    now = datetime.now(
        WITA
    )

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

    secs = (
        seconds % 60
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


# ============================================================
# GET CALENDAR EVENTS
# ============================================================

def get_calendar_events(
    hours_ahead=48
):

    raw_events = fetch_calendar()

    if not raw_events:

        logger.info(
            "[CALENDAR] Gold events after filter: 0"
        )

        return []

    events = parse_events(
        raw_events
    )

    logger.info(
        "[CALENDAR] Gold events after filter: %s",
        len(events)
    )

    now = datetime.now(
        WITA
    )

    end_time = (
        now
        + timedelta(
            hours=hours_ahead
        )
    )

    upcoming = []

    for event in events:

        event_datetime = event.get(
            "datetime"
        )

        if not event_datetime:
            continue

        if event_datetime < now:
            continue

        if event_datetime > end_time:
            continue

        event["countdown"] = countdown(
            event_datetime
        )

        upcoming.append(
            event
        )

    upcoming.sort(
        key=lambda x: x["datetime"]
    )

    logger.info(
        "[CALENDAR] Gold events within %.1f hours: %s",
        hours_ahead,
        len(upcoming)
    )

    for event in upcoming:

        logger.info(
            "[CALENDAR] Upcoming: %s | %s | %s | Countdown: %s",
            event.get("event"),
            event.get("currency"),
            event.get("datetime"),
            event.get("countdown")
        )

    return upcoming


# ============================================================
# EVENT ID
# ============================================================

def get_event_id(
    event
):

    event_datetime = event.get(
        "datetime"
    )

    return "|".join([
        clean_text(
            event.get(
                "event",
                ""
            )
        ).lower(),

        clean_text(
            event.get(
                "currency",
                ""
            )
        ).upper(),

        str(
            event_datetime
        ),
    ])


# ============================================================
# FORMAT TELEGRAM
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

    actual = (
        event.get(
            "actual",
            ""
        )
        or "-"
    )

    forecast = (
        event.get(
            "forecast",
            ""
        )
        or "-"
    )

    previous = (
        event.get(
            "previous",
            ""
        )
        or "-"
    )

    if result:

        header = (
            "🚨 <b>GOLD EVENT RESULT</b>"
        )

    else:

        header = (
            "⏰ <b>GOLD ECONOMIC EVENT</b>"
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

        countdown_text = (
            event.get(
                "countdown"
            )
            or countdown(
                event_datetime
            )
            or "-"
        )

        message += (
            f"⏳ <b>EVENT DALAM:</b> "
            f"{countdown_text}\n\n"
        )

    message += (
        "━━━━━━━━━━━━━━━━━━\n\n"

        "📌 <b>DATA EVENT</b>\n\n"

        f"Forecast: {forecast}\n"
        f"Previous: {previous}\n"
        f"Actual: {actual}\n\n"

        "━━━━━━━━━━━━━━━━━━\n\n"

        "🧠 <b>FUNDAMENTAL ANALYSIS</b>\n\n"

        "🟡 <b>GOLD</b>\n"
        f"{analysis['gold']}\n\n"

        "💵 <b>USD</b>\n"
        f"{analysis['usd']}\n\n"

        "📈 <b>TREASURY YIELD</b>\n"
        f"{analysis['yield']}\n\n"

        f"🎯 <b>FUNDAMENTAL BIAS</b>\n"
        f"{analysis['bias']}\n\n"

        "⚠️ <b>TRADING</b>\n"
        "Hindari entry tepat sebelum high-impact "
        "release. Tunggu reaksi awal XAUUSD dan "
        "konfirmasi price action."
    )

    return message

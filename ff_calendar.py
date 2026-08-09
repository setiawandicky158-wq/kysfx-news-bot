import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests


# ============================================================
# CONFIG
# ============================================================

# Forex Factory / Fair Economy calendar JSON feed.
# Tidak memakai halaman HTML Forex Factory sehingga menghindari
# HTTP 403 dari halaman calendar.
CALENDAR_URL = (
    "https://nfs.faireconomy.media/"
    "ff_calendar_thisweek.json"
)

WITA = ZoneInfo("Asia/Makassar")

REQUEST_TIMEOUT = 20

# Hanya event HIGH IMPACT
HIGH_IMPACT_ONLY = True


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
)


# ============================================================
# GOLD EVENTS
# ============================================================

GOLD_KEYWORDS = [

    # --------------------------------------------------------
    # INFLATION
    # --------------------------------------------------------

    "cpi",
    "core cpi",
    "ppi",
    "core ppi",
    "pce",
    "core pce",
    "inflation",

    # --------------------------------------------------------
    # EMPLOYMENT
    # --------------------------------------------------------

    "non-farm",
    "nonfarm",
    "non-farm payrolls",
    "nonfarm payrolls",
    "payroll",
    "employment change",
    "unemployment rate",
    "unemployment claims",
    "jobless claims",
    "initial jobless claims",
    "adp non-farm",
    "adp nonfarm",
    "jolts",
    "job openings",
    "average hourly earnings",
    "hourly earnings",
    "employment",

    # --------------------------------------------------------
    # FED
    # --------------------------------------------------------

    "federal funds rate",
    "interest rate decision",
    "fed interest rate",
    "fomc",
    "fed chair",
    "powell",
    "fomc member",
    "fed member",
    "fed speaks",
    "fed speech",

    # --------------------------------------------------------
    # US GROWTH
    # --------------------------------------------------------

    "gdp",
    "retail sales",
    "core retail sales",
    "ism manufacturing",
    "ism services",
    "ism manufacturing pmi",
    "ism services pmi",
    "consumer confidence",
    "consumer sentiment",

    # --------------------------------------------------------
    # CHINA
    # --------------------------------------------------------

    "china cpi",
    "chinese cpi",
    "china ppi",
    "chinese ppi",
    "china inflation",

    # --------------------------------------------------------
    # MAJOR CENTRAL BANKS
    # --------------------------------------------------------

    "ecb interest rate",
    "ecb rate",
    "ecb press conference",

    "boj interest rate",
    "boj rate",
    "boj press conference",

    "boe interest rate",
    "boe rate",
    "boe press conference",

    "rba interest rate",
    "rba rate",
    "rba monetary policy",
    "rba press conference",

]


# ============================================================
# GOLD COUNTRIES
# ============================================================

# USD = primary Gold driver
# CNY = secondary macro driver
#
# AUD / EUR / GBP / JPY are included for major central-bank
# decisions because they can materially affect USD/risk sentiment.

GOLD_COUNTRIES = {
    "USD",
    "CNY",
    "AUD",
    "EUR",
    "GBP",
    "JPY",
}


# ============================================================
# TEXT CLEANER
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


# ============================================================
# PARSE NUMBER
# ============================================================

def clean_number(value):

    if value is None:
        return None

    value = clean_text(value)

    if not value:
        return None

    # Ambil angka pertama.
    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value.replace(",", "")
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
# COMPARE ACTUAL VS FORECAST
# ============================================================

def compare_actual_forecast(
    actual,
    forecast
):

    actual_number = clean_number(
        actual
    )

    forecast_number = clean_number(
        forecast
    )

    if (
        actual_number is None
        or forecast_number is None
    ):
        return "unknown"

    if actual_number > forecast_number:
        return "above"

    if actual_number < forecast_number:
        return "below"

    return "inline"


# ============================================================
# EVENT CATEGORY
# ============================================================

def event_category(event_name):

    name = clean_text(
        event_name
    ).lower()

    # Inflation
    if any(
        x in name
        for x in [
            "cpi",
            "ppi",
            "pce",
            "inflation",
        ]
    ):
        return "inflation"

    # Employment
    if any(
        x in name
        for x in [
            "payroll",
            "non-farm",
            "nonfarm",
            "employment",
            "unemployment",
            "jobless",
            "job openings",
            "jolts",
            "hourly earnings",
            "adp",
        ]
    ):
        return "employment"

    # Fed
    if any(
        x in name
        for x in [
            "federal funds",
            "interest rate",
            "fomc",
            "fed chair",
            "powell",
            "fed member",
            "fed speaks",
        ]
    ):
        return "fed"

    # Growth
    if any(
        x in name
        for x in [
            "gdp",
            "retail sales",
            "ism",
            "consumer confidence",
            "consumer sentiment",
        ]
    ):
        return "growth"

    # Central bank
    if any(
        x in name
        for x in [
            "ecb",
            "boj",
            "boe",
            "rba",
            "monetary policy",
        ]
    ):
        return "central_bank"

    # China
    if (
        "china" in name
        or "chinese" in name
    ):
        return "china"

    return "other"


# ============================================================
# GOLD RELEVANCE
# ============================================================

def is_gold_event(
    title,
    country,
    impact
):

    title_clean = clean_text(
        title
    )

    lower_title = (
        title_clean.lower()
    )

    country = clean_text(
        country
    ).upper()

    impact = clean_text(
        impact
    ).lower()

    # --------------------------------------------------------
    # HIGH IMPACT ONLY
    # --------------------------------------------------------

    if HIGH_IMPACT_ONLY:

        if impact != "high":
            return False

    # --------------------------------------------------------
    # COUNTRY FILTER
    # --------------------------------------------------------

    if country not in GOLD_COUNTRIES:
        return False

    # --------------------------------------------------------
    # KEYWORD FILTER
    # --------------------------------------------------------

    for keyword in GOLD_KEYWORDS:

        if keyword in lower_title:
            return True

    # --------------------------------------------------------
    # CENTRAL BANK FALLBACK
    # --------------------------------------------------------

    if (
        country in {
            "USD",
            "EUR",
            "GBP",
            "JPY",
            "AUD",
        }
        and any(
            x in lower_title
            for x in [
                "rate",
                "interest",
                "monetary policy",
                "press conference",
            ]
        )
    ):
        return True

    return False


# ============================================================
# NORMALIZE EVENT NAME
# ============================================================

def normalize_event_name(
    event_name
):

    name = clean_text(
        event_name
    )

    replacements = {

        "Non-Farm Employment Change":
            "NFP",

        "Nonfarm Employment Change":
            "NFP",

        "Non-Farm Payrolls":
            "NFP",

        "Nonfarm Payrolls":
            "NFP",

    }

    return replacements.get(
        name,
        name
    )


# ============================================================
# DATETIME
# ============================================================

def parse_event_datetime(
    value
):

    if not value:
        return None

    value = clean_text(
        value
    )

    # --------------------------------------------------------
    # ISO timestamp dari FF JSON
    # --------------------------------------------------------

    try:

        dt = datetime.fromisoformat(
            value
        )

        # Jika source memberikan timezone,
        # langsung convert ke WITA.

        if dt.tzinfo is not None:

            return dt.astimezone(
                WITA
            )

        return dt.replace(
            tzinfo=WITA
        )

    except ValueError:

        pass

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]

    for fmt in formats:

        try:

            dt = datetime.strptime(
                value,
                fmt
            )

            return dt.replace(
                tzinfo=WITA
            )

        except ValueError:

            continue

    return None


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

    secs = seconds % 60

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


# ============================================================
# FETCH CALENDAR JSON
# ============================================================

def fetch_calendar():

    logger.info(
        "[CALENDAR] Checking Forex Factory JSON feed..."
    )

    try:

        response = session.get(
            CALENDAR_URL,
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

        try:

            data = response.json()

        except ValueError:

            logger.error(
                "[CALENDAR] Invalid JSON response"
            )

            return []

        if not isinstance(
            data,
            list
        ):

            logger.error(
                "[CALENDAR] Unexpected JSON format"
            )

            return []

        logger.info(
            "[CALENDAR] Raw events received: %s",
            len(data)
        )

        return data

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
# PARSE CALENDAR
# ============================================================

def parse_calendar(
    data
):

    if not data:
        return []

    events = []

    for item in data:

        try:

            title = clean_text(
                item.get(
                    "title",
                    ""
                )
            )

            country = clean_text(
                item.get(
                    "country",
                    ""
                )
            ).upper()

            impact = clean_text(
                item.get(
                    "impact",
                    ""
                )
            )

            forecast = clean_text(
                item.get(
                    "forecast",
                    ""
                )
            )

            previous = clean_text(
                item.get(
                    "previous",
                    ""
                )
            )

            actual = clean_text(
                item.get(
                    "actual",
                    ""
                )
            )

            date_value = clean_text(
                item.get(
                    "date",
                    ""
                )
            )

            if not title:
                continue

            # ------------------------------------------------
            # GOLD FILTER
            # ------------------------------------------------

            if not is_gold_event(
                title,
                country,
                impact
            ):
                continue

            event_datetime = (
                parse_event_datetime(
                    date_value
                )
            )

            if not event_datetime:
                continue

            # ------------------------------------------------
            # EVENT
            # ------------------------------------------------

            events.append(
                {
                    "event":
                        normalize_event_name(
                            title
                        ),

                    "original_event":
                        title,

                    "currency":
                        country,

                    "impact":
                        impact,

                    "stars":
                        "⭐⭐⭐⭐⭐",

                    "datetime":
                        event_datetime,

                    "date":
                        event_datetime.strftime(
                            "%d-%m-%Y"
                        ),

                    "time":
                        event_datetime.strftime(
                            "%H:%M"
                        ),

                    "forecast":
                        forecast,

                    "previous":
                        previous,

                    "actual":
                        actual,
                }
            )

        except Exception as e:

            logger.warning(
                "[CALENDAR] Parse error: %s",
                e
            )

            continue

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    events.sort(
        key=lambda x: x[
            "datetime"
        ]
    )

    logger.info(
        "[CALENDAR] Gold events after filter: %s",
        len(events)
    )

    return events


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

    category = event_category(
        name
    )

    # ========================================================
    # PRE-EVENT
    # ========================================================

    if not actual:

        if category == "inflation":

            return {
                "gold":
                    "Actual belum dirilis. CPI/PPI/PCE yang lebih rendah dari Forecast secara umum mendukung Gold, sedangkan data lebih tinggi berpotensi menekan Gold.",

                "usd":
                    "Inflation lebih rendah dapat meningkatkan rate cut expectations dan menekan USD.",

                "yield":
                    "Inflation lebih rendah dapat menekan Treasury Yield.",

                "bias":
                    "🟡 NEUTRAL — MENUNGGU DATA",
            }

        if category == "employment":

            return {
                "gold":
                    "Actual belum dirilis. Employment yang lebih lemah dari Forecast cenderung mendukung Gold melalui potensi peningkatan rate cut expectations.",

                "usd":
                    "Employment yang lebih lemah dapat menekan USD.",

                "yield":
                    "Employment yang lebih lemah dapat menekan Treasury Yield.",

                "bias":
                    "🟡 NEUTRAL — MENUNGGU DATA",
            }

        if category == "fed":

            return {
                "gold":
                    "Fokus pada Fed guidance dan perubahan rate expectations. Dovish Fed cenderung mendukung Gold.",

                "usd":
                    "Hawkish Fed cenderung bullish USD; dovish Fed cenderung bearish USD.",

                "yield":
                    "Hawkish Fed cenderung menaikkan Treasury Yield; dovish Fed cenderung menurunkannya.",

                "bias":
                    "🟡 NEUTRAL — MENUNGGU FED",
            }

        if category == "growth":

            return {
                "gold":
                    "Growth yang lebih lemah dapat meningkatkan ekspektasi kebijakan Fed yang lebih dovish dan mendukung Gold.",

                "usd":
                    "Growth yang kuat cenderung mendukung USD.",

                "yield":
                    "Growth yang kuat dapat meningkatkan Treasury Yield.",

                "bias":
                    "🟡 NEUTRAL — MENUNGGU DATA",
            }

        if category == "central_bank":

            return {
                "gold":
                    "Fokus pada perubahan rate expectations, guidance, dan risk sentiment setelah keputusan central bank.",

                "usd":
                    "Perubahan rate expectations dapat memengaruhi USD dan cross-asset flows.",

                "yield":
                    "Perubahan ekspektasi suku bunga dapat memengaruhi Treasury Yield.",

                "bias":
                    "🟡 NEUTRAL — MENUNGGU KEPUTUSAN",
            }

        return {
            "gold":
                "Event berpotensi meningkatkan volatilitas Gold. Tunggu data dan reaksi market.",

            "usd":
                "Pantau reaksi USD.",

            "yield":
                "Pantau Treasury Yield.",

            "bias":
                "🟡 NEUTRAL",
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
                "gold":
                    f"Actual {actual} berada di bawah Forecast {forecast}. Inflation pressure lebih rendah dari ekspektasi dan cenderung mendukung Gold.",

                "usd":
                    "Rate cut expectations berpotensi meningkat sehingga USD berpotensi melemah.",

                "yield":
                    "Treasury Yield berpotensi turun.",

                "bias":
                    "🟢 BULLISH GOLD",
            }

        if comparison == "above":

            return {
                "gold":
                    f"Actual {actual} berada di atas Forecast {forecast}. Inflation pressure lebih tinggi dari ekspektasi dan berpotensi menekan Gold.",

                "usd":
                    "Higher-for-longer expectations berpotensi meningkat sehingga USD dapat menguat.",

                "yield":
                    "Treasury Yield berpotensi naik.",

                "bias":
                    "🔴 BEARISH GOLD",
            }

    # ========================================================
    # EMPLOYMENT
    # ========================================================

    if category == "employment":

        if comparison == "below":

            return {
                "gold":
                    f"Actual {actual} berada di bawah Forecast {forecast}. Employment lebih lemah dari ekspektasi dan cenderung mendukung Gold.",

                "usd":
                    "Rate cut expectations dapat meningkat sehingga USD berpotensi melemah.",

                "yield":
                    "Treasury Yield berpotensi turun.",

                "bias":
                    "🟢 BULLISH GOLD",
            }

        if comparison == "above":

            return {
                "gold":
                    f"Actual {actual} berada di atas Forecast {forecast}. Employment lebih kuat dari ekspektasi dan berpotensi menekan Gold.",

                "usd":
                    "USD berpotensi menguat.",

                "yield":
                    "Treasury Yield berpotensi naik.",

                "bias":
                    "🔴 BEARISH GOLD",
            }

    # ========================================================
    # GROWTH
    # ========================================================

    if category == "growth":

        if comparison == "above":

            return {
                "gold":
                    "Growth lebih kuat dari Forecast. Ekspektasi kebijakan Fed yang lebih hawkish dapat menekan Gold.",

                "usd":
                    "USD berpotensi menguat.",

                "yield":
                    "Treasury Yield berpotensi naik.",

                "bias":
                    "🔴 BEARISH GOLD",
            }

        if comparison == "below":

            return {
                "gold":
                    "Growth lebih lemah dari Forecast. Ekspektasi kebijakan Fed yang lebih dovish dapat mendukung Gold.",

                "usd":
                    "USD berpotensi melemah.",

                "yield":
                    "Treasury Yield berpotensi turun.",

                "bias":
                    "🟢 BULLISH GOLD",
            }

    # ========================================================
    # FED
    # ========================================================

    if category == "fed":

        return {
            "gold":
                "Fed event sudah dirilis. Analisis utama harus melihat rate expectations, guidance, dot plot jika tersedia, dan reaksi Treasury Yield.",

            "usd":
                "Hawkish Fed → USD cenderung bullish. Dovish Fed → USD cenderung bearish.",

            "yield":
                "Hawkish Fed → Treasury Yield cenderung naik. Dovish Fed → Treasury Yield cenderung turun.",

            "bias":
                "🟡 ANALISIS GUIDANCE FED",
        }

    # ========================================================
    # DEFAULT
    # ========================================================

    return {
        "gold":
            "Reaksi Gold bergantung pada detail data dan perubahan rate expectations.",

        "usd":
            "Pantau USD.",

        "yield":
            "Pantau Treasury Yield.",

        "bias":
            "🟡 NEUTRAL",
    }


# ============================================================
# GET UPCOMING GOLD EVENTS
# ============================================================

def get_calendar_events(
    hours_ahead=2
):

    data = fetch_calendar()

    if not data:
        return []

    events = parse_calendar(
        data
    )

    now = datetime.now(
        WITA
    )

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

        # ----------------------------------------------------
        # Hanya future events
        # ----------------------------------------------------

        if event_datetime <= now:
            continue

        # ----------------------------------------------------
        # Event dalam window
        # ----------------------------------------------------

        if event_datetime > end:
            continue

        event["countdown"] = countdown(
            event_datetime
        )

        valid_events.append(
            event
        )

    valid_events.sort(
        key=lambda x: x[
            "datetime"
        ]
    )

    logger.info(
        "[CALENDAR] Gold events within %.1f hours: %s",
        hours_ahead,
        len(valid_events)
    )

    for event in valid_events:

        logger.info(
            "[CALENDAR] Upcoming: %s | %s | %s WITA",
            event.get("event"),
            event.get("currency"),
            event.get("datetime").strftime(
                "%d-%m-%Y %H:%M"
            )
        )

    return valid_events


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

    if result:

        header = (
            "🚨 <b>GOLD EVENT RESULT</b>"
        )

    else:

        header = (
            "⏰ <b>GOLD ECONOMIC EVENT</b>"
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

    actual = (
        event.get(
            "actual",
            ""
        )
        or "-"
    )

    countdown_text = (
        event.get(
            "countdown",
            "-"
        )
    )

    message = (
        f"{header}\n\n"

        f"📊 <b>{event.get('event', '')}</b>\n"

        f"🌎 Currency: "
        f"{event.get('currency', '')}\n"

        f"🕐 Event: "
        f"{event_time} WITA\n\n"

        f"⚠️ <b>HIGH IMPACT</b> "
        f"{event.get('stars', '⭐⭐⭐⭐⭐')}\n\n"
    )

    if not result:

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
        "Tunggu reaksi awal XAUUSD dan "
        "konfirmasi price action sebelum entry."
    )

    return message


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        )
    )

    events = get_calendar_events(
        hours_ahead=48
    )

    print(
        "\nGold events:\n"
    )

    for event in events:

        print(
            event
        )

        print(
            "-" * 60
        )

import re
import time
import logging
from datetime import datetime, timedelta
from html import unescape
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIG
# ============================================================

FOREX_FACTORY_URL = "https://www.forexfactory.com/calendar"

WITA = ZoneInfo("Asia/Makassar")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.forexfactory.com/",
    "Connection": "keep-alive",
}

REQUEST_TIMEOUT = 30


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# GOLD RELEVANT EVENTS
# ============================================================

GOLD_EVENTS = {
    # US
    "CPI": "inflation",
    "Core CPI": "inflation",
    "PPI": "inflation",
    "Core PPI": "inflation",
    "PCE": "inflation",
    "Core PCE": "inflation",

    "Non-Farm Employment Change": "employment",
    "Nonfarm Payrolls": "employment",
    "Non-Farm Payrolls": "employment",
    "NFP": "employment",

    "Unemployment Rate": "employment",
    "Average Hourly Earnings": "employment",
    "ADP Non-Farm Employment Change": "employment",
    "JOLTS Job Openings": "employment",
    "Initial Jobless Claims": "employment",

    "Federal Funds Rate": "fed",
    "FOMC Statement": "fed",
    "FOMC Press Conference": "fed",
    "Fed Chair Powell Speaks": "fed",
    "Fed Chair Speaks": "fed",

    "GDP": "growth",
    "Retail Sales": "growth",
    "Core Retail Sales": "growth",
    "ISM Manufacturing PMI": "growth",
    "ISM Services PMI": "growth",
    "CB Consumer Confidence": "growth",
    "Michigan Consumer Sentiment": "growth",

    # China
    "Chinese CPI": "china_inflation",
    "Chinese PPI": "china_inflation",
    "China CPI": "china_inflation",
    "China PPI": "china_inflation",

    # Major central banks
    "ECB Interest Rate Decision": "central_bank",
    "ECB Press Conference": "central_bank",
    "BoJ Interest Rate Decision": "central_bank",
    "BoE Interest Rate Decision": "central_bank",
    "RBA Interest Rate Decision": "central_bank",
}


# ============================================================
# EVENT KEYWORD FALLBACK
# ============================================================

EVENT_KEYWORDS = [
    "cpi",
    "core cpi",
    "ppi",
    "core ppi",
    "pce",
    "core pce",
    "non-farm",
    "nonfarm",
    "payroll",
    "unemployment",
    "jobless claims",
    "jolts",
    "federal funds",
    "fomc",
    "fed chair",
    "powell",
    "retail sales",
    "gdp",
    "ism",
    "consumer confidence",
    "interest rate decision",
]


# ============================================================
# SESSION
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


# ============================================================
# TEXT
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = unescape(str(text))

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# NORMALIZE EVENT NAME
# ============================================================

def normalize_event_name(name):
    name = clean_text(name)

    replacements = {
        "Non-Farm Employment Change": "NFP",
        "Nonfarm Employment Change": "NFP",
        "Non-Farm Payrolls": "NFP",
        "Nonfarm Payrolls": "NFP",
        "Fed Interest Rate Decision": "Federal Funds Rate",
        "Federal Funds Rate": "Federal Funds Rate",
    }

    return replacements.get(name, name)


# ============================================================
# CHECK GOLD RELEVANCE
# ============================================================

def is_gold_event(event_name, currency, impact):
    name = clean_text(event_name)
    lower = name.lower()

    currency = clean_text(currency).upper()
    impact = clean_text(impact).lower()

    # Hanya high impact untuk economic-event alert
    if impact and "high" not in impact:
        return False

    # USD adalah prioritas utama
    if currency == "USD":
        for keyword in EVENT_KEYWORDS:
            if keyword in lower:
                return True

    # China
    if currency in ("CNY", "CNH"):
        if any(
            keyword in lower
            for keyword in ["cpi", "ppi", "inflation"]
        ):
            return True

    # Major central bank
    if any(
        keyword in lower
        for keyword in [
            "interest rate decision",
            "fomc",
            "fed chair",
            "powell",
        ]
    ):
        return True

    return False


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


# ============================================================
# DATETIME PARSER
# ============================================================

def parse_event_datetime(date_text, time_text):
    """
    Forex Factory biasanya menggunakan:
    date = YYYY-MM-DD / Today / Tomorrow
    time = 8:30am / 10:00am

    Parser dibuat fleksibel.
    """

    date_text = clean_text(date_text)
    time_text = clean_text(time_text)

    if not time_text:
        return None

    now = datetime.now(WITA)

    # Normalisasi waktu
    time_text = time_text.lower().replace(" ", "")

    # Jika jam berupa All Day / Tentative
    if time_text in {
        "all-day",
        "all day",
        "tentative",
        "day",
        "",
    }:
        return None

    # Hari relatif
    if date_text.lower() == "today":
        event_date = now.date()

    elif date_text.lower() == "tomorrow":
        event_date = (
            now + timedelta(days=1)
        ).date()

    else:
        parsed_date = None

        date_formats = [
            "%Y-%m-%d",
            "%m-%d-%Y",
            "%m/%d/%Y",
            "%b %d",
            "%B %d",
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(
                    date_text,
                    fmt
                )

                if "%Y" not in fmt:
                    parsed_date = parsed_date.replace(
                        year=now.year
                    )

                break

            except ValueError:
                continue

        if not parsed_date:
            return None

        event_date = parsed_date.date()

    # Parse time
    formats = [
        "%I:%M%p",
        "%I%p",
        "%H:%M",
    ]

    parsed_time = None

    for fmt in formats:
        try:
            parsed_time = datetime.strptime(
                time_text,
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
# FETCH FOREX FACTORY
# ============================================================

def fetch_calendar():
    logger.info(
        "[CALENDAR] Checking Forex Factory..."
    )

    try:
        response = session.get(
            FOREX_FACTORY_URL,
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

        return response.text

    except requests.exceptions.RequestException as e:
        logger.error(
            "[CALENDAR] Request error: %s",
            e
        )
        return ""

    except Exception as e:
        logger.exception(
            "[CALENDAR] Unexpected error: %s",
            e
        )
        return ""


# ============================================================
# PARSE CALENDAR
# ============================================================

def parse_calendar(html):
    if not html:
        return []

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    events = []

    # --------------------------------------------------------
    # Forex Factory calendar rows
    # --------------------------------------------------------

    rows = soup.select(
        "tr.calendar__row"
    )

    if not rows:
        rows = soup.select(
            "tr[class*='calendar']"
        )

    logger.info(
        "[CALENDAR] Calendar rows found: %s",
        len(rows)
    )

    current_date = None

    for row in rows:

        try:
            # ------------------------------------------------
            # DATE
            # ------------------------------------------------

            date_node = row.select_one(
                ".calendar__date"
            )

            if date_node:
                date_text = clean_text(
                    date_node.get_text(
                        " ",
                        strip=True
                    )
                )

                if date_text:
                    current_date = date_text

            if not current_date:
                date_text = clean_text(
                    row.get(
                        "data-date",
                        ""
                    )
                )

            else:
                date_text = current_date

            # ------------------------------------------------
            # TIME
            # ------------------------------------------------

            time_node = row.select_one(
                ".calendar__time"
            )

            time_text = ""

            if time_node:
                time_text = clean_text(
                    time_node.get_text(
                        " ",
                        strip=True
                    )
                )

            # ------------------------------------------------
            # CURRENCY
            # ------------------------------------------------

            currency_node = row.select_one(
                ".calendar__currency"
            )

            currency = ""

            if currency_node:
                currency = clean_text(
                    currency_node.get_text(
                        " ",
                        strip=True
                    )
                )

            # ------------------------------------------------
            # IMPACT
            # ------------------------------------------------

            impact_node = row.select_one(
                ".calendar__impact"
            )

            impact = ""

            if impact_node:

                title = clean_text(
                    impact_node.get(
                        "title",
                        ""
                    )
                )

                impact = title

                if not impact:
                    impact = clean_text(
                        impact_node.get_text(
                            " ",
                            strip=True
                        )
                    )

            # ------------------------------------------------
            # EVENT
            # ------------------------------------------------

            event_node = row.select_one(
                ".calendar__event"
            )

            if not event_node:
                event_node = row.select_one(
                    "[class*='calendar__event']"
                )

            event_name = ""

            if event_node:
                event_name = clean_text(
                    event_node.get_text(
                        " ",
                        strip=True
                    )
                )

            if not event_name:
                continue

            # ------------------------------------------------
            # FORECAST
            # ------------------------------------------------

            forecast_node = row.select_one(
                ".calendar__forecast"
            )

            forecast = ""

            if forecast_node:
                forecast = clean_text(
                    forecast_node.get_text(
                        " ",
                        strip=True
                    )
                )

            # ------------------------------------------------
            # PREVIOUS
            # ------------------------------------------------

            previous_node = row.select_one(
                ".calendar__previous"
            )

            previous = ""

            if previous_node:
                previous = clean_text(
                    previous_node.get_text(
                        " ",
                        strip=True
                    )
                )

            # ------------------------------------------------
            # ACTUAL
            # ------------------------------------------------

            actual_node = row.select_one(
                ".calendar__actual"
            )

            actual = ""

            if actual_node:
                actual = clean_text(
                    actual_node.get_text(
                        " ",
                        strip=True
                    )
                )

            # ------------------------------------------------
            # DATETIME
            # ------------------------------------------------

            event_datetime = parse_event_datetime(
                date_text,
                time_text
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

            events.append(
                {
                    "event": normalize_event_name(
                        event_name
                    ),
                    "original_event": event_name,
                    "currency": currency,
                    "impact": impact,
                    "stars": impact_stars(
                        impact
                    ),
                    "date": date_text,
                    "time": time_text,
                    "datetime": event_datetime,
                    "forecast": forecast,
                    "previous": previous,
                    "actual": actual,
                }
            )

        except Exception as e:

            logger.warning(
                "[CALENDAR] Row parse error: %s",
                e
            )

            continue

    return events


# ============================================================
# FUNDAMENTAL RULES
# ============================================================

def clean_number(value):
    if not value:
        return None

    value = (
        value
        .replace(",", "")
        .replace("%", "")
        .replace("$", "")
        .strip()
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
    name = event.get(
        "event",
        ""
    )

    actual = event.get(
        "actual",
        ""
    )

    forecast = event.get(
        "forecast",
        ""
    )

    category = ""

    lower = name.lower()

    if "cpi" in lower or "pce" in lower:
        category = "inflation"

    elif (
        "ppi" in lower
        or "producer" in lower
    ):
        category = "inflation"

    elif (
        "payroll" in lower
        or "nfp" in lower
        or "employment" in lower
        or "unemployment" in lower
        or "jobless" in lower
        or "jolts" in lower
        or "wage" in lower
    ):
        category = "employment"

    elif (
        "retail" in lower
        or "gdp" in lower
        or "ism" in lower
        or "consumer confidence" in lower
    ):
        category = "growth"

    elif (
        "fomc" in lower
        or "federal funds" in lower
        or "powell" in lower
        or "fed chair" in lower
        or "interest rate decision" in lower
    ):
        category = "fed"

    # ========================================================
    # PRE-EVENT
    # ========================================================

    if not actual:

        if category == "inflation":

            return {
                "gold": (
                    "Menunggu data CPI/PCE/PPI. "
                    "Actual di bawah Forecast cenderung "
                    "mendukung Gold."
                ),
                "usd": (
                    "Data inflation yang lebih rendah "
                    "dapat menekan USD."
                ),
                "yield": (
                    "Inflation yang lebih rendah dapat "
                    "menekan Treasury Yield."
                ),
                "bias": "🟡 NEUTRAL — MENUNGGU DATA",
            }

        if category == "employment":

            return {
                "gold": (
                    "Menunggu data employment. "
                    "Data lebih lemah dari Forecast "
                    "cenderung mendukung Gold."
                ),
                "usd": (
                    "Employment yang lebih lemah "
                    "dapat menekan USD."
                ),
                "yield": (
                    "Data employment lemah dapat "
                    "menekan Treasury Yield."
                ),
                "bias": "🟡 NEUTRAL — MENUNGGU DATA",
            }

        if category == "growth":

            return {
                "gold": (
                    "Data growth dapat mengubah "
                    "ekspektasi kebijakan Fed."
                ),
                "usd": (
                    "Growth yang kuat cenderung "
                    "mendukung USD."
                ),
                "yield": (
                    "Growth kuat dapat meningkatkan "
                    "Treasury Yield."
                ),
                "bias": "🟡 NEUTRAL — MENUNGGU DATA",
            }

        if category == "fed":

            return {
                "gold": (
                    "Fokus pada arah kebijakan Fed "
                    "dan perubahan rate expectations."
                ),
                "usd": (
                    "Hawkish Fed cenderung bullish USD."
                ),
                "yield": (
                    "Hawkish Fed cenderung menaikkan "
                    "Treasury Yield."
                ),
                "bias": "🟡 NEUTRAL — MENUNGGU FED",
            }

        return {
            "gold": (
                "Potensi volatilitas tinggi. "
                "Tunggu reaksi XAUUSD."
            ),
            "usd": "Tunggu reaksi USD.",
            "yield": "Pantau Treasury Yield.",
            "bias": "🟡 NEUTRAL",
        }

    # ========================================================
    # POST-EVENT
    # ========================================================

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
                    f"Actual {actual} berada di bawah "
                    f"Forecast {forecast}. "
                    "Inflation pressure lebih rendah."
                ),
                "usd": (
                    "Rate cut expectations berpotensi "
                    "meningkat sehingga USD berpotensi melemah."
                ),
                "yield": (
                    "Treasury Yield berpotensi turun."
                ),
                "bias": "🟢 BULLISH GOLD",
            }

        if comparison == "above":

            return {
                "gold": (
                    f"Actual {actual} berada di atas "
                    f"Forecast {forecast}. "
                    "Inflation pressure lebih tinggi."
                ),
                "usd": (
                    "Higher-for-longer expectations "
                    "berpotensi meningkat sehingga USD "
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
                    f"Actual {actual} berada di bawah "
                    f"Forecast {forecast}. "
                    "Employment menunjukkan pelemahan."
                ),
                "usd": (
                    "USD berpotensi melemah karena "
                    "rate cut expectations dapat meningkat."
                ),
                "yield": (
                    "Treasury Yield berpotensi turun."
                ),
                "bias": "🟢 BULLISH GOLD",
            }

        if comparison == "above":

            return {
                "gold": (
                    f"Actual {actual} berada di atas "
                    f"Forecast {forecast}. "
                    "Employment lebih kuat dari ekspektasi."
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
                    "Data growth lebih kuat dari Forecast. "
                    "Ekspektasi kebijakan Fed yang lebih hawkish "
                    "dapat menekan Gold."
                ),
                "usd": (
                    "USD berpotensi menguat."
                ),
                "yield": (
                    "Treasury Yield berpotensi naik."
                ),
                "bias": "🔴 BEARISH GOLD",
            }

        if comparison == "below":

            return {
                "gold": (
                    "Data growth lebih lemah dari Forecast. "
                    "Ekspektasi kebijakan Fed yang lebih dovish "
                    "dapat mendukung Gold."
                ),
                "usd": (
                    "USD berpotensi melemah."
                ),
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
                "Fed event telah dirilis. "
                "Analisis utama harus mempertimbangkan "
                "perubahan rate expectations dan guidance."
            ),
            "usd": (
                "Hawkish Fed → USD cenderung bullish. "
                "Dovish Fed → USD cenderung bearish."
            ),
            "yield": (
                "Hawkish Fed → Treasury Yield cenderung naik. "
                "Dovish Fed → Treasury Yield cenderung turun."
            ),
            "bias": "🟡 ANALISIS GUIDANCE FED",
        }

    return {
        "gold": "Reaksi Gold bergantung pada detail data.",
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

    delta = (
        event_datetime - now
    )

    seconds = int(
        delta.total_seconds()
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
# GET UPCOMING GOLD EVENTS
# ============================================================

def get_calendar_events(
    hours_ahead=48
):
    html = fetch_calendar()

    if not html:
        return []

    events = parse_calendar(
        html
    )

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
        "[CALENDAR] Gold events found: %s",
        len(valid_events)
    )

    return valid_events


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

    actual = event.get(
        "actual",
        ""
    ) or "-"

    forecast = event.get(
        "forecast",
        ""
    ) or "-"

    previous = event.get(
        "previous",
        ""
    ) or "-"

    countdown_text = event.get(
        "countdown",
        "-"
    )

    message = (
        f"{header}\n\n"

        f"📊 <b>{event.get('event', '')}</b>\n"
        f"🌎 {event.get('currency', '')}\n"
        f"🕐 {event_time} WITA\n\n"

        f"⚠️ <b>HIGH IMPACT NEWS</b> "
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

        f"🟡 <b>GOLD</b>\n"
        f"{analysis['gold']}\n\n"

        f"💵 <b>USD</b>\n"
        f"{analysis['usd']}\n\n"

        f"📈 <b>TREASURY YIELD</b>\n"
        f"{analysis['yield']}\n\n"

        f"🎯 <b>FUNDAMENTAL BIAS</b>\n"
        f"{analysis['bias']}\n\n"

        "⚠️ <b>TRADING</b>\n"
        "Tunggu reaksi awal XAUUSD dan "
        "konfirmasi price action sebelum entry."
    )

    return message

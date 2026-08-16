import hashlib
import html
import logging
import re
import time
from calendar import timegm
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests


logger = logging.getLogger("KYSFX.NEWS")


# ============================================================
# KYSFX NEWS ENGINE V5
# Context + Event + Causality + Direction + Confidence
# ============================================================

REQUEST_TIMEOUT = 20
TRANSLATION_TIMEOUT = 10

MAX_NEWS_AGE_HOURS = 36
MAX_RESULTS_PER_SOURCE = 30

MIN_RELEVANCE_SCORE = 10
DEFAULT_LIMIT = 10


# ============================================================
# NEWS SOURCES
# ============================================================

NEWS_FEEDS = [
    {
        "name": "Google News - Gold",
        "url": (
            "https://news.google.com/rss/search?"
            "q=gold+XAUUSD+gold+price+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 10,
    },
    {
        "name": "Google News - Fed USD",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Federal+Reserve+Fed+USD+dollar+"
            "interest+rates+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 10,
    },
    {
        "name": "Google News - Treasury Yield",
        "url": (
            "https://news.google.com/rss/search?"
            "q=US+Treasury+yields+10-year+yield+"
            "real+yields+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 9,
    },
    {
        "name": "Google News - US Macro",
        "url": (
            "https://news.google.com/rss/search?"
            "q=US+CPI+PCE+PPI+NFP+employment+"
            "GDP+ISM+retail+sales+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 10,
    },
    {
        "name": "Google News - Oil",
        "url": (
            "https://news.google.com/rss/search?"
            "q=WTI+crude+oil+OPEC+oil+prices+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 7,
    },
    {
        "name": "Google News - Geopolitics",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Iran+Israel+Middle+East+war+"
            "geopolitics+gold+oil+when:2d"
            "&hl=en-US&gl=US&ceid=US:en"
        ),
        "priority": 8,
    },
    {
        "name": "InvestingLive",
        "url": "https://investinglive.com/rss/",
        "priority": 10,
    },
]


# ============================================================
# KEYWORDS
# ============================================================

GOLD_KEYWORDS = {
    "gold": 5,
    "xau": 7,
    "xauusd": 9,
    "bullion": 4,
    "gold price": 8,
    "gold prices": 8,
    "gold futures": 7,
    "spot gold": 8,
    "precious metals": 4,
    "precious metal": 4,
    "safe haven": 4,
}


USD_KEYWORDS = {
    "usd": 5,
    "us dollar": 6,
    "u.s. dollar": 6,
    "dollar index": 8,
    "dxy": 8,
    "greenback": 5,
    "dollar": 2,
}


YIELD_KEYWORDS = {
    "treasury yield": 8,
    "treasury yields": 8,
    "10-year yield": 9,
    "10 year yield": 9,
    "10-year treasury": 8,
    "10 year treasury": 8,
    "real yield": 10,
    "real yields": 10,
    "bond yield": 6,
    "bond yields": 6,
    "yields": 3,
}


FED_KEYWORDS = {
    "federal reserve": 9,
    "fed": 4,
    "fomc": 12,
    "powell": 11,
    "fed chair": 10,
    "interest rate": 5,
    "interest rates": 5,
    "rate cut": 8,
    "rate cuts": 8,
    "rate hike": 8,
    "rate hikes": 8,
    "rate decision": 10,
    "monetary policy": 7,
}


INFLATION_KEYWORDS = {
    "cpi": 12,
    "core cpi": 12,
    "pce": 12,
    "core pce": 12,
    "ppi": 10,
    "inflation": 8,
    "consumer prices": 8,
    "producer prices": 8,
}


LABOR_KEYWORDS = {
    "nonfarm payrolls": 14,
    "non-farm payrolls": 14,
    "nfp": 14,
    "payrolls": 10,
    "jobs report": 11,
    "employment report": 10,
    "employment": 5,
    "unemployment": 8,
    "unemployment rate": 10,
    "jobless claims": 10,
    "initial claims": 10,
    "continuing claims": 8,
    "jolts": 9,
    "wages": 6,
    "average hourly earnings": 10,
}


MACRO_KEYWORDS = {
    "gdp": 10,
    "ism": 9,
    "pmi": 7,
    "retail sales": 10,
    "consumer confidence": 7,
    "consumer sentiment": 7,
    "durable goods": 7,
    "industrial production": 7,
    "manufacturing": 4,
}


OIL_KEYWORDS = {
    "crude oil": 8,
    "wti": 10,
    "brent": 7,
    "opec": 9,
    "opec+": 11,
    "oil prices": 8,
    "crude prices": 8,
    "oil inventories": 10,
    "eia": 9,
    "strategic petroleum reserve": 8,
}


GEOPOLITICAL_KEYWORDS = {
    "iran": 7,
    "israel": 5,
    "gaza": 5,
    "middle east": 8,
    "war": 5,
    "conflict": 5,
    "ceasefire": 7,
    "sanctions": 6,
    "missile": 6,
    "military": 5,
    "hormuz": 12,
    "strait of hormuz": 14,
    "red sea": 8,
    "ukraine": 5,
    "russia": 5,
    "tanker attack": 8,
    "shipping disruption": 8,
}


HIGH_IMPACT_KEYWORDS = {
    "fomc": 15,
    "fed decision": 15,
    "interest rate decision": 15,
    "rate decision": 13,
    "nfp": 15,
    "nonfarm payrolls": 15,
    "non-farm payrolls": 15,
    "cpi": 15,
    "pce": 15,
    "core pce": 15,
    "ppi": 12,
    "powell": 13,
    "federal reserve": 10,
    "jobless claims": 10,
    "retail sales": 9,
    "gdp": 9,
    "opec+": 12,
    "hormuz": 13,
    "strait of hormuz": 15,
}


# ============================================================
# DIRECT MARKET MOVEMENT
# ============================================================

USD_BULLISH = [
    "dollar rises",
    "dollar rose",
    "dollar gains",
    "dollar gained",
    "dollar strengthens",
    "dollar strengthened",
    "dollar climbs",
    "dollar climbed",
    "dollar jumps",
    "dollar jumped",
    "dollar firms",
    "dollar firmed",
    "usd rises",
    "usd gains",
    "usd strengthens",
    "dxy rises",
    "dxy gains",
    "dxy climbs",
    "dxy jumped",
    "dxy higher",
    "dxy strengthens",
]


USD_BEARISH = [
    "dollar falls",
    "dollar fell",
    "dollar drops",
    "dollar declined",
    "dollar weakens",
    "dollar weakened",
    "dollar slips",
    "dollar slipped",
    "dollar loses ground",
    "usd falls",
    "usd drops",
    "usd weakens",
    "dxy falls",
    "dxy drops",
    "dxy declines",
    "dxy slipped",
    "dxy lower",
    "dxy weakens",
]


YIELD_BULLISH = [
    "yields rise",
    "yields rose",
    "yield rises",
    "yield rose",
    "yields climb",
    "yield climbs",
    "yields higher",
    "yield higher",
    "yields jump",
    "yield jumps",
    "yields surged",
    "yield surged",
    "yields increase",
    "yield increases",
    "yield increased",
    "real yields rise",
    "real yield rises",
    "real yields higher",
]


YIELD_BEARISH = [
    "yields fall",
    "yields fell",
    "yield falls",
    "yield fell",
    "yields decline",
    "yield declines",
    "yields lower",
    "yield lower",
    "yields drop",
    "yield drops",
    "yields slipped",
    "yield slipped",
    "yields decrease",
    "yield decreases",
    "yield decreased",
    "real yields fall",
    "real yield falls",
    "real yields lower",
]


GOLD_BULLISH = [
    "gold rises",
    "gold rose",
    "gold gains",
    "gold gained",
    "gold advances",
    "gold advanced",
    "gold climbs",
    "gold climbed",
    "gold jumps",
    "gold jumped",
    "gold rallies",
    "gold rallied",
    "gold heads for a gain",
    "gold heads for weekly gain",
    "gold set for weekly gain",
    "gold poised for gains",
    "gold prices rise",
    "gold prices rose",
    "gold prices gain",
    "gold prices gained",
    "gold prices climb",
    "gold prices climbed",
    "gold prices advance",
    "gold prices advanced",
]


GOLD_BEARISH = [
    "gold falls",
    "gold fell",
    "gold drops",
    "gold dropped",
    "gold declines",
    "gold declined",
    "gold retreats",
    "gold retreated",
    "gold slips",
    "gold slipped",
    "gold loses ground",
    "gold prices fall",
    "gold prices fell",
    "gold prices drop",
    "gold prices dropped",
    "gold prices decline",
    "gold prices declined",
]


OIL_BULLISH = [
    "oil rises",
    "oil rose",
    "oil gains",
    "oil gained",
    "oil climbs",
    "oil climbed",
    "oil jumps",
    "oil jumped",
    "oil rallies",
    "oil rallied",
    "oil prices rise",
    "oil prices rose",
    "oil prices gain",
    "oil prices gained",
    "crude rises",
    "crude rose",
    "wti rises",
    "wti rose",
    "wti gains",
    "wti gained",
    "wti climbs",
    "wti climbed",
]


OIL_BEARISH = [
    "oil falls",
    "oil fell",
    "oil drops",
    "oil dropped",
    "oil declines",
    "oil declined",
    "oil retreats",
    "oil retreated",
    "oil slips",
    "oil slipped",
    "oil prices fall",
    "oil prices fell",
    "oil prices drop",
    "oil prices dropped",
    "crude falls",
    "crude fell",
    "wti falls",
    "wti fell",
    "wti drops",
    "wti dropped",
]


# ============================================================
# FED POLICY CONTEXT
# ============================================================

HAWKISH_TERMS = [
    "hawkish",
    "more hawkish",
    "hawkish stance",
    "higher for longer",
    "raise rates",
    "raises rates",
    "raising rates",
    "rate hikes are likely",
    "more rate hikes",
    "additional rate hikes",
    "further rate hikes",
    "tightening",
    "monetary tightening",
    "higher rates",
    "restrictive policy",
    "restrictive monetary",
    "restrictive stance",
]


DOVISH_TERMS = [
    "dovish",
    "more dovish",
    "dovish stance",
    "rate cuts are likely",
    "more rate cuts",
    "additional rate cuts",
    "further rate cuts",
    "cut rates",
    "cuts rates",
    "cutting rates",
    "easing",
    "monetary easing",
    "lower rates",
    "accommodative",
    "accommodative policy",
]


RATE_HIKE_DOVISH_PATTERNS = [
    r"(?:rate|rates)\s+(?:hike|hikes|hike odds|hike expectations|hiking)\b[^.]{0,100}\b(?:fall|fell|falls|decline|declined|declines|drop|dropped|drops|slip|slipped|lower|lowered|reduce|reduced|decrease|decreased|cut|cuts|hit)\b",
    r"\b(?:fall|fell|falls|decline|declined|declines|drop|dropped|drops|slip|slipped|lower|lowered|reduce|reduced|decrease|decreased)\b[^.]{0,100}\b(?:rate|rates)\s+(?:hike|hikes|hiking)\b",
    r"\b(?:hit|blow|setback)\b[^.]{0,100}\b(?:fed\s+)?rate\s+hike\s+(?:odds|expectations|bets)\b",
    r"\b(?:lower|lowered|reduced|decreased|falling|declining)\b[^.]{0,100}\b(?:rate\s+hike|hike)\s+(?:odds|expectations|bets)\b",
    r"\b(?:fewer|less)\s+(?:rate\s+)?hikes?\b",
    r"\b(?:odds|expectations|bets)\s+(?:of|for)\s+(?:a\s+)?rate\s+hike\s+(?:fall|fell|falls|decline|declined|drop|dropped|slip|slipped|lower|reduced|decrease)\b",
]


RATE_HIKE_HAWKISH_PATTERNS = [
    r"(?:rate|rates)\s+(?:hike|hikes|hiking)\b[^.]{0,100}\b(?:rise|rose|rises|increase|increased|increases|jump|jumped|jumps|higher|boost|boosted|strengthen|strengthened)\b",
    r"\b(?:rise|rose|rises|increase|increased|increases|jump|jumped|jumps|higher|boost|boosted)\b[^.]{0,100}\b(?:rate\s+hike|hike)\s+(?:odds|expectations|bets)\b",
    r"\b(?:higher|increased|increasing|rising|stronger)\b[^.]{0,100}\b(?:rate\s+hike|hike)\s+(?:odds|expectations|bets)\b",
    r"\b(?:more|additional|further)\s+(?:rate\s+)?hikes?\b",
]


RATE_CUT_DOVISH_PATTERNS = [
    r"(?:rate|rates)\s+(?:cut|cuts|cutting)\b[^.]{0,100}\b(?:rise|rose|rises|increase|increased|increases|jump|jumped|higher|boost|boosted)\b",
    r"\b(?:rise|rose|rises|increase|increased|increases|jump|jumped|higher)\b[^.]{0,100}\b(?:rate\s+cut|cut)\s+(?:odds|expectations|bets)\b",
    r"\b(?:higher|increased|increasing|rising|stronger)\b[^.]{0,100}\b(?:rate\s+cut|cut)\s+(?:odds|expectations|bets)\b",
    r"\b(?:more|additional|further)\s+(?:rate\s+)?cuts?\b",
]


RATE_CUT_HAWKISH_PATTERNS = [
    r"(?:rate|rates)\s+(?:cut|cuts|cutting)\b[^.]{0,100}\b(?:fall|fell|falls|decline|declined|drop|dropped|slip|slipped|lower|reduced|decrease|decreased|hit)\b",
    r"\b(?:fall|fell|falls|decline|declined|drop|dropped|slip|slipped|lower|reduced|decrease|decreased)\b[^.]{0,100}\b(?:rate\s+cut|cut)\s+(?:odds|expectations|bets)\b",
    r"\b(?:fewer|less)\s+(?:rate\s+)?cuts?\b",
]


def _fed_policy_bias(text):
    """
    +1 = dovish
    -1 = hawkish
     0 = unclear

    "rate hike" alone is deliberately neutral.
    """

    dovish_score = 0
    hawkish_score = 0

    if _has_pattern(text, RATE_HIKE_DOVISH_PATTERNS):
        dovish_score += 4

    if _has_pattern(text, RATE_HIKE_HAWKISH_PATTERNS):
        hawkish_score += 4

    if _has_pattern(text, RATE_CUT_DOVISH_PATTERNS):
        dovish_score += 4

    if _has_pattern(text, RATE_CUT_HAWKISH_PATTERNS):
        hawkish_score += 4

    if _has_any(text, DOVISH_TERMS):
        dovish_score += 2

    if _has_any(text, HAWKISH_TERMS):
        hawkish_score += 2

    if dovish_score > hawkish_score:
        return 1

    if hawkish_score > dovish_score:
        return -1

    return 0


# ============================================================
# GEOPOLITICAL CONTEXT
# ============================================================

ESCALATION_TERMS = [
    "escalate",
    "escalates",
    "escalated",
    "escalating",
    "intensify",
    "intensifies",
    "intensified",
    "intensifying",
    "increase attacks",
    "increased attacks",
    "attacks increase",
    "attacks increased",
    "attack intensifies",
    "attacks intensify",
    "attack intensified",
    "attacks intensified",
    "attack escalates",
    "attacks escalate",
    "attack escalated",
    "attacks escalated",
    "strike intensifies",
    "strikes intensify",
    "strike intensified",
    "strikes intensified",
    "airstrikes intensify",
    "airstrikes intensified",
    "missile attacks intensify",
    "missile attacks intensified",
    "military escalation",
    "military escalation increases",
    "war escalates",
    "conflict escalates",
    "conflict intensified",
    "tensions rise",
    "tensions increase",
    "tensions escalate",
    "heightened tensions",
    "heightened geopolitical tensions",
    "renewed attacks",
    "renewed strikes",
    "new attacks",
    "new strikes",
    "tanker attacks",
    "tanker attack",
    "shipping disruption",
    "shipping disruptions",
    "shipping traffic declined",
    "shipping traffic falls",
]


DEESCALATION_TERMS = [
    "ceasefire",
    "cease-fire",
    "ceasefire agreement",
    "peace agreement",
    "peace deal",
    "peace talks progress",
    "talks progress",
    "de-escalation",
    "deescalation",
    "de-escalate",
    "deescalate",
    "de-escalates",
    "deescalates",
    "de-escalated",
    "deescalated",
    "tensions ease",
    "tensions eased",
    "tensions decline",
    "tensions declined",
    "tensions fall",
    "tensions fell",
    "attacks stop",
    "attacks halted",
    "attack halted",
    "strikes halted",
    "strikes stop",
    "military operations halted",
    "military operations stopped",
    "truce",
    "reopening",
    "reopen",
    "reopens",
    "reopened",
    "hormuz reopens",
    "hormuz reopened",
    "strait reopens",
    "strait reopened",
    "shipping resumes",
    "shipping resumed",
]


HORMUZ_CLOSED_TERMS = [
    "strait of hormuz closed",
    "strait of hormuz remains closed",
    "strait of hormuz stayed closed",
    "strait of hormuz shut",
    "strait of hormuz remains shut",
    "hormuz remains closed",
    "hormuz remains shut",
    "hormuz closure",
    "hormuz closures",
    "hormuz disruption",
    "hormuz disruptions",
    "hormuz blockade",
    "hormuz blocked",
    "hormuz partially closed",
    "shipping through hormuz declined",
    "shipping traffic through hormuz declined",
    "traffic through hormuz declined",
]


HORMUZ_REOPEN_TERMS = [
    "hormuz reopens",
    "hormuz reopened",
    "hormuz reopening",
    "strait reopens",
    "strait reopened",
    "strait reopening",
    "strait of hormuz reopens",
    "strait of hormuz reopened",
    "shipping resumes through hormuz",
    "shipping resumed through hormuz",
]


SAFE_HAVEN_TERMS = [
    "safe haven",
    "safe-haven",
    "risk-off",
    "risk off",
    "geopolitical tensions",
    "geopolitical uncertainty",
    "geopolitical risk",
    "flight to safety",
    "flight to safe havens",
    "investors seek safety",
    "investors seek safe havens",
]


# ============================================================
# DATA SURPRISE
# ============================================================

EVENT_PATTERNS = {
    "CPI": [
        "cpi",
        "consumer price index",
        "consumer prices",
    ],
    "PCE": [
        "pce",
        "personal consumption expenditures",
    ],
    "PPI": [
        "ppi",
        "producer price index",
        "producer prices",
    ],
    "NFP": [
        "nonfarm payrolls",
        "non-farm payrolls",
        "nfp",
        "payrolls",
        "jobs report",
    ],
    "UNEMPLOYMENT": [
        "unemployment rate",
        "unemployment",
    ],
    "JOBLESS_CLAIMS": [
        "jobless claims",
        "initial claims",
        "continuing claims",
    ],
    "GDP": [
        "gdp",
        "gross domestic product",
    ],
    "RETAIL_SALES": [
        "retail sales",
    ],
    "ISM": [
        "ism",
        "ism manufacturing",
        "ism services",
    ],
    "PMI": [
        "pmi",
        "pmi data",
    ],
}


def detect_event(text):
    text = text.lower()

    for event, patterns in EVENT_PATTERNS.items():
        if any(pattern in text for pattern in patterns):
            return event

    return None


def _parse_number(value):
    if value is None:
        return None

    value = value.replace(",", "").replace("%", "").strip()

    multiplier = 1

    if value.lower().endswith("k"):
        multiplier = 1000
        value = value[:-1]

    if value.lower().endswith("m"):
        multiplier = 1000000
        value = value[:-1]

    try:
        return float(value) * multiplier
    except Exception:
        return None


def extract_surprise(text, event):
    """
    Attempts to detect:
      actual vs forecast
      actual vs expected
      actual vs previous

    This is intentionally conservative.
    If numbers are ambiguous, return None.
    """

    if not event:
        return None

    text = text.lower()

    number = r"([-+]?\d+(?:\.\d+)?%?|[-+]?\d+(?:,\d+)?(?:\.\d+)?[km]?)"

    patterns = [
        rf"(?:actual|reported|came in at|rose to|fell to|was)\s*[:\-]?\s*{number}"
        rf".{{0,80}}?"
        rf"(?:forecast|expected|estimate|consensus)\s*[:\-]?\s*{number}",

        rf"{number}\s*(?:actual|reported)"
        rf".{{0,80}}?"
        rf"{number}\s*(?:forecast|expected|estimate|consensus)",

        rf"(?:actual|reported)\s*{number}"
        rf".{{0,80}}?"
        rf"(?:expected|forecast)\s*{number}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            continue

        groups = match.groups()

        if len(groups) >= 2:
            actual = _parse_number(groups[0])
            forecast = _parse_number(groups[1])

            if actual is not None and forecast is not None:
                difference = actual - forecast

                return {
                    "actual": actual,
                    "forecast": forecast,
                    "difference": difference,
                    "surprise": (
                        "ABOVE_EXPECTATIONS"
                        if difference > 0
                        else "BELOW_EXPECTATIONS"
                        if difference < 0
                        else "IN_LINE"
                    ),
                }

    return None


# ============================================================
# BLOCKED TITLES
# ============================================================

BLOCKED_TITLE_KEYWORDS = [
    "week ahead",
    "weekly preview",
    "weekly outlook",
    "newsquawk week ahead",
    "newsquawk weekly preview",
    "newsquawk weekly outlook",
    "events next week",
    "calendar next week",
    "coming week",
    "what to watch this week",
    "week in review",
]


# ============================================================
# NORMALIZE
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    value = html.unescape(str(value))

    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


# ============================================================
# DATE
# ============================================================

def parse_entry_datetime(entry):

    candidates = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created"),
    ]

    for value in candidates:
        if not value:
            continue

        try:
            parsed = parsedate_to_datetime(value)

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed.astimezone(timezone.utc)

        except Exception:
            pass

    for field in (
        "published_parsed",
        "updated_parsed",
    ):
        value = entry.get(field)

        if value:
            try:
                return datetime.fromtimestamp(
                    timegm(value),
                    tz=timezone.utc,
                )
            except Exception:
                pass

    return datetime.now(timezone.utc)


# ============================================================
# FEED
# ============================================================

def fetch_feed(source):

    name = source["name"]
    url = source["url"]

    logger.info("[NEWS] Fetching: %s", name)

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(compatible; KYSFX-NewsBot/5.0)"
                )
            },
        )

        response.raise_for_status()

        feed = feedparser.parse(response.content)

        entries = feed.entries[:MAX_RESULTS_PER_SOURCE]

        logger.info(
            "[NEWS] %s entries: %s",
            name,
            len(entries),
        )

        return entries

    except Exception as exc:
        logger.warning(
            "[NEWS] Source failed: %s | %s",
            name,
            exc,
        )

        return []


# ============================================================
# KEYWORD SCORE
# ============================================================

def keyword_score(text, keywords):

    score = 0
    matched = []

    text = text.lower()

    for keyword, weight in keywords.items():

        if keyword.lower() in text:
            score += weight
            matched.append(keyword)

    return score, matched


def _has_any(text, terms):
    return any(term in text for term in terms)


def _has_pattern(text, patterns):
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in patterns
    )


# ============================================================
# CATEGORY
# ============================================================

def detect_category(matches):

    priority = [
        ("Geopolitik", "geopolitics"),
        ("Bank Sentral", "fed"),
        ("Inflasi", "inflation"),
        ("Tenaga Kerja", "labor"),
        ("Energi", "oil"),
        ("Yield", "yield"),
        ("USD", "usd"),
        ("Gold", "gold"),
        ("Ekonomi AS", "macro"),
    ]

    for category, group in priority:
        if matches.get(group):
            return category

    return "Market"


# ============================================================
# RELEVANCE ENGINE V5
# ============================================================

def analyze_relevance(title, summary):

    text = f"{title} {summary}".lower()

    groups = {
        "gold": GOLD_KEYWORDS,
        "usd": USD_KEYWORDS,
        "yield": YIELD_KEYWORDS,
        "fed": FED_KEYWORDS,
        "inflation": INFLATION_KEYWORDS,
        "labor": LABOR_KEYWORDS,
        "macro": MACRO_KEYWORDS,
        "oil": OIL_KEYWORDS,
        "geopolitics": GEOPOLITICAL_KEYWORDS,
        "high_impact": HIGH_IMPACT_KEYWORDS,
    }

    scores = {}
    matches = {}

    for name, keywords in groups.items():
        score, found = keyword_score(text, keywords)

        scores[name] = score
        matches[name] = found

    score = sum(
        scores[group]
        for group in (
            "gold",
            "usd",
            "yield",
            "fed",
            "inflation",
            "labor",
            "macro",
            "oil",
            "geopolitics",
        )
    )

    score += scores["high_impact"]

    # Cross-market relationships
    if matches["gold"]:
        if matches["usd"]:
            score += 8
        if matches["yield"]:
            score += 10
        if matches["fed"]:
            score += 10
        if matches["inflation"]:
            score += 10
        if matches["labor"]:
            score += 10
        if matches["macro"]:
            score += 6
        if matches["geopolitics"]:
            score += 7

    if matches["fed"]:
        if matches["usd"]:
            score += 7
        if matches["yield"]:
            score += 8

    if matches["inflation"]:
        if matches["usd"]:
            score += 7
        if matches["yield"]:
            score += 8

    if matches["labor"]:
        if matches["usd"]:
            score += 7
        if matches["yield"]:
            score += 8

    if matches["geopolitics"]:
        if matches["gold"]:
            score += 10
        if matches["oil"]:
            score += 7

    if matches["oil"] and matches["gold"]:
        score += 5

    # Event detection bonus
    event = detect_event(text)

    if event:
        score += 5

    # Geopolitical escalation bonus
    if _has_any(text, ESCALATION_TERMS):
        score += 6

    # Hormuz-specific importance
    if _has_any(text, HORMUZ_CLOSED_TERMS):
        score += 8

    market_groups = sum(
        bool(matches[group])
        for group in (
            "gold",
            "usd",
            "yield",
            "fed",
            "inflation",
            "labor",
            "macro",
            "oil",
            "geopolitics",
        )
    )

    relevant = score >= MIN_RELEVANCE_SCORE

    if market_groups == 1:
        only_group = next(
            (
                group
                for group in (
                    "gold",
                    "usd",
                    "yield",
                    "fed",
                    "inflation",
                    "labor",
                    "macro",
                    "oil",
                    "geopolitics",
                )
                if matches[group]
            ),
            None,
        )

        if only_group in ("usd", "oil", "macro"):
            relevant = score >= 18

    return {
        "score": score,
        "relevant": relevant,
        "matches": matches,
        "scores": scores,
        "event": event,
    }


# ============================================================
# IMPACT
# ============================================================

def impact_level(score):

    if score >= 60:
        return "Critical Impact News", "⭐⭐⭐⭐⭐"

    if score >= 40:
        return "High Impact News", "⭐⭐⭐⭐⭐"

    if score >= 28:
        return "High Impact News", "⭐⭐⭐⭐"

    if score >= 18:
        return "Medium-High Impact", "⭐⭐⭐"

    if score >= 10:
        return "Market Impact", "⭐⭐"

    return "Low Impact", "⭐"


# ============================================================
# MACRO SURPRISE ANALYSIS
# ============================================================

def macro_surprise_bias(event, surprise):

    if not event or not surprise:
        return 0

    result = surprise["surprise"]

    # Positive economic surprise:
    # generally USD/yield bullish.
    #
    # But inflation is special:
    # higher inflation -> hawkish -> USD/Yield bullish -> Gold bearish.
    #
    # Labor:
    # stronger jobs -> USD/Yield bullish -> Gold bearish.
    #
    # Unemployment:
    # higher unemployment -> weaker labor -> dovish -> Gold bullish.

    if event in (
        "CPI",
        "PCE",
        "PPI",
    ):
        if result == "ABOVE_EXPECTATIONS":
            return -1

        if result == "BELOW_EXPECTATIONS":
            return 1

    if event in (
        "NFP",
        "GDP",
        "RETAIL_SALES",
        "ISM",
        "PMI",
    ):
        if result == "ABOVE_EXPECTATIONS":
            return -1

        if result == "BELOW_EXPECTATIONS":
            return 1

    if event == "UNEMPLOYMENT":
        if result == "ABOVE_EXPECTATIONS":
            return 1

        if result == "BELOW_EXPECTATIONS":
            return -1

    if event == "JOBLESS_CLAIMS":
        # Higher claims = weaker labor = dovish.
        if result == "ABOVE_EXPECTATIONS":
            return 1

        if result == "BELOW_EXPECTATIONS":
            return -1

    return 0


# ============================================================
# DIRECTION ENGINE V5
# ============================================================

def directional_analysis(title, summary):

    text = normalize_text(
        f"{title} {summary}"
    ).lower()

    gold_score = 0
    usd_score = 0
    yield_score = 0
    oil_score = 0

    reasons = []

    # --------------------------------------------------------
    # DIRECT GOLD
    # --------------------------------------------------------

    if _has_any(text, GOLD_BULLISH):
        gold_score += 4
        reasons.append("Gold price language is bullish.")

    if _has_any(text, GOLD_BEARISH):
        gold_score -= 4
        reasons.append("Gold price language is bearish.")

    # --------------------------------------------------------
    # DIRECT USD
    # --------------------------------------------------------

    if _has_any(text, USD_BULLISH):
        usd_score += 4
        reasons.append("USD/DXY is described as stronger.")

    if _has_any(text, USD_BEARISH):
        usd_score -= 4
        reasons.append("USD/DXY is described as weaker.")

    # --------------------------------------------------------
    # DIRECT YIELD
    # --------------------------------------------------------

    if _has_any(text, YIELD_BULLISH):
        yield_score += 4
        gold_score -= 2
        reasons.append("US yields are rising.")

    if _has_any(text, YIELD_BEARISH):
        yield_score -= 4
        gold_score += 2
        reasons.append("US yields are falling.")

    # Real yield receives stronger weight.
    if "real yields rise" in text or "real yield rises" in text:
        gold_score -= 2
        reasons.append("Real yields are rising.")

    if "real yields fall" in text or "real yield falls" in text:
        gold_score += 2
        reasons.append("Real yields are falling.")

    # --------------------------------------------------------
    # DIRECT OIL
    # --------------------------------------------------------

    if _has_any(text, OIL_BULLISH):
        oil_score += 4
        reasons.append("Oil price language is bullish.")

    if _has_any(text, OIL_BEARISH):
        oil_score -= 4
        reasons.append("Oil price language is bearish.")

    # --------------------------------------------------------
    # FED POLICY
    # --------------------------------------------------------

    policy_bias = _fed_policy_bias(text)

    if policy_bias > 0:
        usd_score -= 4
        yield_score -= 3
        gold_score += 5
        reasons.append(
            "Fed expectations/language are dovish."
        )

    elif policy_bias < 0:
        usd_score += 4
        yield_score += 3
        gold_score -= 5
        reasons.append(
            "Fed expectations/language are hawkish."
        )

    # --------------------------------------------------------
    # MACRO DATA SURPRISE
    # --------------------------------------------------------

    event = detect_event(text)
    surprise = extract_surprise(text, event)

    surprise_bias = macro_surprise_bias(
        event,
        surprise,
    )

    if surprise_bias > 0:
        usd_score -= 3
        yield_score -= 3
        gold_score += 4

        if surprise:
            reasons.append(
                f"{event} came in below expectations."
            )

    elif surprise_bias < 0:
        usd_score += 3
        yield_score += 3
        gold_score -= 4

        if surprise:
            reasons.append(
                f"{event} came in above expectations."
            )

    elif surprise and surprise["surprise"] == "IN_LINE":
        reasons.append(
            f"{event} was broadly in line with expectations."
        )

    # --------------------------------------------------------
    # GEOPOLITICAL ESCALATION
    # --------------------------------------------------------

    escalation = _has_any(
        text,
        ESCALATION_TERMS,
    )

    deescalation = _has_any(
        text,
        DEESCALATION_TERMS,
    )

    if escalation and not deescalation:
        gold_score += 5
        reasons.append(
            "Geopolitical risk is escalating."
        )

    elif deescalation and not escalation:
        gold_score -= 3
        reasons.append(
            "Geopolitical risk is easing."
        )

    # --------------------------------------------------------
    # HORMUZ
    # --------------------------------------------------------

    hormuz_closed = _has_any(
        text,
        HORMUZ_CLOSED_TERMS,
    )

    hormuz_reopen = _has_any(
        text,
        HORMUZ_REOPEN_TERMS,
    )

    if hormuz_closed and not hormuz_reopen:
        gold_score += 4
        oil_score += 5

        reasons.append(
            "Hormuz disruption raises geopolitical and supply risk."
        )

    if hormuz_reopen:
        gold_score -= 3
        oil_score -= 4

        reasons.append(
            "Hormuz reopening reduces supply/geopolitical risk."
        )

    # --------------------------------------------------------
    # SAFE HAVEN
    # --------------------------------------------------------

    if _has_any(text, SAFE_HAVEN_TERMS):
        gold_score += 4
        reasons.append(
            "Safe-haven demand supports Gold."
        )

    # --------------------------------------------------------
    # OIL -> INFLATION -> FED SECOND-ORDER EFFECT
    # --------------------------------------------------------

    if oil_score >= 4:
        inflation_pressure_terms = [
            "inflation risk",
            "inflationary pressure",
            "higher inflation",
            "energy inflation",
            "oil-driven inflation",
            "fuel prices rise",
            "energy prices rise",
        ]

        if _has_any(text, inflation_pressure_terms):
            gold_score -= 2
            usd_score += 2
            yield_score += 2

            reasons.append(
                "Higher energy prices may increase inflation pressure."
            )

    # --------------------------------------------------------
    # CROSS-MARKET CAUSALITY
    # --------------------------------------------------------

    # Strong USD normally pressures Gold.
    if usd_score >= 4 and gold_score <= 1:
        gold_score -= 2
        reasons.append(
            "Stronger USD is a headwind for XAUUSD."
        )

    if usd_score <= -4 and gold_score >= -1:
        gold_score += 2
        reasons.append(
            "Weaker USD supports XAUUSD."
        )

    # Strong yield normally pressures Gold.
    if yield_score >= 4 and gold_score <= 1:
        gold_score -= 2
        reasons.append(
            "Higher US yields are a headwind for XAUUSD."
        )

    if yield_score <= -4 and gold_score >= -1:
        gold_score += 2
        reasons.append(
            "Lower US yields support XAUUSD."
        )

    # --------------------------------------------------------
    # BIAS
    # --------------------------------------------------------

    def bias(score):
        if score >= 3:
            return "BULLISH"

        if score <= -3:
            return "BEARISH"

        return "NEUTRAL"

    gold = bias(gold_score)
    usd = bias(usd_score)
    yield_bias = bias(yield_score)
    oil = bias(oil_score)

    # --------------------------------------------------------
    # GOLD INFERENCE
    # --------------------------------------------------------

    if gold == "NEUTRAL":

        if usd == "BULLISH" and yield_bias == "BULLISH":
            gold = "BEARISH"

            reasons.append(
                "USD and yields both support a bearish Gold bias."
            )

        elif usd == "BEARISH" and yield_bias == "BEARISH":
            gold = "BULLISH"

            reasons.append(
                "USD and yields both support a bullish Gold bias."
            )

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    absolute_score = abs(gold_score)

    explicit_signals = sum(
        [
            1 if _has_any(text, GOLD_BULLISH + GOLD_BEARISH) else 0,
            1 if _has_any(text, USD_BULLISH + USD_BEARISH) else 0,
            1 if _has_any(text, YIELD_BULLISH + YIELD_BEARISH) else 0,
            1 if policy_bias != 0 else 0,
            1 if escalation != deescalation else 0,
            1 if hormuz_closed or hormuz_reopen else 0,
            1 if surprise is not None else 0,
        ]
    )

    if absolute_score >= 9 or explicit_signals >= 4:
        confidence = "HIGH"

    elif absolute_score >= 5 or explicit_signals >= 2:
        confidence = "MEDIUM"

    else:
        confidence = "LOW"

    # Neutral should rarely claim HIGH confidence.
    if gold == "NEUTRAL":
        confidence = "LOW" if explicit_signals < 3 else "MEDIUM"

    # --------------------------------------------------------
    # DEDUP REASONS
    # --------------------------------------------------------

    clean_reasons = []

    for reason in reasons:
        if reason not in clean_reasons:
            clean_reasons.append(reason)

    return {
        "gold": gold,
        "usd": usd,
        "yield": yield_bias,
        "oil": oil,
        "gold_score": gold_score,
        "usd_score": usd_score,
        "yield_score": yield_score,
        "oil_score": oil_score,
        "confidence": confidence,
        "reasons": clean_reasons[:8],
        "event": event,
        "policy_bias": policy_bias,
        "surprise": surprise,
        "geopolitical_escalation": escalation,
        "geopolitical_deescalation": deescalation,
        "hormuz_closed": hormuz_closed,
        "hormuz_reopen": hormuz_reopen,
    }


# ============================================================
# SOURCE
# ============================================================

def detect_source(entry, fallback):

    source = entry.get("source")

    if isinstance(source, dict):
        name = source.get("title")

        if name:
            return normalize_text(name)

    if isinstance(source, str):
        return normalize_text(source)

    return fallback


# ============================================================
# TITLE
# ============================================================

def clean_title(title):

    title = normalize_text(title)

    if not title:
        return ""

    parts = title.split(" - ")

    if len(parts) >= 2:

        last = parts[-1].strip()

        if len(last) < 80:
            title = " - ".join(parts[:-1])

    return title.strip()


# ============================================================
# SUMMARY
# ============================================================

def create_summary(title, summary):

    summary = normalize_text(summary)

    if not summary:
        return title[:600]

    sentences = re.split(
        r"(?<=[.!?])\s+",
        summary,
    )

    sentences = [
        x.strip()
        for x in sentences
        if x.strip()
    ]

    if not sentences:
        return summary[:700]

    return " ".join(sentences[:3])[:700]


# ============================================================
# NEWS ID
# ============================================================

def make_news_id(title, url):

    raw = (
        normalize_text(title).lower()
        + "|"
        + normalize_text(url).lower()
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:24]


# ============================================================
# PROCESS ENTRY
# ============================================================

def process_entry(entry, source):

    title = clean_title(
        entry.get("title", "")
    )

    if not title:
        return None

    summary = normalize_text(
        entry.get(
            "summary",
            entry.get(
                "description",
                "",
            ),
        )
    )

    url = normalize_text(
        entry.get("link", "")
    )

    published = parse_entry_datetime(entry)

    now = datetime.now(timezone.utc)

    age = now - published

    if age > timedelta(hours=MAX_NEWS_AGE_HOURS):
        return None

    if age < timedelta(minutes=-10):
        return None

    title_lower = title.lower()

    for blocked in BLOCKED_TITLE_KEYWORDS:
        if blocked in title_lower:
            return None

    analysis = analyze_relevance(
        title,
        summary,
    )

    if not analysis["relevant"]:
        return None

    category = detect_category(
        analysis["matches"]
    )

    impact, stars = impact_level(
        analysis["score"]
    )

    direction = directional_analysis(
        title,
        summary,
    )

    source_name = detect_source(
        entry,
        source,
    )

    news_id = make_news_id(
        title,
        url,
    )

    return {
        "id": news_id,
        "title": title,
        "summary": summary,
        "url": url,
        "source": source_name,
        "published": published,
        "score": analysis["score"],
        "impact": impact,
        "stars": stars,
        "category": category,
        "matches": analysis["matches"],
        "event": analysis["event"],
        "direction": direction,
    }


# ============================================================
# FETCH ALL
# ============================================================

def fetch_all_news():

    collected = []

    for source in sorted(
        NEWS_FEEDS,
        key=lambda x: x["priority"],
        reverse=True,
    ):

        entries = fetch_feed(source)

        for entry in entries:

            try:

                item = process_entry(
                    entry,
                    source["name"],
                )

                if item:
                    collected.append(item)

            except Exception as exc:

                logger.warning(
                    "[NEWS] Entry error: %s",
                    exc,
                )

    return collected


# ============================================================
# DEDUP
# ============================================================

def normalize_title_for_dedup(title):

    title = title.lower()

    title = re.sub(
        r"[^a-z0-9]+",
        " ",
        title,
    )

    stopwords = {
        "the",
        "a",
        "an",
        "to",
        "of",
        "for",
        "and",
        "on",
        "in",
        "as",
        "with",
        "after",
        "before",
    }

    words = [
        word
        for word in title.split()
        if word not in stopwords
    ]

    return " ".join(words)


def title_similarity(title_a, title_b):

    words_a = set(
        normalize_title_for_dedup(
            title_a
        ).split()
    )

    words_b = set(
        normalize_title_for_dedup(
            title_b
        ).split()
    )

    if not words_a or not words_b:
        return 0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def deduplicate_news(news):

    unique = []

    for item in news:

        duplicate = False

        for existing in unique:

            if (
                item["url"]
                and existing["url"]
                and item["url"] == existing["url"]
            ):
                duplicate = True
                break

            similarity = title_similarity(
                item["title"],
                existing["title"],
            )

            if similarity >= 0.72:

                duplicate = True

                if item["score"] > existing["score"]:
                    existing.clear()
                    existing.update(item)

                break

        if not duplicate:
            unique.append(item)

    return unique


# ============================================================
# SORT
# ============================================================

def sort_news(news):

    return sorted(
        news,
        key=lambda item: (
            item["score"],
            item["published"],
        ),
        reverse=True,
    )


# ============================================================
# PUBLIC API
# ============================================================

def get_news(limit=DEFAULT_LIMIT):

    logger.info(
        "[NEWS] Starting KYSFX News Engine V5..."
    )

    started = time.time()

    news = fetch_all_news()

    logger.info(
        "[NEWS] Relevant before dedup: %s",
        len(news),
    )

    news = deduplicate_news(news)

    news = sort_news(news)

    news = news[:limit]

    elapsed = time.time() - started

    logger.info(
        "[NEWS] Final results: %s | %.2fs",
        len(news),
        elapsed,
    )

    return news


# ============================================================
# TRANSLATION
# ============================================================

def translate_to_indonesian(text):

    if not text:
        return ""

    try:

        response = requests.get(
            "https://translate.googleapis.com/"
            "translate_a/single",
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": "id",
                "dt": "t",
                "q": text[:4500],
            },
            timeout=TRANSLATION_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        result = ""

        for item in data[0]:

            if item and item[0]:
                result += item[0]

        return normalize_text(result)

    except Exception as exc:

        logger.warning(
            "[NEWS] Translation failed: %s",
            exc,
        )

        return text


# ============================================================
# TELEGRAM HELPERS
# ============================================================

def direction_text(direction):

    return {
        "BULLISH": "🟢 Bullish",
        "BEARISH": "🔴 Bearish",
        "NEUTRAL": "⚪ Neutral",
    }.get(
        direction,
        "⚪ Neutral",
    )


def confidence_text(confidence):

    return {
        "HIGH": "🟢 HIGH",
        "MEDIUM": "🟡 MEDIUM",
        "LOW": "⚪ LOW",
    }.get(
        confidence,
        "⚪ LOW",
    )


def gold_conclusion(direction, confidence):

    if direction == "BULLISH":

        return (
            "Cenderung <b>BULLISH</b> untuk XAUUSD "
            f"dengan confidence <b>{confidence}</b>."
        )

    if direction == "BEARISH":

        return (
            "Cenderung <b>BEARISH</b> untuk XAUUSD "
            f"dengan confidence <b>{confidence}</b>."
        )

    return (
        "Dampak terhadap XAUUSD belum memiliki "
        f"arah yang cukup kuat. Confidence <b>{confidence}</b>."
    )


def analysis_reason_text(direction):

    reasons = direction.get(
        "reasons",
        [],
    )

    if not reasons:
        return "Tidak ada katalis dominan yang terdeteksi."

    return "\n".join(
        f"• {html.escape(reason)}"
        for reason in reasons[:6]
    )


# ============================================================
# TELEGRAM FORMATTER V5
# ============================================================

def format_news_message(
    item,
    translate=True,
):

    title = item["title"]

    summary = create_summary(
        title,
        item["summary"],
    )

    if translate:

        title = translate_to_indonesian(
            title
        )

        summary = translate_to_indonesian(
            summary
        )

    direction = item["direction"]

    gold = direction["gold"]
    usd = direction["usd"]
    yield_bias = direction["yield"]
    oil = direction["oil"]

    confidence = direction.get(
        "confidence",
        "LOW",
    )

    event = direction.get(
        "event"
    )

    event_text = (
        event.replace("_", " ")
        if event
        else "Market"
    )

    message = (
        "🚨 <b>BREAKING NEWS</b>\n\n"

        f"📂 <b>{html.escape(item['category'])}</b>\n"

        f"📰 <b>{html.escape(title)}</b>\n\n"

        f"⚠️ <b>{html.escape(item['impact'])}</b> "
        f"{item['stars']}\n\n"

        f"📝 {html.escape(summary)}\n\n"

        "🥇 <b>GOLD / XAUUSD</b>\n"
        f"{direction_text(gold)}\n\n"

        "💵 <b>USD</b>\n"
        f"{direction_text(usd)}\n\n"

        "📈 <b>US YIELD</b>\n"
        f"{direction_text(yield_bias)}\n\n"

        "🛢️ <b>OIL / WTI</b>\n"
        f"{direction_text(oil)}\n\n"

        "🧠 <b>ANALISIS</b>\n"
        f"{analysis_reason_text(direction)}\n\n"

        "🎯 <b>CONFIDENCE</b>\n"
        f"{confidence_text(confidence)}\n\n"

        "📌 <b>DAMPAK XAUUSD</b>\n"
        f"{gold_conclusion(gold, confidence)}\n\n"

        f"🔎 <b>Event:</b> "
        f"{html.escape(event_text)}\n"

        f"📊 <b>News Score:</b> "
        f"{item['score']}\n"

        f"📰 <b>Sumber:</b> "
        f"{html.escape(item['source'])}\n\n"

        f"🔗 <a href=\""
        f"{html.escape(item['url'])}"
        f"\">Baca berita</a>"
    )

    return message


# ============================================================
# DEBUG / TEST
# ============================================================

def print_debug_item(item):

    direction = item["direction"]

    print()
    print("=" * 90)

    print(
        f"TITLE      : {item['title']}"
    )

    print(
        f"SCORE      : {item['score']}"
    )

    print(
        f"IMPACT     : "
        f"{item['impact']} "
        f"{item['stars']}"
    )

    print(
        f"CATEGORY   : {item['category']}"
    )

    print(
        f"EVENT      : "
        f"{direction.get('event')}"
    )

    print(
        f"GOLD       : "
        f"{direction['gold']}"
    )

    print(
        f"USD        : "
        f"{direction['usd']}"
    )

    print(
        f"YIELD      : "
        f"{direction['yield']}"
    )

    print(
        f"OIL        : "
        f"{direction['oil']}"
    )

    print(
        f"CONFIDENCE : "
        f"{direction['confidence']}"
    )

    print(
        f"GOLD SCORE : "
        f"{direction['gold_score']}"
    )

    print(
        f"USD SCORE  : "
        f"{direction['usd_score']}"
    )

    print(
        f"YIELD SCORE: "
        f"{direction['yield_score']}"
    )

    print(
        f"OIL SCORE  : "
        f"{direction['oil_score']}"
    )

    print(
        "REASONS:"
    )

    for reason in direction.get(
        "reasons",
        [],
    ):
        print(
            f"  - {reason}"
        )

    print(
        f"SOURCE     : {item['source']}"
    )

    print(
        f"URL        : {item['url']}"
    )


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )

    results = get_news(
        limit=10
    )

    print()
    print("=" * 90)
    print(
        f"KYSFX NEWS ENGINE V5 | FINAL NEWS: {len(results)}"
    )
    print("=" * 90)

    for item in results:
        print_debug_item(item)

        print()
        print("TELEGRAM PREVIEW:")
        print("-" * 90)

        print(
            format_news_message(
                item,
                translate=False,
            )
        )

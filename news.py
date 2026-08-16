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
# SETTINGS
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
    "real yield": 9,
    "real yields": 9,
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
    "ceasefire": 6,
    "sanctions": 6,
    "missile": 6,
    "military": 5,
    "hormuz": 12,
    "strait of hormuz": 14,
    "red sea": 8,
    "ukraine": 5,
    "russia": 5,
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
# DIRECTION TERMS
# ============================================================

USD_BULLISH = [
    "dollar rises", "dollar rose", "dollar gains",
    "dollar gained", "dollar strengthens",
    "dollar strengthened", "dollar climbs",
    "dollar climbed", "dollar jumps",
    "dollar jumped", "dollar firms",
    "dollar firmed", "usd rises",
    "usd gains", "usd strengthens",
    "dxy rises", "dxy gains",
    "dxy climbs", "dxy jumped",
    "dollar strengthens on",
]

USD_BEARISH = [
    "dollar falls", "dollar fell", "dollar drops",
    "dollar declined", "dollar weakens",
    "dollar weakened", "dollar slips",
    "dollar slipped", "dollar loses ground",
    "usd falls", "usd drops",
    "usd weakens", "dxy falls",
    "dxy drops", "dxy declines",
    "dxy slipped",
]

YIELD_BULLISH = [
    "yields rise", "yields rose",
    "yield rises", "yield rose",
    "yields climb", "yield climbs",
    "yields higher", "yield higher",
    "yields jump", "yield jumps",
    "yields surged", "yield surged",
    "yields increase", "yield increases",
    "yield increased",
]

YIELD_BEARISH = [
    "yields fall", "yields fell",
    "yield falls", "yield fell",
    "yields decline", "yield declines",
    "yields lower", "yield lower",
    "yields drop", "yield drops",
    "yields slipped", "yield slipped",
    "yields decrease", "yield decreases",
    "yield decreased",
]

GOLD_BULLISH = [
    "gold rises", "gold rose", "gold gains",
    "gold gained", "gold advances",
    "gold advanced", "gold climbs",
    "gold climbed", "gold jumps",
    "gold jumped", "gold rallies",
    "gold rallied", "gold prices rise",
    "gold prices rose", "gold prices gain",
    "gold prices gained", "gold prices climb",
    "gold prices climbed", "gold prices advance",
    "gold prices advanced",
]

GOLD_BEARISH = [
    "gold falls", "gold fell", "gold drops",
    "gold dropped", "gold declines",
    "gold declined", "gold retreats",
    "gold retreated", "gold slips",
    "gold slipped", "gold loses ground",
    "gold prices fall", "gold prices fell",
    "gold prices drop", "gold prices dropped",
    "gold prices decline", "gold prices declined",
]

OIL_BULLISH = [
    "oil rises", "oil rose", "oil gains",
    "oil gained", "oil climbs", "oil climbed",
    "oil jumps", "oil jumped", "oil rallies",
    "oil rallied", "oil prices rise",
    "oil prices rose", "oil prices gain",
    "oil prices gained", "crude rises",
    "crude rose", "wti rises", "wti rose",
    "wti gains", "wti gained", "wti climbs",
    "wti climbed",
]

OIL_BEARISH = [
    "oil falls", "oil fell", "oil drops",
    "oil dropped", "oil declines", "oil declined",
    "oil retreats", "oil retreated", "oil slips",
    "oil slipped", "oil prices fall",
    "oil prices fell", "oil prices drop",
    "oil prices dropped", "crude falls",
    "crude fell", "wti falls", "wti fell",
    "wti drops", "wti dropped",
]


# ============================================================
# FED POLICY
# ============================================================

HAWKISH_TERMS = [
    "hawkish",
    "higher for longer",
    "raise rates",
    "raises rates",
    "raising rates",
    "more rate hikes",
    "additional rate hikes",
    "further rate hikes",
    "tightening",
    "higher rates",
    "restrictive policy",
    "restrictive monetary",
]

DOVISH_TERMS = [
    "dovish",
    "rate cuts are likely",
    "more rate cuts",
    "additional rate cuts",
    "further rate cuts",
    "cut rates",
    "cuts rates",
    "cutting rates",
    "easing",
    "lower rates",
    "accommodative",
    "monetary easing",
]

RATE_HIKE_DOVISH_PATTERNS = [
    r"(?:rate|rates)\s+(?:hike|hikes|hike odds|hike expectations|hiking)\b[^.]{0,100}\b(?:fall|fell|falls|decline|declined|declines|drop|dropped|drops|slip|slipped|lower|lowered|reduce|reduced|decrease|decreased|cut|cuts)\b",
    r"\b(?:fall|fell|falls|decline|declined|declines|drop|dropped|drops|slip|slipped|lower|lowered|reduce|reduced|decrease|decreased)\b[^.]{0,100}\b(?:rate|rates)\s+(?:hike|hikes|hiking)\b",
    r"\b(?:fewer|less)\s+(?:rate\s+)?hikes?\b",
]

RATE_HIKE_HAWKISH_PATTERNS = [
    r"(?:rate|rates)\s+(?:hike|hikes|hiking)\b[^.]{0,100}\b(?:rise|rose|rises|increase|increased|increases|jump|jumped|jumps|higher|boost|boosted|strengthen|strengthened)\b",
    r"\b(?:rise|rose|rises|increase|increased|increases|jump|jumped|jumps|higher|boost|boosted)\b[^.]{0,100}\b(?:rate\s+hike|hike)\s+(?:odds|expectations|bets)\b",
    r"\b(?:more|additional|further)\s+(?:rate\s+)?hikes?\b",
]

RATE_CUT_DOVISH_PATTERNS = [
    r"(?:rate|rates)\s+(?:cut|cuts|cutting)\b[^.]{0,100}\b(?:rise|rose|rises|increase|increased|increases|jump|jumped|higher|boost|boosted)\b",
    r"\b(?:more|additional|further)\s+(?:rate\s+)?cuts?\b",
]

RATE_CUT_HAWKISH_PATTERNS = [
    r"(?:rate|rates)\s+(?:cut|cuts|cutting)\b[^.]{0,100}\b(?:fall|fell|falls|decline|declined|drop|dropped|slip|slipped|lower|reduced|decrease|decreased|hit)\b",
    r"\b(?:fewer|less)\s+(?:rate\s+)?cuts?\b",
]


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
# HELPERS
# ============================================================

def _has_any(text, terms):
    return any(term.lower() in text for term in terms)


def _has_pattern(text, patterns):
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in patterns
    )


def normalize_text(value):
    if value is None:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


# ============================================================
# FED POLICY BIAS
# ============================================================

def _fed_policy_bias(text):
    """
    +1 = dovish
    -1 = hawkish
     0 = unclear
    """

    dovish = 0
    hawkish = 0

    if _has_pattern(text, RATE_HIKE_DOVISH_PATTERNS):
        dovish += 4

    if _has_pattern(text, RATE_HIKE_HAWKISH_PATTERNS):
        hawkish += 4

    if _has_pattern(text, RATE_CUT_DOVISH_PATTERNS):
        dovish += 4

    if _has_pattern(text, RATE_CUT_HAWKISH_PATTERNS):
        hawkish += 4

    if _has_any(text, DOVISH_TERMS):
        dovish += 2

    if _has_any(text, HAWKISH_TERMS):
        hawkish += 2

    if dovish > hawkish:
        return 1

    if hawkish > dovish:
        return -1

    return 0


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
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

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
# FETCH
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
                    "(compatible; KYSFX-NewsBot/6.0)"
                )
            },
        )

        response.raise_for_status()

        feed = feedparser.parse(
            response.content
        )

        entries = feed.entries[
            :MAX_RESULTS_PER_SOURCE
        ]

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


# ============================================================
# RELEVANCE
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

        score, found = keyword_score(
            text,
            keywords,
        )

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

        if only_group in (
            "usd",
            "oil",
            "macro",
        ):
            relevant = score >= 18

    return {
        "score": score,
        "relevant": relevant,
        "matches": matches,
        "scores": scores,
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
# DIRECTION ENGINE V6
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
    risks = []

    # --------------------------------------------------------
    # DIRECT MARKET MOVEMENT
    # --------------------------------------------------------

    if _has_any(text, GOLD_BULLISH):
        gold_score += 5
        reasons.append(
            "Harga Gold menunjukkan tekanan bullish."
        )

    if _has_any(text, GOLD_BEARISH):
        gold_score -= 5
        reasons.append(
            "Harga Gold menunjukkan tekanan bearish."
        )

    if _has_any(text, USD_BULLISH):
        usd_score += 5
        gold_score -= 3
        reasons.append(
            "USD menguat, yang biasanya memberikan tekanan "
            "terhadap XAUUSD."
        )

    if _has_any(text, USD_BEARISH):
        usd_score -= 5
        gold_score += 3
        reasons.append(
            "USD melemah, yang biasanya mendukung XAUUSD."
        )

    if _has_any(text, YIELD_BULLISH):
        yield_score += 5
        gold_score -= 3
        reasons.append(
            "US Yield meningkat dan menjadi tekanan bagi Gold."
        )

    if _has_any(text, YIELD_BEARISH):
        yield_score -= 5
        gold_score += 3
        reasons.append(
            "US Yield menurun dan mendukung Gold."
        )

    if _has_any(text, OIL_BULLISH):
        oil_score += 5
        reasons.append(
            "Harga minyak menunjukkan tekanan bullish."
        )

    if _has_any(text, OIL_BEARISH):
        oil_score -= 5
        reasons.append(
            "Harga minyak menunjukkan tekanan bearish."
        )

    # --------------------------------------------------------
    # FED
    # --------------------------------------------------------

    policy_bias = _fed_policy_bias(text)

    if policy_bias > 0:

        usd_score -= 4
        yield_score -= 4
        gold_score += 5

        reasons.append(
            "Ekspektasi kebijakan Fed cenderung dovish, "
            "mendukung Gold melalui USD dan yield yang lebih rendah."
        )

    elif policy_bias < 0:

        usd_score += 4
        yield_score += 4
        gold_score -= 5

        reasons.append(
            "Ekspektasi kebijakan Fed cenderung hawkish, "
            "memberikan tekanan terhadap Gold."
        )

    # --------------------------------------------------------
    # SAFE HAVEN
    # --------------------------------------------------------

    safe_haven_terms = [
        "safe haven",
        "risk-off",
        "risk off",
        "geopolitical tensions",
        "geopolitical uncertainty",
        "geopolitical risk",
        "war escalates",
        "conflict escalates",
        "military escalation",
        "escalation in the middle east",
        "attack",
        "attacks",
        "missile strike",
        "airstrike",
        "air strikes",
        "hostilities",
        "escalation",
    ]

    geopolitical_terms = [
        "iran",
        "israel",
        "gaza",
        "middle east",
        "hormuz",
        "strait of hormuz",
        "war",
        "conflict",
        "military",
        "missile",
        "sanctions",
    ]

    geopolitical_risk = _has_any(
        text,
        geopolitical_terms,
    )

    safe_haven = _has_any(
        text,
        safe_haven_terms,
    )

    if geopolitical_risk or safe_haven:

        gold_score += 4

        reasons.append(
            "Risiko geopolitik meningkatkan permintaan "
            "aset safe haven seperti Gold."
        )

    # --------------------------------------------------------
    # OIL -> INFLATION -> FED/YIELD CHANNEL
    # --------------------------------------------------------

    oil_inflation_terms = [
        "oil fuels inflation",
        "oil stokes inflation",
        "oil boosts inflation",
        "oil raises inflation",
        "higher oil inflation",
        "oil-driven inflation",
        "energy inflation",
        "inflation pressure from oil",
        "inflation fears",
        "inflation concerns",
        "higher inflation",
        "inflation expectations",
        "energy prices",
    ]

    oil_supply_terms = [
        "supply disruption",
        "supply disruptions",
        "supply risk",
        "supply shock",
        "oil supply",
        "production disruption",
        "production disruptions",
        "shipping disruption",
        "shipping disruptions",
        "hormuz",
        "strait of hormuz",
    ]

    oil_bullish = oil_score > 0

    inflation_risk = (
        oil_bullish
        and (
            _has_any(text, oil_inflation_terms)
            or _has_any(text, oil_supply_terms)
        )
    )

    if inflation_risk:

        # Secondary bearish Gold channel.
        gold_score -= 2

        risks.append(
            "Kenaikan harga minyak dapat meningkatkan "
            "risiko inflasi dan ekspektasi suku bunga lebih tinggi."
        )

        if policy_bias < 0:

            gold_score -= 3
            usd_score += 2
            yield_score += 2

            reasons.append(
                "Risiko inflasi memperkuat ekspektasi Fed hawkish."
            )

        else:

            reasons.append(
                "Namun tekanan inflasi dari minyak dapat menjadi "
                "headwind bagi Gold jika mendorong yield/USD naik."
            )

    # --------------------------------------------------------
    # HORMUZ SPECIAL LOGIC
    # --------------------------------------------------------

    hormuz = (
        "hormuz" in text
        or "strait of hormuz" in text
    )

    if hormuz and oil_bullish:

        gold_score += 1

        reasons.append(
            "Gangguan Hormuz memberikan tambahan risiko geopolitik "
            "dan mendukung safe-haven demand."
        )

    # --------------------------------------------------------
    # INFLATION DIRECT
    # --------------------------------------------------------

    inflation_bearish_gold_terms = [
        "inflation rises",
        "inflation rose",
        "inflation increases",
        "inflation increased",
        "inflation higher",
        "hotter inflation",
        "hot inflation",
        "higher than expected inflation",
        "cpi hotter",
        "cpi rises",
        "pce rises",
    ]

    inflation_bullish_gold_terms = [
        "inflation falls",
        "inflation fell",
        "inflation declines",
        "inflation declined",
        "inflation cools",
        "inflation cooled",
        "cooler inflation",
        "lower than expected inflation",
        "cpi cools",
        "pce cools",
    ]

    if _has_any(text, inflation_bearish_gold_terms):

        gold_score -= 4
        usd_score += 2
        yield_score += 2

        reasons.append(
            "Inflasi yang lebih tinggi meningkatkan tekanan "
            "terhadap Gold melalui ekspektasi suku bunga."
        )

    if _has_any(text, inflation_bullish_gold_terms):

        gold_score += 4
        usd_score -= 2
        yield_score -= 2

        reasons.append(
            "Inflasi yang lebih rendah mengurangi tekanan "
            "terhadap suku bunga dan mendukung Gold."
        )

    # --------------------------------------------------------
    # LABOR / MACRO
    # --------------------------------------------------------

    strong_us_data = [
        "strong jobs report",
        "strong employment",
        "strong payrolls",
        "payrolls beat",
        "jobs beat expectations",
        "employment beat expectations",
        "strong economic data",
        "better than expected",
        "beats expectations",
    ]

    weak_us_data = [
        "weak jobs report",
        "weak employment",
        "weak payrolls",
        "payrolls miss",
        "jobs miss expectations",
        "employment missed expectations",
        "weak economic data",
        "worse than expected",
        "misses expectations",
    ]

    if _has_any(text, strong_us_data):

        usd_score += 3
        yield_score += 3
        gold_score -= 4

        reasons.append(
            "Data ekonomi AS yang kuat cenderung mendukung "
            "USD/yield dan menekan Gold."
        )

    if _has_any(text, weak_us_data):

        usd_score -= 3
        yield_score -= 3
        gold_score += 4

        reasons.append(
            "Data ekonomi AS yang lemah cenderung menekan "
            "USD/yield dan mendukung Gold."
        )

    # --------------------------------------------------------
    # FINAL BIAS
    # --------------------------------------------------------

    def bias(score):

        if score >= 2:
            return "BULLISH"

        if score <= -2:
            return "BEARISH"

        return "NEUTRAL"

    gold = bias(gold_score)
    usd = bias(usd_score)
    yield_bias = bias(yield_score)
    oil = bias(oil_score)

    # --------------------------------------------------------
    # GOLD CAUSAL FALLBACK
    # --------------------------------------------------------

    if gold == "NEUTRAL":

        if usd == "BULLISH" or yield_bias == "BULLISH":
            gold = "BEARISH"

        elif usd == "BEARISH" or yield_bias == "BEARISH":
            gold = "BULLISH"

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    bullish_evidence = 0
    bearish_evidence = 0

    if gold_score > 0:
        bullish_evidence += gold_score

    if gold_score < 0:
        bearish_evidence += abs(gold_score)

    if usd_score < 0:
        bullish_evidence += 2

    if usd_score > 0:
        bearish_evidence += 2

    if yield_score < 0:
        bullish_evidence += 2

    if yield_score > 0:
        bearish_evidence += 2

    if geopolitical_risk:
        bullish_evidence += 2

    if inflation_risk:
        bearish_evidence += 1

    total_evidence = (
        bullish_evidence + bearish_evidence
    )

    if total_evidence >= 10:
        confidence = "HIGH"

    elif total_evidence >= 5:
        confidence = "MEDIUM"

    else:
        confidence = "LOW"

    # Konflik antara safe haven dan inflation/yield.
    if (
        geopolitical_risk
        and inflation_risk
        and abs(gold_score) <= 4
    ):
        confidence = "MEDIUM"

    # Kalau hampir seimbang, jangan terlalu percaya diri.
    if (
        bullish_evidence > 0
        and bearish_evidence > 0
        and abs(
            bullish_evidence - bearish_evidence
        ) <= 2
    ):
        confidence = "MEDIUM"

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
        "reasons": reasons,
        "risks": risks,
        "policy_bias": policy_bias,
        "inflation_risk": inflation_risk,
        "geopolitical_risk": geopolitical_risk,
    }


# ============================================================
# ANALYSIS TRANSLATION / CLEANING
# ============================================================

def build_indonesian_analysis(direction):

    reasons = direction.get("reasons", [])
    risks = direction.get("risks", [])

    # Remove duplicate reasons.
    clean_reasons = []

    for reason in reasons:

        if reason not in clean_reasons:
            clean_reasons.append(reason)

    clean_risks = []

    for risk in risks:

        if risk not in clean_risks:
            clean_risks.append(risk)

    analysis_lines = clean_reasons[:6]

    if not analysis_lines:

        analysis_lines.append(
            "Belum terdapat sinyal fundamental yang cukup kuat "
            "untuk menentukan arah XAUUSD."
        )

    return analysis_lines, clean_risks[:3]


# ============================================================
# CONCLUSION
# ============================================================

def gold_conclusion(direction):

    gold = direction["gold"]
    confidence = direction["confidence"]

    if gold == "BULLISH":

        return (
            f"Cenderung <b>BULLISH</b> untuk XAUUSD "
            f"dengan confidence <b>{confidence}</b>."
        )

    if gold == "BEARISH":

        return (
            f"Cenderung <b>BEARISH</b> untuk XAUUSD "
            f"dengan confidence <b>{confidence}</b>."
        )

    return (
        f"Arah XAUUSD masih <b>NEUTRAL</b> "
        f"dengan confidence <b>{confidence}</b>."
    )


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

    return " ".join(
        sentences[:3]
    )[:700]


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

    if age > timedelta(
        hours=MAX_NEWS_AGE_HOURS
    ):
        return None

    if age < timedelta(
        minutes=-10
    ):
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
        "scores": analysis["scores"],
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

                if item["score"] > existing["score"]:
                    existing.clear()
                    existing.update(item)

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
        "[NEWS] Starting news scan..."
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
# TELEGRAM FORMAT
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

        title_id = translate_to_indonesian(
            title
        )

        summary_id = translate_to_indonesian(
            summary
        )

    else:

        title_id = title
        summary_id = summary

    direction = item["direction"]

    gold = direction["gold"]
    usd = direction["usd"]
    yield_bias = direction["yield"]
    oil = direction["oil"]

    analysis_lines, risk_lines = (
        build_indonesian_analysis(
            direction
        )
    )

    analysis_text = ""

    for line in analysis_lines:
        analysis_text += (
            f"• {html.escape(line)}\n"
        )

    risk_text = ""

    if risk_lines:

        risk_text = (
            "\n⚠️ <b>RISIKO</b>\n"
        )

        for line in risk_lines:
            risk_text += (
                f"• {html.escape(line)}\n"
            )

        risk_text += "\n"

    event = item["category"]

    # Translate only external content.
    # Internal analytical text is already Indonesian.
    message = (
        "🚨 <b>BREAKING NEWS</b>\n\n"

        f"📂 <b>{html.escape(event)}</b>\n\n"

        f"📰 <b>{html.escape(title_id)}</b>\n\n"

        f"⚠️ <b>{html.escape(item['impact'])}</b> "
        f"{item['stars']}\n\n"

        f"📝 {html.escape(summary_id)}\n\n"

        "🥇 <b>GOLD / XAUUSD</b>\n"
        f"{direction_text(gold)}\n\n"

        "💵 <b>USD</b>\n"
        f"{direction_text(usd)}\n\n"

        "📈 <b>US YIELD</b>\n"
        f"{direction_text(yield_bias)}\n\n"

        "🛢️ <b>OIL / WTI</b>\n"
        f"{direction_text(oil)}\n\n"

        "🧠 <b>ANALISIS</b>\n"
        f"{analysis_text}\n"

        f"🎯 <b>CONFIDENCE</b>\n"
        f"{direction['confidence']}\n\n"

        f"📌 <b>DAMPAK XAUUSD</b>\n"
        f"{gold_conclusion(direction)}\n\n"

        f"{risk_text}"

        f"📊 <b>Event:</b> "
        f"{html.escape(event)}\n"

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
# DEBUG
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

    results = get_news(limit=10)

    print()
    print("=" * 80)
    print(
        f"FINAL NEWS: {len(results)}"
    )
    print("=" * 80)

    for index, item in enumerate(
        results,
        start=1,
    ):

        d = item["direction"]

        print()
        print(
            f"{index}. {item['title']}"
        )

        print(
            f"   SCORE      : {item['score']}"
        )

        print(
            f"   IMPACT     : "
            f"{item['impact']} "
            f"{item['stars']}"
        )

        print(
            f"   CATEGORY   : "
            f"{item['category']}"
        )

        print(
            f"   GOLD       : "
            f"{d['gold']}"
        )

        print(
            f"   USD        : "
            f"{d['usd']}"
        )

        print(
            f"   YIELD      : "
            f"{d['yield']}"
        )

        print(
            f"   OIL        : "
            f"{d['oil']}"
        )

        print(
            f"   CONFIDENCE : "
            f"{d['confidence']}"
        )

        print(
            f"   GOLD SCORE : "
            f"{d['gold_score']}"
        )

        print(
            f"   SOURCE     : "
            f"{item['source']}"
        )

        print(
            f"   URL        : "
            f"{item['url']}"
        )

        print(
            "\n   ANALYSIS:"
        )

        for reason in d["reasons"]:
            print(
                f"   - {reason}"
            )

        if d["risks"]:

            print(
                "\n   RISKS:"
            )

            for risk in d["risks"]:
                print(
                    f"   - {risk}"
                )

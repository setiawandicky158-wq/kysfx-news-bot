import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib
import re
import time


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://investinglive.com"
NEWS_URL = "https://investinglive.com/news/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# GOLD
# ============================================================

GOLD_KEYWORDS = [
    "gold",
    "xau",
    "xauusd",
    "bullion",
    "precious metal",
    "precious metals",
]


# ============================================================
# USD
# ============================================================

USD_KEYWORDS = [
    "usd",
    "us dollar",
    "dollar",
    "greenback",
    "dxy",
    "fed",
    "federal reserve",
    "fomc",
    "powell",
    "interest rate",
    "rate cut",
    "rate hike",
    "rate decision",
]


# ============================================================
# YIELD
# ============================================================

YIELD_KEYWORDS = [
    "yield",
    "yields",
    "treasury",
    "10-year",
    "10 year",
    "10y",
    "us10y",
    "bond yield",
]


# ============================================================
# OIL + WTI = SATU
# ============================================================

OIL_KEYWORDS = [
    "oil",
    "wti",
    "crude",
    "crude oil",
    "west texas intermediate",
    "opec",
    "opec+",
    "oil inventory",
    "oil inventories",
    "oil production",
    "oil supply",
    "oil demand",
    "eia",
]


# ============================================================
# HIGH IMPACT
# ============================================================

HIGH_IMPACT_KEYWORDS = [
    "nfp",
    "nonfarm",
    "non-farm",
    "payroll",
    "employment report",
    "unemployment rate",
    "unemployment",
    "cpi",
    "core cpi",
    "inflation",
    "ppi",
    "gdp",
    "fomc",
    "fed decision",
    "fed meeting",
    "powell",
    "interest rate decision",
    "rate decision",
    "rate cut",
    "rate hike",
    "opec",
    "opec+",
    "eia",
    "crude inventories",
    "oil inventories",
    "war",
    "sanctions",
    "tariff",
    "iran",
    "israel",
    "russia",
    "ukraine",
    "middle east",
    "hormuz",
    "retail sales",
    "pce",
    "jobless claims",
    "jolts",
    "ism",
    "pmi",
]


# ============================================================
# BLOCKED NEWS
# ============================================================

BLOCKED_TITLE_KEYWORDS = [
    "newsquawk week ahead",
    "newsquawk weekly preview",
    "newsquawk weekly outlook",
    "week ahead",
    "weekly preview",
    "weekly outlook",
    "events next week",
    "calendar next week",
    "coming week",
]


# ============================================================
# CATEGORY
# ============================================================

CATEGORY_KEYWORDS = {

    "💼 Tenaga Kerja": [
        "nfp",
        "nonfarm",
        "non-farm",
        "payroll",
        "employment",
        "unemployment",
        "jobless claims",
        "jobs",
        "jolts",
        "labor",
        "labour",
        "wages",
    ],

    "🏦 Bank Sentral": [
        "fed",
        "fomc",
        "powell",
        "federal reserve",
        "interest rate",
        "rate decision",
        "rate cut",
        "rate hike",
        "central bank",
        "rba",
        "boj",
        "ecb",
        "boe",
    ],

    "📊 Inflasi": [
        "cpi",
        "inflation",
        "core inflation",
        "ppi",
        "consumer prices",
        "producer prices",
        "pce",
    ],

    "🛢️ Energi": [
        "oil",
        "wti",
        "crude",
        "opec",
        "opec+",
        "eia",
        "inventory",
        "inventories",
        "production",
        "energy",
    ],

    "🌍 Geopolitik": [
        "war",
        "conflict",
        "iran",
        "israel",
        "russia",
        "ukraine",
        "sanctions",
        "attack",
        "military",
        "middle east",
        "hormuz",
    ],

    "💵 Ekonomi AS": [
        "gdp",
        "retail sales",
        "ism",
        "pmi",
        "consumer confidence",
        "economic growth",
    ],
}


# ============================================================
# ISTILAH YANG TIDAK BOLEH DITERJEMAHKAN
# ============================================================

PRESERVE_TERMS = [
    "Non-Farm Payrolls",
    "Non-Farm Payroll",
    "nonfarm payrolls",
    "nonfarm payroll",
    "NFP",

    "Gold",
    "XAUUSD",
    "XAU",

    "USD",
    "DXY",

    "Oil",
    "WTI",
    "Crude Oil",
    "West Texas Intermediate",

    "Yield",
    "Yields",
    "Treasury Yield",
    "US Treasury",

    "Fed",
    "Federal Reserve",
    "FOMC",
    "Powell",

    "CPI",
    "Core CPI",
    "PPI",
    "GDP",
    "PCE",
    "JOLTS",
    "ISM",
    "PMI",

    "OPEC",
    "OPEC+",
    "EIA",

    "RBA",
    "BoJ",
    "ECB",
    "BOE",

    "Interest Rate",
    "Rate Hike",
    "Rate Cut",

    "Retail Sales",
    "Jobless Claims",
    "Unemployment Rate",
]


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    soup = BeautifulSoup(
        str(text),
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    text = " ".join(
        text.split()
    )

    prefixes = [
        "investingLive",
        "InvestingLive",
        "investinglive",
        "Investinglive",
        "investment",
    ]

    changed = True

    while changed:

        changed = False

        for prefix in prefixes:

            if text.startswith(prefix):

                text = text[
                    len(prefix):
                ].strip()

                changed = True

    return text.strip()


# ============================================================
# NORMALIZE URL
# ============================================================

def normalize_url(url):

    if not url:
        return ""

    url = url.strip()

    if url.startswith("/"):
        return urljoin(
            BASE_URL,
            url
        )

    return url


# ============================================================
# KEYWORD CHECK
# ============================================================

def contains_keyword(
    text,
    keywords
):

    if not text:
        return False

    lower = text.lower()

    return any(
        keyword.lower() in lower
        for keyword in keywords
    )


# ============================================================
# BLOCKED TITLE
# ============================================================

def is_blocked_title(title):

    if not title:
        return True

    return contains_keyword(
        title,
        BLOCKED_TITLE_KEYWORDS
    )


# ============================================================
# CHECK URL
# ============================================================

def looks_like_url(text):

    if not text:
        return True

    text = text.strip().lower()

    if text.startswith("/news/"):
        return True

    if text.startswith("http://"):
        return True

    if text.startswith("https://"):
        return True

    if "investinglive.com/news/" in text:
        return True

    return False


# ============================================================
# EXTRACT TITLE
# ============================================================

def extract_title(link):

    candidates = []

    # --------------------------------------------------------
    # 1. Text anchor
    # --------------------------------------------------------

    direct = clean_text(
        link.get_text(
            " ",
            strip=True
        )
    )

    if direct:
        candidates.append(
            direct
        )

    # --------------------------------------------------------
    # 2. Attributes
    # --------------------------------------------------------

    for attr in [
        "title",
        "aria-label",
        "data-title",
        "data-headline",
        "data-original-title",
    ]:

        value = clean_text(
            link.get(
                attr,
                ""
            )
        )

        if value:
            candidates.append(
                value
            )

    # --------------------------------------------------------
    # 3. Parent elements
    # --------------------------------------------------------

    parent = link.parent

    for _ in range(5):

        if not parent:
            break

        for heading in parent.find_all(
            [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
            ]
        ):

            value = clean_text(
                heading.get_text(
                    " ",
                    strip=True
                )
            )

            if value:
                candidates.append(
                    value
                )

        for attr in [
            "title",
            "aria-label",
            "data-title",
            "data-headline",
        ]:

            value = clean_text(
                parent.get(
                    attr,
                    ""
                )
            )

            if value:
                candidates.append(
                    value
                )

        parent = parent.parent

    # --------------------------------------------------------
    # Pilih title valid
    # --------------------------------------------------------

    for candidate in candidates:

        candidate = clean_text(
            candidate
        )

        if not candidate:
            continue

        if looks_like_url(
            candidate
        ):
            continue

        if len(candidate) < 15:
            continue

        if len(candidate) > 500:
            continue

        return candidate

    return ""


# ============================================================
# TRANSLATION
# ============================================================

def translate_to_indonesian(text):

    if not text:
        return ""

    text = text.strip()

    if not text:
        return ""

    placeholders = {}

    protected_text = text

    # --------------------------------------------------------
    # Sort dari istilah terpanjang
    # --------------------------------------------------------

    sorted_terms = sorted(
        PRESERVE_TERMS,
        key=len,
        reverse=True
    )

    # --------------------------------------------------------
    # LOCK TERMS
    # --------------------------------------------------------

    counter = 0

    for term in sorted_terms:

        pattern = re.compile(
            re.escape(term),
            re.IGNORECASE
        )

        def replace_term(
            match
        ):

            nonlocal counter

            key = (
                f"ZZTERM{counter}ZZ"
            )

            placeholders[key] = (
                match.group(0)
            )

            counter += 1

            return key

        protected_text = pattern.sub(
            replace_term,
            protected_text
        )

    # --------------------------------------------------------
    # TRANSLATE
    # --------------------------------------------------------

    try:

        response = requests.get(
            "https://translate.googleapis.com/"
            "translate_a/single",

            params={
                "client": "gtx",
                "sl": "en",
                "tl": "id",
                "dt": "t",
                "q": protected_text,
            },

            headers=HEADERS,

            timeout=20,
        )

        if response.status_code != 200:

            print(
                "[TRANSLATE] HTTP:",
                response.status_code
            )

            return text

        data = response.json()

        translated = ""

        if data and data[0]:

            for item in data[0]:

                if item and item[0]:

                    translated += item[0]

        translated = translated.strip()

        if not translated:

            return text

        # ----------------------------------------------------
        # RESTORE TERMS
        # ----------------------------------------------------

        for key, original in (
            placeholders.items()
        ):

            translated = translated.replace(
                key,
                original
            )

            translated = translated.replace(
                key.lower(),
                original
            )

        return translated

    except Exception as e:

        print(
            "[TRANSLATE ERROR]",
            type(e).__name__,
            str(e)
        )

        return text


# ============================================================
# CATEGORY
# ============================================================

def detect_category(text):

    lower = text.lower()

    order = [
        "💼 Tenaga Kerja",
        "🏦 Bank Sentral",
        "📊 Inflasi",
        "🛢️ Energi",
        "🌍 Geopolitik",
        "💵 Ekonomi AS",
    ]

    for category in order:

        for keyword in CATEGORY_KEYWORDS[
            category
        ]:

            if keyword.lower() in lower:

                return category

    return "📰 Market"


# ============================================================
# IMPACT
# ============================================================

def calculate_impact(text):

    lower = text.lower()

    score = 0

    for keyword in HIGH_IMPACT_KEYWORDS:

        if keyword.lower() in lower:

            score += 2

    if contains_keyword(
        text,
        GOLD_KEYWORDS
    ):

        score += 2

    if contains_keyword(
        text,
        USD_KEYWORDS
    ):

        score += 1

    if contains_keyword(
        text,
        YIELD_KEYWORDS
    ):

        score += 1

    if contains_keyword(
        text,
        OIL_KEYWORDS
    ):

        score += 2

    if score >= 8:

        return (
            "High Impact News",
            "⭐⭐⭐⭐⭐"
        )

    if score >= 5:

        return (
            "High Impact News",
            "⭐⭐⭐⭐"
        )

    if score >= 3:

        return (
            "Market Impact",
            "⭐⭐⭐"
        )

    return (
        "Low Impact",
        "⭐⭐"
    )


# ============================================================
# GOLD ANALYSIS
# ============================================================

def analyze_gold(text):

    lower = text.lower()

    bullish = [
        "gold up",
        "gold rises",
        "gold rose",
        "gold gains",
        "gold higher",
        "gold climbs",
        "gold advances",
        "gold rallies",
        "gold strengthens",
        "gold jumps",
    ]

    bearish = [
        "gold down",
        "gold falls",
        "gold fell",
        "gold drops",
        "gold lower",
        "gold declines",
        "gold slides",
        "gold weakens",
        "gold tumbles",
    ]

    if any(
        x in lower
        for x in bullish
    ):

        return (
            "Gold berpotensi bullish. "
            "Tunggu konfirmasi price action."
        )

    if any(
        x in lower
        for x in bearish
    ):

        return (
            "Gold berpotensi bearish. "
            "Tunggu konfirmasi price action."
        )

    return (
        "Potensi volatilitas tinggi. "
        "Tunggu reaksi harga."
    )


# ============================================================
# USD ANALYSIS
# ============================================================

def analyze_usd(text):

    lower = text.lower()

    bullish = [
        "dollar rises",
        "dollar rose",
        "dollar gains",
        "dollar higher",
        "dollar strengthens",
        "usd rises",
        "usd higher",
        "usd gains",
        "dollar jumps",
    ]

    bearish = [
        "dollar falls",
        "dollar fell",
        "dollar drops",
        "dollar lower",
        "dollar weakens",
        "usd falls",
        "usd lower",
        "usd drops",
    ]

    if any(
        x in lower
        for x in bullish
    ):

        return (
            "USD menguat. "
            "Berpotensi memberi tekanan pada Gold."
        )

    if any(
        x in lower
        for x in bearish
    ):

        return (
            "USD melemah. "
            "Berpotensi mendukung Gold."
        )

    return (
        "Perhatikan arah USD setelah "
        "rilis data atau kebijakan."
    )


# ============================================================
# YIELD ANALYSIS
# ============================================================

def analyze_yield(text):

    lower = text.lower()

    bullish = [
        "yields rise",
        "yield rises",
        "yields higher",
        "yield higher",
        "yields up",
        "yield up",
    ]

    bearish = [
        "yields fall",
        "yield falls",
        "yields lower",
        "yield lower",
        "yields down",
        "yield down",
    ]

    if any(
        x in lower
        for x in bullish
    ):

        return (
            "Kenaikan Yield dapat menekan Gold."
        )

    if any(
        x in lower
        for x in bearish
    ):

        return (
            "Penurunan Yield dapat mendukung Gold."
        )

    return (
        "Pantau pergerakan US Treasury Yield."
    )


# ============================================================
# OIL / WTI ANALYSIS
# ============================================================

def analyze_oil(text):

    lower = text.lower()

    bullish = [
        "wti rises",
        "wti rose",
        "wti higher",
        "wti gains",
        "oil rises",
        "oil rose",
        "oil higher",
        "oil gains",
        "crude rises",
        "crude higher",
        "oil rally",
    ]

    bearish = [
        "wti falls",
        "wti fell",
        "wti lower",
        "wti drops",
        "oil falls",
        "oil fell",
        "oil lower",
        "oil drops",
        "crude falls",
        "crude lower",
    ]

    if any(
        x in lower
        for x in bullish
    ):

        return (
            "Oil/WTI berpotensi bullish. "
            "Tunggu konfirmasi harga."
        )

    if any(
        x in lower
        for x in bearish
    ):

        return (
            "Oil/WTI berpotensi bearish. "
            "Tunggu konfirmasi harga."
        )

    if contains_keyword(
        text,
        OIL_KEYWORDS
    ):

        return (
            "Perubahan Oil/WTI dapat "
            "mempengaruhi ekspektasi inflasi."
        )

    return (
        "Pantau dampaknya terhadap Oil/WTI."
    )


# ============================================================
# RELEVANCE
# ============================================================

def is_relevant(text):

    return (
        contains_keyword(
            text,
            GOLD_KEYWORDS
        )
        or
        contains_keyword(
            text,
            USD_KEYWORDS
        )
        or
        contains_keyword(
            text,
            YIELD_KEYWORDS
        )
        or
        contains_keyword(
            text,
            OIL_KEYWORDS
        )
        or
        contains_keyword(
            text,
            HIGH_IMPACT_KEYWORDS
        )
    )


# ============================================================
# GET NEWS
# ============================================================

def get_news(limit=10):

    print(
        "[NEWS] Checking InvestingLive..."
    )

    try:

        response = requests.get(
            NEWS_URL,
            headers=HEADERS,
            timeout=30
        )

        print(
            "[NEWS] HTTP Status:",
            response.status_code
        )

        if response.status_code != 200:

            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

    except Exception as e:

        print(
            "[NEWS ERROR]",
            type(e).__name__,
            str(e)
        )

        return []

    candidates = []
    seen_urls = set()

    # ========================================================
    # FIND ARTICLE LINKS
    # ========================================================

    for link in soup.find_all(
        "a",
        href=True
    ):

        href = normalize_url(
            link.get(
                "href",
                ""
            )
        )

        if not href:
            continue

        if not href.startswith(
            BASE_URL
        ):
            continue

        if "/news/" not in href:
            continue

        if href.rstrip(
            "/"
        ) == NEWS_URL.rstrip(
            "/"
        ):
            continue

        if href in seen_urls:
            continue

        title = extract_title(
            link
        )

        # ----------------------------------------------------
        # Fallback: buat title dari URL slug
        # ----------------------------------------------------

        if not title:

            slug = href.rstrip(
                "/"
            ).split(
                "/"
            )[-1]

            if slug:

                title = slug.replace(
                    "-",
                    " "
                )

        title = clean_text(
            title
        )

        if not title:
            continue

        if looks_like_url(
            title
        ):
            continue

        if len(title) < 15:
            continue

        if is_blocked_title(
            title
        ):

            print(
                "[FILTER] Blocked:",
                title
            )

            continue

        seen_urls.add(
            href
        )

        candidates.append(
            {
                "title": title,
                "link": href,
            }
        )

    print(
        "[NEWS] Candidate articles:",
        len(candidates)
    )

    results = []

    # ========================================================
    # PROCESS ARTICLES
    # ========================================================

    for item in candidates:

        title = item["title"]
        link = item["link"]

        print(
            "[NEWS] Checking:",
            title
        )

        if not is_relevant(
            title
        ):

            print(
                "[FILTER] Not relevant:",
                title
            )

            continue

        print(
            "[NEWS] Relevant:",
            title
        )

        # ----------------------------------------------------
        # TRANSLATE ONLY TITLE
        # ----------------------------------------------------

        print(
            "[TRANSLATE] English:",
            title
        )

        translated_title = (
            translate_to_indonesian(
                title
            )
        )

        print(
            "[TRANSLATE] Indonesian:",
            translated_title
        )

        # ----------------------------------------------------
        # IMPACT
        # ----------------------------------------------------

        impact, stars = calculate_impact(
            title
        )

        # ----------------------------------------------------
        # CATEGORY
        # ----------------------------------------------------

        category = detect_category(
            title
        )

        # ----------------------------------------------------
        # UNIQUE ID
        # ----------------------------------------------------

        news_id = hashlib.sha256(
            link.encode(
                "utf-8"
            )
        ).hexdigest()

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        result = {

            "id": news_id,

            "title": translated_title,

            "summary": "",

            "link": link,

            "category": category,

            "impact": impact,

            "stars": stars,

            "gold": analyze_gold(
                title
            ),

            "usd": analyze_usd(
                title
            ),

            "yield": analyze_yield(
                title
            ),

            "oil": analyze_oil(
                title
            ),
        }

        results.append(
            result
        )

        if len(results) >= limit:
            break

        time.sleep(
            0.4
        )

    print(
        "[NEWS] Relevant articles:",
        len(results)
    )

    return results


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_news(news):

    return (
        "🚨 <b>BREAKING NEWS</b>\n"
        f"📂 {news['category']}\n\n"

        f"📰 <b>{news['title']}</b>\n\n"

        f"⚠️ <b>{news['impact']}</b> "
        f"{news['stars']}\n\n"

        f"🟡 <b>Gold:</b>\n"
        f"{news['gold']}\n\n"

        f"💵 <b>USD:</b>\n"
        f"{news['usd']}\n\n"

        f"📈 <b>Yield:</b>\n"
        f"{news['yield']}\n\n"

        f"🛢️ <b>Oil:</b>\n"
        f"{news['oil']}\n\n"

        f"🔗 <a href=\"{news['link']}\">"
        "Sumber berita"
        "</a>"
    )

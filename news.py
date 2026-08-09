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
# BLOCKED TITLE
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
# ISTILAH YANG WAJIB TETAP ASLI
# ============================================================

PRESERVE_TERMS = [
    "Non-Farm Payrolls",
    "Non-Farm Payroll",
    "Nonfarm Payrolls",
    "Nonfarm Payroll",
    "NFP",

    "Gold",
    "XAUUSD",
    "XAU",

    "USD",
    "US Dollar",
    "DXY",

    "Oil",
    "WTI",
    "Crude Oil",
    "West Texas Intermediate",

    "Yield",
    "Yields",
    "Treasury Yield",
    "US Treasury",
    "Treasury",

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
    "Rate Decision",

    "Retail Sales",
    "Jobless Claims",
    "Unemployment Rate",

    "US",
    "Iran",
    "Israel",
    "Russia",
    "Ukraine",
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
# URL
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
# KEYWORD
# ============================================================

def contains_keyword(text, keywords):

    if not text:
        return False

    lower = text.lower()

    return any(
        keyword.lower() in lower
        for keyword in keywords
    )


# ============================================================
# BLOCKED
# ============================================================

def is_blocked_title(title):

    if not title:
        return True

    return contains_keyword(
        title,
        BLOCKED_TITLE_KEYWORDS
    )


# ============================================================
# URL CHECK
# ============================================================

def looks_like_url(text):

    if not text:
        return True

    value = text.strip().lower()

    return (
        value.startswith("/news/")
        or value.startswith("http://")
        or value.startswith("https://")
        or "investinglive.com/news/" in value
    )


# ============================================================
# EXTRACT TITLE
# ============================================================

def extract_title(link):

    candidates = []

    direct = clean_text(
        link.get_text(
            " ",
            strip=True
        )
    )

    if direct:
        candidates.append(direct)

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
            candidates.append(value)

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
                candidates.append(value)

        parent = parent.parent

    for candidate in candidates:

        candidate = clean_text(
            candidate
        )

        if not candidate:
            continue

        if looks_like_url(candidate):
            continue

        if len(candidate) < 15:
            continue

        if len(candidate) > 500:
            continue

        return candidate

    return ""


# ============================================================
# GET REAL ARTICLE TITLE
# ============================================================

def get_real_article_title(
    url,
    fallback_title=""
):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=25
        )

        if response.status_code != 200:

            return clean_text(
                fallback_title
            )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # OpenGraph

        og = soup.find(
            "meta",
            property="og:title"
        )

        if og:

            value = clean_text(
                og.get(
                    "content",
                    ""
                )
            )

            if value and not looks_like_url(
                value
            ):

                return value

        # H1

        h1 = soup.find("h1")

        if h1:

            value = clean_text(
                h1.get_text(
                    " ",
                    strip=True
                )
            )

            if value and not looks_like_url(
                value
            ):

                return value

        # Title

        title_tag = soup.find(
            "title"
        )

        if title_tag:

            value = clean_text(
                title_tag.get_text(
                    " ",
                    strip=True
                )
            )

            value = re.sub(
                r"\s*\|\s*investingLive.*$",
                "",
                value,
                flags=re.IGNORECASE
            )

            if value and not looks_like_url(
                value
            ):

                return value.strip()

    except Exception as e:

        print(
            "[TITLE ERROR]",
            type(e).__name__,
            str(e)
        )

    return clean_text(
        fallback_title
    )


# ============================================================
# GET ARTICLE BODY
# ============================================================

def get_article(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:

            return ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Hapus elemen yang tidak diperlukan

        for element in soup(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "nav",
                "footer",
                "header",
                "form",
                "iframe",
            ]
        ):

            element.decompose()

        selectors = [
            "article",
            "[class*='article-body']",
            "[class*='article-content']",
            "[class*='post-content']",
            "[class*='entry-content']",
            "main",
        ]

        best_text = ""

        for selector in selectors:

            element = soup.select_one(
                selector
            )

            if not element:
                continue

            paragraphs = element.find_all(
                "p"
            )

            text_parts = []

            for p in paragraphs:

                text = clean_text(
                    p.get_text(
                        " ",
                        strip=True
                    )
                )

                if len(text) >= 30:

                    text_parts.append(
                        text
                    )

            text = " ".join(
                text_parts
            )

            if len(text) > len(
                best_text
            ):

                best_text = text

        # Fallback seluruh paragraph

        if len(best_text) < 150:

            paragraphs = soup.find_all(
                "p"
            )

            parts = []

            for p in paragraphs:

                text = clean_text(
                    p.get_text(
                        " ",
                        strip=True
                    )
                )

                if len(text) >= 30:

                    parts.append(text)

            best_text = " ".join(
                parts
            )

        return best_text.strip()

    except Exception as e:

        print(
            "[ARTICLE ERROR]",
            type(e).__name__,
            str(e)
        )

        return ""


# ============================================================
# MAKE SUMMARY
# ============================================================

def make_summary(article):

    if not article:
        return ""

    article = clean_text(
        article
    )

    if not article:
        return ""

    # Pecah berdasarkan kalimat

    sentences = re.split(
        r"(?<=[.!?])\s+",
        article
    )

    clean_sentences = []

    for sentence in sentences:

        sentence = clean_text(
            sentence
        )

        if len(sentence) < 25:
            continue

        # Hindari bagian navigasi / iklan

        lower = sentence.lower()

        blocked = [
            "subscribe",
            "sign up",
            "advertisement",
            "cookie",
            "privacy policy",
            "terms of use",
        ]

        if any(
            x in lower
            for x in blocked
        ):
            continue

        clean_sentences.append(
            sentence
        )

    if not clean_sentences:
        return article[:700]

    # Ambil maksimal 3 kalimat

    summary = " ".join(
        clean_sentences[:3]
    )

    # Batasi panjang

    if len(summary) > 900:

        summary = summary[:900]

        last_space = summary.rfind(
            " "
        )

        if last_space > 500:

            summary = summary[
                :last_space
            ]

        summary += "..."

    return summary


# ============================================================
# TRANSLATE
# Istilah teknis dikunci sebelum translasi
# ============================================================

def translate_to_indonesian(text):

    if not text:
        return ""

    text = clean_text(
        text
    )

    if not text:
        return ""

    placeholders = {}

    protected_text = text

    # Istilah terpanjang diproses terlebih dahulu

    sorted_terms = sorted(
        PRESERVE_TERMS,
        key=len,
        reverse=True
    )

    counter = 0

    for term in sorted_terms:

        pattern = re.compile(
            re.escape(term),
            re.IGNORECASE
        )

        def replace_term(match):

            nonlocal counter

            key = (
                f"ZXTERM{counter}ZX"
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

        # Kembalikan semua istilah

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

    score = 0

    for keyword in HIGH_IMPACT_KEYWORDS:

        if keyword.lower() in text.lower():

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
    seen = set()

    # ========================================================
    # COLLECT LINKS
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

        if href.rstrip("/") == NEWS_URL.rstrip("/"):
            continue

        if href in seen:
            continue

        raw_title = extract_title(
            link
        )

        if not raw_title:
            continue

        if looks_like_url(
            raw_title
        ):
            continue

        seen.add(
            href
        )

        candidates.append(
            (
                raw_title,
                href
            )
        )

    print(
        "[NEWS] Candidate articles:",
        len(candidates)
    )

    results = []

    # ========================================================
    # PROCESS
    # ========================================================

    for raw_title, href in candidates:

        print(
            "[NEWS] Checking:",
            raw_title
        )

        # ----------------------------------------------------
        # REAL TITLE
        # ----------------------------------------------------

        real_title = get_real_article_title(
            href,
            raw_title
        )

        real_title = clean_text(
            real_title
        )

        if not real_title:
            continue

        if looks_like_url(
            real_title
        ):
            continue

        if is_blocked_title(
            real_title
        ):

            print(
                "[FILTER] Blocked:",
                real_title
            )

            continue

        # ----------------------------------------------------
        # ARTICLE BODY
        # ----------------------------------------------------

        article = get_article(
            href
        )

        full_text = (
            real_title
            + " "
            + article
        )

        # ----------------------------------------------------
        # RELEVANCE
        # ----------------------------------------------------

        if not is_relevant(
            full_text
        ):

            print(
                "[FILTER] Not relevant:",
                real_title
            )

            continue

        print(
            "[NEWS] Relevant:",
            real_title
        )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        summary_english = make_summary(
            article
        )

        # ----------------------------------------------------
        # TRANSLATE TITLE
        # ----------------------------------------------------

        print(
            "[TRANSLATE] English Title:",
            real_title
        )

        translated_title = (
            translate_to_indonesian(
                real_title
            )
        )

        print(
            "[TRANSLATE] Indonesian Title:",
            translated_title
        )

        # ----------------------------------------------------
        # TRANSLATE SUMMARY
        # ----------------------------------------------------

        translated_summary = ""

        if summary_english:

            print(
                "[TRANSLATE] English Summary:",
                summary_english[:300]
            )

            translated_summary = (
                translate_to_indonesian(
                    summary_english
                )
            )

            print(
                "[TRANSLATE] Indonesian Summary:",
                translated_summary[:300]
            )

        # ----------------------------------------------------
        # IMPACT
        # ----------------------------------------------------

        impact, stars = calculate_impact(
            full_text
        )

        # ----------------------------------------------------
        # CATEGORY
        # ----------------------------------------------------

        category = detect_category(
            full_text
        )

        # ----------------------------------------------------
        # UNIQUE ID
        # ----------------------------------------------------

        news_id = hashlib.sha256(
            href.encode(
                "utf-8"
            )
        ).hexdigest()

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        result = {

            "id": news_id,

            "title": translated_title,

            "summary": translated_summary,

            "link": href,

            "category": category,

            "impact": impact,

            "stars": stars,

            "gold": analyze_gold(
                full_text
            ),

            "usd": analyze_usd(
                full_text
            ),

            "yield": analyze_yield(
                full_text
            ),

            "oil": analyze_oil(
                full_text
            ),
        }

        results.append(
            result
        )

        if len(results) >= limit:
            break

        time.sleep(
            0.5
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

    message = (
        "🚨 <b>BREAKING NEWS</b>\n"
        f"📂 {news['category']}\n\n"

        f"📰 <b>{news['title']}</b>\n"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    if news.get(
        "summary"
    ):

        message += (
            "\n"
            f"📝 <b>Ringkasan:</b>\n"
            f"{news['summary']}\n"
        )

    # --------------------------------------------------------
    # IMPACT
    # --------------------------------------------------------

    message += (
        "\n"
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

    return message

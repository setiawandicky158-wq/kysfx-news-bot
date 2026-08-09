import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib
import re
import time


BASE_URL = "https://investinglive.com"
NEWS_URL = "https://investinglive.com/news/"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# KEYWORDS
# ============================================================

GOLD_KEYWORDS = [
    "gold",
    "xau",
    "xauusd",
    "bullion",
    "precious metal",
    "precious metals",
]


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
]


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


# OIL + WTI = SATU KATEGORI
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


HIGH_IMPACT_KEYWORDS = [
    "nfp",
    "nonfarm",
    "non-farm",
    "payroll",
    "employment report",
    "unemployment rate",
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
]


# ============================================================
# BERITA YANG TIDAK BOLEH DIKIRIM
# ============================================================

BLOCKED_KEYWORDS = [
    "newsquawk week ahead",
    "week ahead",
    "next week",
    "weekly preview",
    "weekly outlook",
    "week ahead preview",
    "events next week",
    "calendar next week",
    "agenda minggu depan",
    "coming week",
    "this week ahead",
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
# TRANSLATION
# ============================================================

def translate_to_indonesian(text):

    if not text:
        return ""

    text = text.strip()

    if not text:
        return ""

    try:

        url = (
            "https://translate.googleapis.com/"
            "translate_a/single"
        )

        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "id",
            "dt": "t",
            "q": text,
        }

        response = requests.get(
            url,
            params=params,
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

        if translated:
            return translated

        return text

    except Exception as e:

        print(
            "[TRANSLATE ERROR]",
            type(e).__name__,
            str(e)
        )

        return text


def translate_long_text(text):

    if not text:
        return ""

    text = text.strip()

    if len(text) <= 4500:

        return translate_to_indonesian(
            text
        )

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    chunks = []
    current = ""

    for sentence in sentences:

        if len(current) + len(sentence) > 4000:

            if current:
                chunks.append(
                    current
                )

            current = sentence

        else:

            if current:
                current += " "

            current += sentence

    if current:
        chunks.append(
            current
        )

    translated_chunks = []

    for chunk in chunks:

        translated_chunks.append(
            translate_to_indonesian(
                chunk
            )
        )

        time.sleep(0.3)

    return " ".join(
        translated_chunks
    )


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(text):

    if not text:
        return ""

    soup = BeautifulSoup(
        text,
        "html.parser"
    )

    return " ".join(
        soup.get_text(
            " ",
            strip=True
        ).split()
    )


def contains_keyword(text, keywords):

    if not text:
        return False

    text_lower = text.lower()

    return any(
        keyword.lower() in text_lower
        for keyword in keywords
    )


def is_blocked_news(text):

    if not text:
        return True

    return contains_keyword(
        text,
        BLOCKED_KEYWORDS
    )


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
# CATEGORY
# ============================================================

def detect_category(text):

    text_lower = text.lower()

    # Urutan penting agar kategori lebih tepat
    priority = [
        "💼 Tenaga Kerja",
        "🏦 Bank Sentral",
        "📊 Inflasi",
        "🛢️ Energi",
        "🌍 Geopolitik",
        "💵 Ekonomi AS",
    ]

    for category in priority:

        keywords = CATEGORY_KEYWORDS[
            category
        ]

        for keyword in keywords:

            if keyword.lower() in text_lower:
                return category

    return "📰 Market"


# ============================================================
# IMPACT
# ============================================================

def calculate_impact(text):

    if not text:
        return (
            "Low Impact",
            "⭐⭐"
        )

    text_lower = text.lower()

    score = 0

    for keyword in HIGH_IMPACT_KEYWORDS:

        if keyword.lower() in text_lower:
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
# GET ARTICLE
# ============================================================

def get_article(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:

            print(
                "[ARTICLE] HTTP:",
                response.status_code
            )

            return ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for element in soup(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "nav",
                "footer",
                "header",
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

        article_text = ""

        for selector in selectors:

            element = soup.select_one(
                selector
            )

            if element:

                text = clean_text(
                    element.get_text(
                        " ",
                        strip=True
                    )
                )

                if len(text) > len(
                    article_text
                ):

                    article_text = text

        if len(article_text) < 200:

            paragraphs = soup.find_all(
                "p"
            )

            article_text = " ".join(
                clean_text(
                    p.get_text(
                        " ",
                        strip=True
                    )
                )
                for p in paragraphs
            )

        return article_text

    except Exception as e:

        print(
            "[ARTICLE ERROR]",
            type(e).__name__,
            str(e)
        )

        return ""


# ============================================================
# MARKET ANALYSIS
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
        "Perhatikan arah dolar setelah "
        "rilis data atau kebijakan."
    )


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
            "Kenaikan yield dapat menekan Gold."
        )

    if any(
        x in lower
        for x in bearish
    ):

        return (
            "Penurunan yield dapat mendukung Gold."
        )

    return (
        "Pantau pergerakan US Treasury Yield."
    )


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

    results = []
    seen = set()

    links = soup.find_all(
        "a",
        href=True
    )

    for link in links:

        href = normalize_url(
            link.get(
                "href",
                ""
            )
        )

        title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        if not href or not title:
            continue

        if "/news/" not in href:
            continue

        if href in seen:
            continue

        seen.add(href)

        # ----------------------------------------------------
        # BLOKIR BERITA AGENDA / WEEK AHEAD
        # ----------------------------------------------------

        if is_blocked_news(title):

            print(
                "[FILTER] Blocked:",
                title
            )

            continue

        # ----------------------------------------------------
        # CEK RELEVANSI
        # ----------------------------------------------------

        relevant = (
            contains_keyword(
                title,
                GOLD_KEYWORDS
            )
            or contains_keyword(
                title,
                USD_KEYWORDS
            )
            or contains_keyword(
                title,
                YIELD_KEYWORDS
            )
            or contains_keyword(
                title,
                OIL_KEYWORDS
            )
            or contains_keyword(
                title,
                HIGH_IMPACT_KEYWORDS
            )
        )

        if not relevant:

            continue

        print(
            "[NEWS] Relevant:",
            title
        )

        # ----------------------------------------------------
        # AMBIL ARTIKEL
        # ----------------------------------------------------

        article = get_article(
            href
        )

        full_text = (
            title + " " + article
        )

        # ----------------------------------------------------
        # FILTER LAGI SETELAH MEMBACA ARTIKEL
        # ----------------------------------------------------

        if is_blocked_news(
            full_text
        ):

            print(
                "[FILTER] Blocked article:",
                title
            )

            continue

        # ----------------------------------------------------
        # IMPACT
        # ----------------------------------------------------

        impact, stars = calculate_impact(
            full_text
        )

        category = detect_category(
            full_text
        )

        # ----------------------------------------------------
        # ID UNIK
        # ----------------------------------------------------

        news_id = hashlib.sha256(
            href.encode("utf-8")
        ).hexdigest()

        # ----------------------------------------------------
        # TRANSLATE HEADLINE
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
        # HASIL
        # ----------------------------------------------------

        result = {

            "id": news_id,

            "title": translated_title,

            "summary": "",

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

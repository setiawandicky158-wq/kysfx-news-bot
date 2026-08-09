 import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib
import re


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

# Oil + WTI = SATU kategori
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
# HELPERS
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
    text = text.lower()

    return any(
        keyword.lower() in text
        for keyword in keywords
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

    for category, keywords in CATEGORY_KEYWORDS.items():

        for keyword in keywords:

            if keyword.lower() in text_lower:
                return category

    return "📰 Market"


# ============================================================
# IMPACT
# ============================================================

def calculate_impact(text):

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
# DOWNLOAD ARTICLE
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
                f"[ARTICLE] HTTP "
                f"{response.status_code}: {url}"
            )

            return ""

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Hapus elemen yang bukan isi artikel
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

        # Prioritas selector artikel
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

        # Fallback
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
            f"[ARTICLE ERROR] "
            f"{type(e).__name__}: {e}"
        )

        return ""


# ============================================================
# EXTRACT MARKET SECTION
# ============================================================

def extract_market_data(text):

    text_lower = text.lower()

    gold = ""
    usd = ""
    yield_data = ""
    oil = ""

    # --------------------------------------------------------
    # GOLD
    # --------------------------------------------------------

    gold_patterns = [
        r"gold[^.]{0,180}",
        r"gold[^,\n]{0,150}",
    ]

    for pattern in gold_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            gold = clean_text(
                match.group(0)
            )

            break

    # --------------------------------------------------------
    # YIELD
    # --------------------------------------------------------

    yield_patterns = [
        r"US 10-year yields?[^.]{0,180}",
        r"10-year yields?[^.]{0,180}",
        r"treasury yields?[^.]{0,180}",
    ]

    for pattern in yield_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            yield_data = clean_text(
                match.group(0)
            )

            break

    # --------------------------------------------------------
    # WTI / OIL
    # --------------------------------------------------------

    oil_patterns = [
        r"WTI[^.]{0,180}",
        r"oil[^.]{0,180}",
        r"crude oil[^.]{0,180}",
    ]

    for pattern in oil_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            oil = clean_text(
                match.group(0)
            )

            break

    # --------------------------------------------------------
    # USD
    # --------------------------------------------------------

    usd_patterns = [
        r"US dollar[^.]{0,180}",
        r"USD[^.]{0,180}",
        r"dollar[^.]{0,180}",
    ]

    for pattern in usd_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            usd = clean_text(
                match.group(0)
            )

            break

    return {
        "gold": gold,
        "usd": usd,
        "yield": yield_data,
        "oil": oil,
    }


# ============================================================
# ANALYSIS
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
            "🟢 Gold berpotensi bullish. "
            "Tunggu konfirmasi price action."
        )

    if any(
        x in lower
        for x in bearish
    ):
        return (
            "🔴 Gold berpotensi bearish. "
            "Tunggu konfirmasi price action."
        )

    if contains_keyword(
        text,
        GOLD_KEYWORDS
    ):
        return (
            "🟡 Potensi volatilitas tinggi. "
            "Tunggu reaksi harga."
        )

    return (
        "Pantau dampaknya terhadap Gold."
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
            "🟢 USD menguat. "
            "Berpotensi memberi tekanan pada Gold."
        )

    if any(
        x in lower
        for x in bearish
    ):
        return (
            "🔴 USD melemah. "
            "Berpotensi mendukung Gold."
        )

    return (
        "Perhatikan arah dolar setelah "
        "rilis data/kebijakan."
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
            "🔴 Kenaikan yield dapat "
            "menekan Gold."
        )

    if any(
        x in lower
        for x in bearish
    ):
        return (
            "🟢 Penurunan yield dapat "
            "mendukung Gold."
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
            "🟢 Oil/WTI berpotensi bullish. "
            "Tunggu konfirmasi harga."
        )

    if any(
        x in lower
        for x in bearish
    ):
        return (
            "🔴 Oil/WTI berpotensi bearish. "
            "Tunggu konfirmasi harga."
        )

    if contains_keyword(
        text,
        OIL_KEYWORDS
    ):
        return (
            "🟡 Perubahan Oil/WTI dapat "
            "mempengaruhi ekspektasi inflasi."
        )

    return (
        "Pantau dampaknya terhadap Oil/WTI."
    )


# ============================================================
# NEWS LIST
# ============================================================

def get_news(limit=10):

    print(
        "[NEWS] Loading InvestingLive..."
    )

    try:

        response = requests.get(
            NEWS_URL,
            headers=HEADERS,
            timeout=30
        )

        print(
            f"[NEWS] HTTP Status: "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

    except Exception as e:

        print(
            f"[NEWS ERROR] "
            f"{type(e).__name__}: {e}"
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

        # Hindari duplicate
        if href in seen:
            continue

        seen.add(href)

        # Filter market relevance
        title_lower = title.lower()

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
            f"[NEWS] Reading: {title}"
        )

        article = get_article(
            href
        )

        full_text = (
            f"{title} {article}"
        )

        impact, stars = calculate_impact(
            full_text
        )

        category = detect_category(
            full_text
        )

        market = extract_market_data(
            full_text
        )

        news_id = hashlib.sha256(
            href.encode("utf-8")
        ).hexdigest()

        result = {

            "id": news_id,

            "title": title,

            "summary": article[:1000],

            "link": href,

            "category": category,

            "impact": impact,

            "stars": stars,

            "gold_data": market["gold"],

            "usd_data": market["usd"],

            "yield_data": market["yield"],

            "oil_data": market["oil"],

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
        f"[NEWS] Relevant articles: "
        f"{len(results)}"
    )

    return results


# ============================================================
# TELEGRAM FORMAT
# ============================================================

def format_news(news):

    link = news.get(
        "link",
        ""
    )

    return (
        "🚨 <b>BREAKING NEWS</b>\n"
        f"📂 {news['category']}\n"
        f"📰 {news['title']}\n"
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

        f"🔗 <a href=\"{link}\">"
        "Sumber berita"
        "</a>"
    )

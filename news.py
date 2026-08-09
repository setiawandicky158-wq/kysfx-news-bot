import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib
import re
import time
import html


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
    "warsh",
    "interest rate",
    "rate cut",
    "rate hike",
    "rate decision",
]

YIELD_KEYWORDS = [
    "yield",
    "yields",
    "treasury",
    "treasury yield",
    "10-year",
    "10 year",
    "10y",
    "us10y",
    "bond yield",
]

# OIL + WTI SATU KATEGORI
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
    "crude inventories",
    "oil production",
    "oil supply",
    "oil demand",
    "eia",
]

HIGH_IMPACT_KEYWORDS = [
    "nfp",
    "nonfarm",
    "non-farm",
    "non-farm payrolls",
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
    "warsh",
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
# BLOCKED ARTICLES
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
        "warsh",
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
# ISTILAH YANG WAJIB DIPERTAHANKAN
# ============================================================

PROTECTED_TERMS = [
    "non-farm payrolls",
    "non-farm payroll",
    "nonfarm payrolls",
    "nonfarm payroll",
    "rate hike",
    "rate hikes",
    "rate cut",
    "rate cuts",
    "rate decision",
    "Fed",
    "FOMC",
    "Federal Reserve",
    "CPI",
    "PPI",
    "PCE",
    "GDP",
    "NFP",
    "JOLTS",
    "ISM",
    "PMI",
    "USD",
    "USD/JPY",
    "DXY",
    "XAUUSD",
    "Gold",
    "Treasury yield",
    "Treasury yields",
    "US Treasury",
    "US Treasury yield",
    "WTI",
    "Oil",
    "OPEC",
    "OPEC+",
    "EIA",
    "crude oil",
    "jobless claims",
    "retail sales",
    "central bank",
    "Fed funds",
    "Fed funds futures",
    "odds",
    "yield",
    "yields",
]


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = html.unescape(str(text))

    soup = BeautifulSoup(
        text,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    # Bersihkan prefix yang sering muncul
    prefixes = [
        "investingLive",
        "InvestingLive",
        "investinglive",
        "Investinglive",
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

    return text


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
# GET REAL TITLE
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
        og_title = soup.find(
            "meta",
            property="og:title"
        )

        if og_title:

            value = clean_text(
                og_title.get(
                    "content",
                    ""
                )
            )

            if value:
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

            if value:
                return value

        # TITLE
        title_tag = soup.find("title")

        if title_tag:

            value = clean_text(
                title_tag.get_text(
                    " ",
                    strip=True
                )
            )

            if value:

                value = re.sub(
                    r"\s*\|\s*investingLive.*$",
                    "",
                    value,
                    flags=re.IGNORECASE
                )

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
# GET ARTICLE SUMMARY
# ============================================================

def get_article_summary(url):

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

        # Hapus elemen yang bukan isi berita
        for element in soup.find_all(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "nav",
                "footer",
                "header",
                "aside",
                "form",
            ]
        ):
            element.decompose()

        # ====================================================
        # PRIORITAS SELECTOR
        # ====================================================

        selectors = [
            "[class*='article-body']",
            "[class*='article-content']",
            "[class*='post-content']",
            "[class*='entry-content']",
            "[class*='story-body']",
            "article",
        ]

        candidates = []

        for selector in selectors:

            elements = soup.select(
                selector
            )

            for element in elements:

                paragraphs = element.find_all(
                    "p"
                )

                texts = []

                for p in paragraphs:

                    text = clean_text(
                        p.get_text(
                            " ",
                            strip=True
                        )
                    )

                    if len(text) >= 30:
                        texts.append(text)

                if texts:

                    candidate = " ".join(
                        texts
                    )

                    candidates.append(
                        candidate
                    )

        # ====================================================
        # META DESCRIPTION
        # ====================================================

        meta = soup.find(
            "meta",
            attrs={
                "name": "description"
            }
        )

        if meta:

            meta_text = clean_text(
                meta.get(
                    "content",
                    ""
                )
            )

            if len(meta_text) >= 40:

                candidates.append(
                    meta_text
                )

        # ====================================================
        # PILIH KANDIDAT TERBAIK
        # ====================================================

        if not candidates:

            print(
                "[SUMMARY] No valid article summary"
            )

            return ""

        # Jangan ambil konten terlalu panjang
        # karena sering termasuk navigation/footer
        candidates = sorted(
            candidates,
            key=len,
            reverse=True
        )

        summary = candidates[0]

        # ====================================================
        # BUANG NOISE
        # ====================================================

        noise_patterns = [
            r"^Home\s+",
            r"^News\s+",
            r"^investingLive\s+",
            r"^InvestingLive\s+",
        ]

        for pattern in noise_patterns:

            summary = re.sub(
                pattern,
                "",
                summary,
                flags=re.IGNORECASE
            )

        # Hapus nama author + tanggal GMT
        summary = re.sub(
            r"\b[A-Z][A-Za-z]+\s+[A-Z][A-Za-z]+\s+\d{2}/\d{2}/\d{4}\s*\|\s*\d{2}:\d{2}\s*GMT\b",
            "",
            summary
        )

        summary = clean_text(
            summary
        )

        if len(summary) < 80:

            print(
                "[ARTICLE] Content too short"
            )

            return ""

        # Batasi summary
        if len(summary) > 1200:

            summary = summary[:1200]

            last_period = summary.rfind(".")

            if last_period > 500:

                summary = summary[
                    :last_period + 1
                ]

        print(
            "[SUMMARY] Summary found"
        )

        return summary

    except Exception as e:

        print(
            "[SUMMARY ERROR]",
            type(e).__name__,
            str(e)
        )

        return ""


# ============================================================
# PROTECT TERMS
# ============================================================

def protect_terms(text):

    if not text:
        return text, {}

    protected = {}

    # Urutkan dari yang paling panjang
    terms = sorted(
        PROTECTED_TERMS,
        key=len,
        reverse=True
    )

    counter = 0

    for term in terms:

        pattern = re.compile(
            re.escape(term),
            re.IGNORECASE
        )

        def replace(match):

            nonlocal counter

            key = f"ZZZTERM{counter}ZZZ"

            protected[key] = match.group(0)

            counter += 1

            return key

        text = pattern.sub(
            replace,
            text
        )

    return text, protected


# ============================================================
# RESTORE TERMS
# ============================================================

def restore_terms(
    text,
    protected
):

    if not text:
        return text

    for key, value in protected.items():

        text = text.replace(
            key,
            value
        )

        # Google kadang mengubah placeholder
        text = text.replace(
            key.lower(),
            value
        )

    return text


# ============================================================
# TRANSLATE
# ============================================================

def translate_to_indonesian(text):

    if not text:
        return ""

    text = clean_text(
        text
    )

    if not text:
        return ""

    protected_text, protected = protect_terms(
        text
    )

    try:

        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "en",
                "tl": "id",
                "dt": "t",
                "q": protected_text,
            },
            headers=HEADERS,
            timeout=25,
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

        translated = restore_terms(
            translated,
            protected
        )

        # ====================================================
        # PERBAIKAN ISTILAH
        # ====================================================

        replacements = {

            "kenaikan suku bunga":
                "rate hike",

            "penurunan suku bunga":
                "rate cut",

            "pemotongan suku bunga":
                "rate cut",

            "penggajian non-pertanian":
                "non-farm payrolls",

            "penggajian non pertanian":
                "non-farm payrolls",

            "penggajian non-pertanian":
                "non-farm payrolls",

            "Federal Reserve":
                "Fed",

            "Hasil Treasury":
                "Treasury yield",

            "hasil Treasury":
                "Treasury yield",

            "hasil obligasi":
                "bond yield",

            "odds":
                "odds",
        }

        for old, new in replacements.items():

            translated = re.sub(
                re.escape(old),
                new,
                translated,
                flags=re.IGNORECASE
            )

        return translated.strip()

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
        "dollar strengthens",
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
        "dollar declines",
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
        "treasury yields rise",
        "treasury yield rises",
    ]

    bearish = [
        "yields fall",
        "yield falls",
        "yields lower",
        "yield lower",
        "yields down",
        "yield down",
        "treasury yields fall",
        "treasury yield falls",
    ]

    if any(
        x in lower
        for x in bullish
    ):

        return (
            "Kenaikan Treasury yield dapat "
            "menekan Gold."
        )

    if any(
        x in lower
        for x in bearish
    ):

        return (
            "Penurunan Treasury yield dapat "
            "mendukung Gold."
        )

    return (
        "Pantau pergerakan US Treasury yield."
    )


# ============================================================
# OIL / WTI
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
    # AMBIL LINK
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

        raw_title = clean_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        if not href:
            continue

        if "/news/" not in href:
            continue

        if href in seen:
            continue

        seen.add(href)

        if is_blocked_title(
            raw_title
        ):

            print(
                "[FILTER] Blocked:",
                raw_title
            )

            continue

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
    # PROSES BERITA
    # ========================================================

    for raw_title, href in candidates:

        if len(results) >= limit:
            break

        print(
            "[NEWS] Checking:",
            raw_title
        )

        # ----------------------------------------------------
        # TITLE
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

        if is_blocked_title(
            real_title
        ):

            print(
                "[FILTER] Blocked:",
                real_title
            )

            continue

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        summary = get_article_summary(
            href
        )

        # ----------------------------------------------------
        # RELEVANCE
        # ----------------------------------------------------

        full_text = (
            real_title
            + " "
            + summary
        )

        relevant = (
            contains_keyword(
                full_text,
                GOLD_KEYWORDS
            )
            or contains_keyword(
                full_text,
                USD_KEYWORDS
            )
            or contains_keyword(
                full_text,
                YIELD_KEYWORDS
            )
            or contains_keyword(
                full_text,
                OIL_KEYWORDS
            )
            or contains_keyword(
                full_text,
                HIGH_IMPACT_KEYWORDS
            )
        )

        if not relevant:

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
        # IMPACT
        # ----------------------------------------------------

        impact, stars = calculate_impact(
            full_text
        )

        category = detect_category(
            full_text
        )

        # ----------------------------------------------------
        # ID
        # ----------------------------------------------------

        news_id = hashlib.sha256(
            href.encode(
                "utf-8"
            )
        ).hexdigest()

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

        if summary:

            print(
                "[TRANSLATE] English Summary:",
                summary[:500]
            )

            translated_summary = (
                translate_to_indonesian(
                    summary
                )
            )

            print(
                "[TRANSLATE] Indonesian Summary:",
                translated_summary[:500]
            )

        else:

            print(
                "[SUMMARY] No valid article summary"
            )

        # ----------------------------------------------------
        # RESULT
        # ----------------------------------------------------

        result = {

            "id": news_id,

            "title":
                translated_title,

            "summary":
                translated_summary,

            "link":
                href,

            "category":
                category,

            "impact":
                impact,

            "stars":
                stars,

            "gold":
                analyze_gold(
                    full_text
                ),

            "usd":
                analyze_usd(
                    full_text
                ),

            "yield":
                analyze_yield(
                    full_text
                ),

            "oil":
                analyze_oil(
                    full_text
                ),
        }

        results.append(
            result
        )

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

    title = news.get(
        "title",
        ""
    )

    summary = news.get(
        "summary",
        ""
    )

    category = news.get(
        "category",
        "📰 Market"
    )

    impact = news.get(
        "impact",
        "Market Impact"
    )

    stars = news.get(
        "stars",
        "⭐⭐⭐"
    )

    gold = news.get(
        "gold",
        "Potensi volatilitas tinggi. Tunggu reaksi harga."
    )

    usd = news.get(
        "usd",
        "Perhatikan arah USD setelah rilis data atau kebijakan."
    )

    yield_text = news.get(
        "yield",
        "Pantau pergerakan US Treasury yield."
    )

    oil = news.get(
        "oil",
        "Pantau dampaknya terhadap Oil/WTI."
    )

    link = news.get(
        "link",
        ""
    )

    message = (
        "🚨 <b>BREAKING NEWS</b>\n"
        f"📂 {category}\n\n"

        f"📰 <b>{title}</b>\n\n"
    )

    # Summary hanya ditampilkan kalau valid
    if summary:

        message += (
            f"📝 <b>Ringkasan:</b>\n"
            f"{summary}\n\n"
        )

    message += (
        f"⚠️ <b>{impact}</b> "
        f"{stars}\n\n"

        f"🟡 <b>Gold:</b>\n"
        f"{gold}\n\n"

        f"💵 <b>USD:</b>\n"
        f"{usd}\n\n"

        f"📈 <b>Yield:</b>\n"
        f"{yield_text}\n\n"

        f"🛢️ <b>Oil:</b>\n"
        f"{oil}\n\n"

        f'🔗 <a href="{link}">Sumber berita</a>'
    )

    return message

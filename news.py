import requests
from bs4 import BeautifulSoup


URL = "https://investinglive.com/news/"


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


def get_page():

    print("=" * 60)
    print("[TEST] InvestingLive News")

    try:

        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=30
        )

        print(
            f"[HTTP] Status: "
            f"{response.status_code}"
        )

        print(
            f"[HTTP] Content-Type: "
            f"{response.headers.get('content-type')}"
        )

        print(
            f"[HTTP] Size: "
            f"{len(response.content)} bytes"
        )

        if response.status_code != 200:

            print(
                "[ERROR] Halaman tidak dapat diakses."
            )

            return None

        return response.text

    except Exception as e:

        print(
            f"[ERROR] "
            f"{type(e).__name__}: {e}"
        )

        return None


def get_news(limit=20):

    html = get_page()

    if not html:

        return []

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    results = []

    # --------------------------------------------------------
    # Cari semua link artikel
    # --------------------------------------------------------

    links = soup.find_all(
        "a",
        href=True
    )

    seen = set()

    for link in links:

        href = link.get(
            "href",
            ""
        ).strip()

        title = link.get_text(
            " ",
            strip=True
        )

        if not href or not title:
            continue

        # Hanya artikel InvestingLive
        if "/news/" not in href:
            continue

        if not href.startswith("http"):

            href = (
                "https://investinglive.com"
                + href
            )

        if href in seen:
            continue

        seen.add(href)

        # ----------------------------------------------------
        # Filter judul yang relevan
        # ----------------------------------------------------

        text = title.lower()

        keywords = [
            "gold",
            "xau",
            "dollar",
            "usd",
            "fed",
            "fomc",
            "powell",
            "yield",
            "treasury",
            "nfp",
            "nonfarm",
            "payroll",
            "cpi",
            "inflation",
            "ppi",
            "oil",
            "wti",
            "crude",
            "opec",
            "eia",
            "gdp",
            "tariff",
            "sanction",
            "iran",
            "russia",
            "ukraine",
        ]

        if not any(
            keyword in text
            for keyword in keywords
        ):
            continue

        print(
            "[NEWS]",
            title
        )

        print(
            "[LINK]",
            href
        )

        results.append(
            {
                "title": title,
                "summary": "",
                "link": href,
                "category": "📰 Market",
                "impact": "Market Impact",
                "stars": "⭐⭐⭐",
                "gold": (
                    "Potensi volatilitas tinggi. "
                    "Tunggu reaksi harga."
                ),
                "usd": (
                    "Perhatikan arah dolar "
                    "setelah rilis data/kebijakan."
                ),
                "yield": (
                    "Pantau pergerakan "
                    "US Treasury Yield."
                ),
                "oil": (
                    "Perubahan minyak dapat "
                    "mempengaruhi ekspektasi inflasi."
                ),
            }
        )

        if len(results) >= limit:
            break

    print(
        f"[RESULT] "
        f"Relevant articles: {len(results)}"
    )

    return results


def format_news(news):

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

        f"🔗 <a href=\"{news['link']}\">"
        "Sumber berita</a>"
    )

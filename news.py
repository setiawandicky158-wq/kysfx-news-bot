 ```python
import requests
import feedparser


URLS = [
    "https://investinglive.com/rss/",
    "https://investinglive.com/rss/news/",
]


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def test_feed(url):

    print("=" * 60)
    print(f"[TEST] {url}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        print(f"[HTTP] Status: {response.status_code}")
        print(f"[HTTP] Content-Type: {response.headers.get('content-type')}")
        print(f"[HTTP] Size: {len(response.content)} bytes")

        feed = feedparser.parse(
            response.content
        )

        print(
            f"[RSS] Entries: {len(feed.entries)}"
        )

        if feed.bozo:
            print(
                f"[RSS] Parse warning: {feed.bozo_exception}"
            )

        for entry in feed.entries[:5]:

            print(
                "[NEWS]",
                entry.get(
                    "title",
                    "NO TITLE"
                )
            )

            print(
                "[LINK]",
                entry.get(
                    "link",
                    "NO LINK"
                )
            )

        return feed

    except Exception as e:

        print(
            f"[ERROR] {type(e).__name__}: {e}"
        )

        return None


def get_news(limit=20):

    all_news = []

    for url in URLS:

        feed = test_feed(url)

        if not feed:
            continue

        for entry in feed.entries[:limit]:

            title = entry.get(
                "title",
                ""
            ).strip()

            link = entry.get(
                "link",
                ""
            ).strip()

            if not title:
                continue

            all_news.append(
                {
                    "title": title,
                    "summary": entry.get(
                        "summary",
                        ""
                    ),
                    "link": link,
                    "category": "📰 Market",
                    "impact": "Market Impact",
                    "stars": "⭐⭐⭐",
                    "gold": "Potensi volatilitas tinggi. Tunggu reaksi harga.",
                    "usd": "Perhatikan arah dolar setelah rilis data/kebijakan.",
                    "yield": "Pantau pergerakan US Treasury Yield.",
                    "oil": "Perubahan minyak dapat mempengaruhi ekspektasi inflasi.",
                }
            )

    print(
        f"[RESULT] Total news: {len(all_news)}"
    )

    return all_news


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

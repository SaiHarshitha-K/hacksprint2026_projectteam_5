import requests
import feedparser
import json
from datetime import datetime

# -------------------------------
# RSS FEED CONFIG
# -------------------------------
RSS_FEEDS = {
    "Sports": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms",
    "Tech": "https://timesofindia.indiatimes.com/rssfeeds/66949542.cms",
    "India": "https://timesofindia.indiatimes.com/rssfeeds/29570699.cms",
    "Auto": "https://timesofindia.indiatimes.com/rssfeeds/733242.cms"
}

# -------------------------------
# FETCH RSS SAFELY
# -------------------------------
def fetch_rss(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return feedparser.parse(response.text)
    except Exception as e:
        print(f"[ERROR] Failed to fetch RSS: {url} | {e}")
        return None

# -------------------------------
# COLLECT ARTICLES FROM ALL FEEDS
# -------------------------------
def collect_articles():
    articles = []
    seen_urls = set()

    for category, url in RSS_FEEDS.items():
        feed = fetch_rss(url)
        if not feed or not feed.entries:
            continue

        for entry in feed.entries:
            link = entry.get("link", "").strip()
            if not link or link in seen_urls:
                continue

            seen_urls.add(link)

            article = {
                "title": entry.get("title", "").strip(),
                "url": link,
                "rss_category": category,
                "published_at": entry.get("published", ""),
                "article_text": ""  # to be filled by article_scraper.py
            }

            articles.append(article)

    return articles

# -------------------------------
# SAVE OUTPUT TO JSON
# -------------------------------
def save_to_json(data, filename="rss_output.json"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Saved output to {filename}")
    except Exception as e:
        print(f"[ERROR] Failed to save JSON: {e}")

# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    data = collect_articles()
    print(f"[SUCCESS] Fetched {len(data)} unique articles")

    if data:
        print("[SAMPLE RECORD]")
        print(json.dumps(data[0], indent=2, ensure_ascii=False))

    save_to_json(data)

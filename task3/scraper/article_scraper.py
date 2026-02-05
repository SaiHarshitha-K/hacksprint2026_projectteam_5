import requests
import time
from bs4 import BeautifulSoup
from pymongo import MongoClient

# -------------------------------
# MONGODB CONNECTION
# -------------------------------
client = MongoClient("mongodb://localhost:27017")
db = client.newsstream_db
collection = db.articles

# -------------------------------
# HEADERS
# -------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# -------------------------------
# FINAL ROBUST SCRAPER
# -------------------------------
def extract_article_text(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        text_blocks = []

        # Known TOI layouts (ordered by reliability)
        selectors = [
            "div.Normal p",                 # standard articles
            "div._s30J.clearfix p",          # liveblogs
            "div[class*='content'] p",       # generic TOI blocks
            "article p"                      # semantic fallback
        ]

        for selector in selectors:
            for p in soup.select(selector):
                t = p.get_text(strip=True)
                if t and len(t.split()) > 6:
                    text_blocks.append(t)

            if len(text_blocks) > 5:
                break

        # Last-resort fallback
        if not text_blocks:
            for p in soup.find_all("p"):
                t = p.get_text(strip=True)
                if t and len(t.split()) > 10:
                    text_blocks.append(t)

        return "\n".join(text_blocks)

    except Exception as e:
        print(f"[SCRAPE ERROR] {url}")
        return ""

# -------------------------------
# MAIN: RESCRAPE EMPTY ARTICLES
# -------------------------------
if __name__ == "__main__":
    docs = collection.find({ "article_text": "" })
    total = collection.count_documents({ "article_text": "" })
    print(f"[INFO] Re-scraping {total} empty articles")

    updated = 0

    for doc in docs:
        text = extract_article_text(doc["url"])

        if text:
            collection.update_one(
                { "_id": doc["_id"] },
                { "$set": {
                    "article_text": text,
                    "processed": False   # allow LLM re-run
                }}
            )
            updated += 1
            print(f"[UPDATED] {doc['title'][:60]}...")
        else:
            collection.update_one(
                { "_id": doc["_id"] },
                { "$set": { "scrape_status": "failed" } }
            )

        time.sleep(0.5)  # polite scraping

    print(f"[SUCCESS] Updated {updated} articles with text")

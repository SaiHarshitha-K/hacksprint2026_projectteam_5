import os
import json
from pymongo import MongoClient
import google.generativeai as genai

# -------------------------------
# GEMINI CONFIG
# -------------------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash"
)

# -------------------------------
# MONGODB CONNECTION
# -------------------------------
client = MongoClient("mongodb://localhost:27017")
db = client.newsstream_db
collection = db.articles

# -------------------------------
# SYSTEM PROMPT
# -------------------------------
SYSTEM_PROMPT = """
You are a news analysis assistant.

TASKS:
1. Write a concise summary (max 5 lines).
2. Classify the article into ONE category:
   - Political
   - Author Opinion
   - Threatful
   - Entertainment
3. Identify sentiment:
   - Positive
   - Neutral
   - Negative

RULES:
- Respond ONLY in valid JSON.
- No explanations.
- Use exactly these keys:
  summary, predicted_category, sentiment
"""

# -------------------------------
# LLM CALL
# -------------------------------
def analyze_article(article_text):
    prompt = SYSTEM_PROMPT + "\n\nARTICLE:\n" + article_text[:5000]

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json"
        }
    )

    return json.loads(response.text)

# -------------------------------
# MAIN PIPELINE
# -------------------------------
if __name__ == "__main__":
    cursor = collection.find({"processed": False})

    processed_count = 0

    for article in cursor:
        try:
            print(f"[PROCESSING] {article['title'][:60]}...")

            result = analyze_article(article["article_text"])

            collection.update_one(
                {"_id": article["_id"]},
                {"$set": {
                    "summary": result["summary"],
                    "predicted_category": result["predicted_category"],
                    "sentiment": result["sentiment"],
                    "processed": True
                }}
            )

            processed_count += 1

        except Exception as e:
            print(f"[ERROR] {article['url']} | {e}")

    print(f"[SUCCESS] Processed {processed_count} articles using Gemini-2.5-Flash")

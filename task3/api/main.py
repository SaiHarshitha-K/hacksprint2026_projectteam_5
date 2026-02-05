from fastapi import FastAPI, Request
from pymongo import MongoClient
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="NewsStream AI Dashboard")

# -------------------------------
# MONGODB
# -------------------------------
client = MongoClient("mongodb://localhost:27017")
db = client.newsstream_db
collection = db.articles

templates = Jinja2Templates(directory="api/templates")

# -------------------------------
# API HELPERS
# -------------------------------

def clean_match():
    """
    Exclude:
    - Empty summaries
    - 'No article content was provided'
    - Boilerplate TOI desk summaries
    """
    return {
        "processed": True,
        "summary": {
            "$nin": [None, ""],
            "$not": {
                "$regex": "No article content was provided|TOI Tech Desk",
                "$options": "i"
            }
        }
    }

# -------------------------------
# API ROUTES
# -------------------------------

@app.get("/stats/category")
def category_stats():
    pipeline = [
        {"$match": clean_match()},
        {
            "$group": {
                "_id": {
                    "$cond": [
                        {"$eq": ["$predicted_category", "Unknown"]},
                        "Author Opinion",
                        "$predicted_category"
                    ]
                },
                "count": {"$sum": 1}
            }
        }
    ]
    return list(collection.aggregate(pipeline))


@app.get("/stats/sentiment")
def sentiment_stats():
    pipeline = [
        {"$match": clean_match()},
        {"$group": {"_id": "$sentiment", "count": {"$sum": 1}}}
    ]
    return list(collection.aggregate(pipeline))


@app.get("/articles/latest")
def latest_articles(limit: int = 10):
    cursor = collection.find(
        clean_match(),
        {
            "title": 1,
            "summary": 1,
            "predicted_category": 1,
            "sentiment": 1
        }
    ).sort("_id", -1).limit(limit)

    return list(cursor)

# -------------------------------
# DASHBOARD UI
# -------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "categories": category_stats(),
            "sentiments": sentiment_stats(),
            "articles": latest_articles(10)
        }
    )

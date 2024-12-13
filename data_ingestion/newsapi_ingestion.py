import requests
import os
from database.db_setup import get_mongo_client
from user_management.preferences import get_user_preferences

API_KEY = os.getenv("NEWSAPI_KEY")
API_URL = "https://newsapi.org/v2/everything"

def fetch_news(query, page_size=10):
    params = {
        "q": query,
        "pageSize": page_size,
        "apiKey": API_KEY
    }
    response = requests.get(API_URL, params=params)
    if response.status_code == 200:
        return response.json()["articles"]
    else:
        print("Error:", response.status_code, response.text)
        return []

def save_news_to_db(query, user_id):
    preferences = get_user_preferences(user_id)
    topics = preferences.get("topics", [])
    sources = preferences.get("sources", [])
    
    # Filter the query to only include user preferences
    filtered_query = query if query in topics else topics
    
    articles = fetch_news(filtered_query)
    db = get_mongo_client()
    
    # Insert the articles with the user_id to associate them with the correct user
    for article in articles:
        article["user_id"] = user_id  # Add the user_id to each article
    db["news_articles"].insert_many(articles)
    print(f"Saved {len(articles)} articles to the database.")

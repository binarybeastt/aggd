import requests
import os
from database.db_setup import get_mongo_client
from user_management.preferences import get_user_preferences
from config.config_loader import NEWSAPI_KEY

API_KEY = NEWSAPI_KEY
API_URL = "https://newsapi.org/v2/everything"

def fetch_news(query, page_size=10):
    params = {
        "q": query,
        "pageSize": page_size,
        "apiKey": API_KEY
    }
    response = requests.get(API_URL, params=params)
    
    if response.status_code == 200:
        return response.json().get("articles", [])
    else:
        # Print full error message from the API
        print(f"Error occurred: HTTP {response.status_code}")
        print("Response Text:", response.text)
        
        # Optionally, you can parse the JSON error response if available
        try:
            error_details = response.json()  # Try to get detailed error message in JSON format
            print("Error Details:", error_details)
        except ValueError:
            print("Error response is not in JSON format.")
        
        return []

def save_news_to_db(query, user_id):
    preferences = get_user_preferences(user_id)
    topics = preferences.get("topics", [])
    sources = preferences.get("sources", [])
    
    # Filter the query to only include user preferences
    filtered_query = query if query in topics else topics
    
    articles = fetch_news(filtered_query)
    
    if not articles:
        # Print a message instead of raising an error to see what happens
        print("No articles returned from the API.")
    
    db = get_mongo_client()
    
    # If articles exist, insert them into the database
    if articles:
        for article in articles:
            article["user_id"] = user_id  # Add the user_id to each article
        db["news_articles"].insert_many(articles)
        print(f"Saved {len(articles)} articles to the database.")
    else:
        print("No articles to save.")

import requests
import os
from datetime import datetime
from database.db_setup import get_mongo_client
from config.config_loader import TWITTER_BEARER_TOKEN
from user_management.preferences import get_user_preferences

API_URL = "https://api.twitter.com/2/tweets/search/recent"

def fetch_tweets(query, max_results=10):
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "created_at,public_metrics"
    }
    response = requests.get(API_URL, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print("Error:", response.status_code, response.text)
        return []

def save_tweets_to_db(query, user_id):
    preferences = get_user_preferences(user_id)
    topics = preferences.get("topics", [])
    
    # Only fetch tweets related to the user's preferred topics
    if query not in topics:
        print(f"Query {query} is not in the user's preferences.")
        return
    
    tweets = fetch_tweets(query)
    db = get_mongo_client()
    
    # Insert tweets with user_id
    for tweet in tweets:
        tweet["user_id"] = user_id  # Add the user_id to each tweet
    db["tweets"].insert_many(tweets)
    print(f"Saved {len(tweets)} tweets to the database.")


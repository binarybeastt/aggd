import time
import requests
from database.db_setup import get_mongo_client
from user_management.preferences import get_user_preferences
from config.config_loader import BING_API_KEY

API_KEY = BING_API_KEY
ENDPOINT = "https://api.bing.microsoft.com/v7.0/news/search"
ARTICLES_PER_REQUEST = 3
DEFAULT_MARKET = 'en-US'

import os
from openai import OpenAI
from config.config_loader import OPENAI_API_KEY

# Specify your OpenAI API key and embedding model

model = "text-embedding-3-small"
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Define a function to generate embeddings
def get_embedding(text):
   """Generates vector embeddings for the given text."""

   embedding = openai_client.embeddings.create(input = [text], model=model).data[0].embedding
   return embedding

def fetch_news(query, page_size=10):
    """
    Fetch news articles from Bing News API and return them.
    """
    results = []
    offset = 0
    headers = {'Ocp-Apim-Subscription-Key': API_KEY}
    
    while len(results) < page_size:
        params = {
            'q': query,
            'mkt': DEFAULT_MARKET,
            'count': min(ARTICLES_PER_REQUEST, page_size - len(results)),
            'offset': offset
        }
        
        try:
            response = requests.get(ENDPOINT, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "value" in data:
                articles = data["value"]
                if not articles:
                    break
                
                transformed_articles = [{
                    "title": article["name"],
                    "snippet": article.get("description", ""),
                    "url": article["url"],
                    "publishedAt": article.get("datePublished", ""),
                    "source": {
                        "name": article.get("provider", [{}])[0].get("name", "Unknown")
                    }
                } for article in articles]
                
                results.extend(transformed_articles)
                offset += len(articles)
                
                if len(results) < page_size:
                    time.sleep(1)  # Respect API rate limits
            else:
                print(f"Unexpected API response format: {data}")
                break
        
        except requests.exceptions.RequestException as e:
            print(f"Error occurred: {e}")
            break
    
    return results[:page_size]

def save_news_to_db(query, user_id):
    """
    Fetch news based on user preferences, add embeddings, and save to database.
    """
    preferences = get_user_preferences(user_id)
    topics = preferences.get("topics", [])
    sources = preferences.get("sources", [])
    
    filtered_query = query if query in topics else topics[0] if topics else query
    articles = fetch_news(filtered_query)
    
    if not articles:
        print("No articles returned from the API.")
        return
    
    if sources:
        articles = [article for article in articles if article["source"]["name"] in sources]
    
    db = get_mongo_client()
    collection = db["news_articles"]
    
    for article in articles:
        try:
            # Add user_id, timestamp, and embedding
            article["user_id"] = user_id
            article["saved_at"] = time.time()
            article["embedding"] = get_embedding(article["snippet"])
            collection.insert_one(article)
            print(f"Saved article '{article['title']}' with embedding.")
        except Exception as e:
            print(f"Error saving article '{article['title']}': {e}")

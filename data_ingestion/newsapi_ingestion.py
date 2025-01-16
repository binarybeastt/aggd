import time
import requests
from database.db_setup import get_mongo_client
from user_management.preferences import get_user_preferences
from config.config_loader import BING_API_KEY

API_KEY = BING_API_KEY
ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
ARTICLES_PER_REQUEST = 3
DEFAULT_MARKET = 'en-US'

def fetch_news(query, page_size=10):
    """
    Fetch news articles from Bing News API
    
    Args:
        query (str): Search query
        page_size (int): Number of articles to retrieve
    
    Returns:
        list: List of articles
    """
    results = []
    offset = 0
    
    headers = {
        'Ocp-Apim-Subscription-Key': API_KEY
    }
    
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
            
            if "webPages" in data and "value" in data["webPages"]:
                articles = data["webPages"]["value"]
                if not articles:
                    break
                    
                # Transform Bing News format to match existing schema
                transformed_articles = [{
                    "title": article["name"],
                    "snippet": article.get("snippet", ""),  # Bing News API uses description for the snippet
                    "url": article["url"],
                    "publishedAt": article.get("datePublished", ""),
                    "source": {
                        "name": article.get("provider", [{}])[0].get("name", "Unknown")
                    }
                } for article in articles]
                
                results.extend(transformed_articles)
                offset += len(articles)
                
                # Respect API rate limits (3 transactions per second)
                if len(results) < page_size:
                    time.sleep(1)
            else:
                print(f"Unexpected API response format: {data}")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"Error occurred: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response text: {e.response.text}")
            break
            
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            break
    
    return results[:page_size]

def save_news_to_db(query, user_id):
    """
    Fetch news based on user preferences and save to database
    
    Args:
        query (str): Search query
        user_id (str): User identifier
    """
    preferences = get_user_preferences(user_id)
    topics = preferences.get("topics", [])
    sources = preferences.get("sources", [])
    
    # Filter the query to only include user preferences
    filtered_query = query if query in topics else topics[0] if topics else query
    
    articles = fetch_news(filtered_query)
    
    if not articles:
        print("No articles returned from the API.")
        return
    
    # Filter articles by preferred sources if specified
    if sources:
        articles = [
            article for article in articles 
            if article["source"]["name"] in sources
        ]
    
    db = get_mongo_client()
    
    if articles:
        # Add user_id and timestamp to each article
        for article in articles:
            article["user_id"] = user_id
            article["saved_at"] = time.time()
            
        try:
            db["news_articles"].insert_many(articles)
            print(f"Saved {len(articles)} articles to the database.")
        except Exception as e:
            print(f"Database error: {str(e)}")
    else:
        print("No articles to save after filtering.")
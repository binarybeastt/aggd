import time
import requests
from pprint import pprint

# Function to perform Bing Web Search
def bing_web_search(query, offset=0):
    subscription_key = '42e77e31f4da4b2da3a01d621c6d2a01'
    endpoint = "https://api.bing.microsoft.com/v7.0/search"
    if not subscription_key or not endpoint:
        raise ValueError("Environment variables for API key and endpoint are not set.")

    # Parameters for the API call
    params = {
        'q': query,
        'mkt': 'en-US',
        'count': 3,   # Retrieve 3 articles per request
        'offset': offset
    }
    headers = {'Ocp-Apim-Subscription-Key': subscription_key}

    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

# Query
query = "Artificial Intelligence"
total_results = 10  # Total number of articles needed
results = []
articles_per_request = 3  # Bing API returns 3 results per request
offset = 0

while len(results) < total_results:
    # Fetch results
    response = bing_web_search(query, offset=offset)
    if response and "webPages" in response:
        articles = response["webPages"]["value"]
        results.extend(articles[:total_results - len(results)])  # Limit to required count
        offset += len(articles)
    
    # Check if more results are available
    if not response or "webPages" not in response or not response["webPages"]["value"]:
        print("No more results available.")
        break

    # Respect API rate limits (3 transactions per second)
    if len(results) < total_results:
        time.sleep(1)

# Print the results
print(f"\nRetrieved {len(results)} articles:\n")
for i, article in enumerate(results, 1):
    print(f"{i}. Title: {article['name']}")
    print(f"   URL: {article['url']}")
    print(f"   Snippet: {article['snippet']}\n")

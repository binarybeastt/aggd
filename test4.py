import requests

# Replace with your actual Bing Search API key
api_key = "42e77e31f4da4b2da3a01d621c6d2a01"
url = "https://api.bing.microsoft.com/v7.0/news/search"

# Define the parameters for your query
params = {
    'q': 'technology',  # The search query (e.g., 'technology', 'business', etc.)
    'count': 10,        # Number of results per page
    'mkt': 'en-US',     # Market (e.g., 'en-US' for English, US)
    'freshness': 'Day'  # Freshness of the results ('Day', 'Week', 'Month')
}

# Set the headers for authentication
headers = {
    'Ocp-Apim-Subscription-Key': api_key
}

# Send GET request
response = requests.get(url, headers=headers, params=params)

# Check if request was successful
if response.status_code == 200:
    data = response.json()
    # Print the headlines of the news results
    for item in data['value']:
        print(item['name'], item['url'])
else:
    print(f"Error: {response.status_code}, {response.text}")

import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Twitter API Keys
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")

# Reddit API Keys
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")

# NewsAPI Key
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

# MongoDB URI
MONGO_URI = os.getenv("MONGO_URI")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")

# Optional: Validate critical variables
def validate_env_vars():
    required_vars = {
        "TWITTER_BEARER_TOKEN": TWITTER_BEARER_TOKEN,
        "TWITTER_API_KEY": TWITTER_API_KEY,
        "TWITTER_API_SECRET": TWITTER_API_SECRET,
        "REDDIT_CLIENT_ID": REDDIT_CLIENT_ID,
        "REDDIT_CLIENT_SECRET": REDDIT_CLIENT_SECRET,
        "NEWSAPI_KEY": NEWSAPI_KEY,
        "MONGO_URI": MONGO_URI,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "TAVILY_API_KEY": TAVILY_API_KEY,
        "BING_API_KEY": BING_API_KEY
    }
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")

# Call the validation (optional, to catch issues early)
validate_env_vars()
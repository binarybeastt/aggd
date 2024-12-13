import os
import praw
from database.db_setup import get_mongo_client

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="my_user_agent"
)

def fetch_reddit_posts(subreddit_name, limit=10):
    subreddit = reddit.subreddit(subreddit_name)
    posts = []
    for submission in subreddit.hot(limit=limit):
        posts.append({
            "title": submission.title,
            "content": submission.selftext,
            "timestamp": submission.created_utc,
            "score": submission.score,
            "comments_count": submission.num_comments,
            "subreddit": subreddit_name
        })
    return posts

def save_posts_to_db(user_id, subreddit_name):
    posts = fetch_reddit_posts(subreddit_name)
    db = get_mongo_client()
    for post in posts:
        post["user_id"] = user_id  # Add user ID
        post["source"] = "Reddit"
    db["reddit_posts"].insert_many(posts)
    print(f"Saved {len(posts)} posts from r/{subreddit_name} for user {user_id}.")

import os
import json
import uuid
from fastapi import FastAPI, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.exceptions import HTTPException
from fastapi import Request
from user_management.auth import signup_user, login_user, get_current_user
from user_management.preferences import update_user_preferences, get_user_preferences
from user_management.fcm_router import fcm_router
from user_management.models import UserCreate, UserLogin, PreferencesUpdate
from data_ingestion.newsapi_ingestion import save_news_to_db
from data_ingestion.reddit_ingestion import save_posts_to_db
from data_ingestion.twitter_ingestion import save_tweets_to_db
from summarizer.notification_scheduler import NotificationScheduler
from summarizer.summ import UserContentSummarizer 
from summarizer.summary_retriever import get_summary_by_id
from notifications.notifications_retriever import get_summary_by_notification, get_user_notifications
from chat_s.s_chat import RAGChatService
from chat.retrieval_graph import graph
from typing import List, Optional
from bson import ObjectId
from database.db_setup import get_mongo_client
from config.config_loader import OPENAI_API_KEY, TAVILY_API_KEY
from pydantic import BaseModel
import logging
logger = logging.getLogger(__name__)

class QuestionRequest(BaseModel):
    question: str
    user_id: int

class QuestionResponse(BaseModel):
    response: str

db = get_mongo_client()

notification_scheduler = NotificationScheduler()
app = FastAPI()
app.include_router(fcm_router, prefix="/api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://web-tau-three-18.vercel.app"],  # Allows all origins (adjust for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
# app.mount("/static", StaticFiles(directory="web"), name="static")


# # In your main FastAPI app file
# @app.get("/{catch_all:path}")
# async def serve_react_app(catch_all: str):
#     return FileResponse(os.path.join("web", "index.html"))

# @app.get("/actions/")
# async def actions_page():
#     return FileResponse(os.path.join("web", "actions.html"))

@app.post("/signup/")
async def signup(user: UserCreate):
    return signup_user(email=user.email, username=user.username, password=user.password)

@app.post("/login/")
async def login(user: UserLogin):
    token = login_user(email=user.email, password=user.password)
    return {"access_token": token, "token_type": "bearer"}

@app.put("/preferences/")
async def preferences(preferences: PreferencesUpdate, current_user: dict = Depends(get_current_user)):
    return update_user_preferences(
        current_user=current_user,
        topics=preferences.topics,
        sources=preferences.sources,
        notification_times=preferences.notification_times
    )

@app.get("/get_preferences/")
async def get_preferences(current_user: dict = Depends(get_current_user)):
    return get_user_preferences(current_user)

@app.get("/ingest/news/")
async def ingest_news(user_id: str = Depends(get_current_user)):
    preferences = get_user_preferences(user_id)
    topics = preferences.get("topics", [])
    for topic in topics:
        save_news_to_db(query=topic, user_id=user_id)
    return {"message": "News ingestion completed based on user preferences."}

@app.get("/ingest/reddit/")
async def ingest_reddit(user_id: str = Depends(get_current_user)):
    preferences = get_user_preferences(user_id)
    sources = preferences.get("sources", [])
    for subreddit in sources:
        save_posts_to_db(subreddit_name=subreddit, user_id=user_id)
    return {"message": "Reddit ingestion completed based on user preferences."}

@app.get("/ingest/twitter/")
async def ingest_twitter(user_id: str = Depends(get_current_user)):
    preferences = get_user_preferences(user_id)
    topics = preferences.get("topics", [])
    for topic in topics:
        save_tweets_to_db(query=topic, user_id=user_id)
    return {"message": "Twitter ingestion completed based on user preferences."}

@app.get("/summarize/recent_articles/")
async def summarize_recent_articles(current_user: dict = Depends(get_current_user)):
    summarizer = UserContentSummarizer()
    results = summarizer.summarize_recent_user_articles(user_id=str(current_user['_id']))
    # try:
    #     # This is a manual method to send notifications immediately
    #     await notification_scheduler._send_notification(str(current_user['_id']))
    # except Exception as e:
    #     print(f"Notification sending error: {e}")
    
    return {"message": f"Summarized {len(results)} articles", "summaries": results}

@app.get("/summaries/{summary_id}")
async def get_summary(summary_id: str, current_user: dict = Depends(get_current_user)):
    summary = get_summary_by_id(summary_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    # Optional: Add additional authorization check
    if str(current_user['_id']) != summary['user_id']['_id']:
        raise HTTPException(status_code=403, detail="Unauthorized to access this summary")
    
    return summary

@app.post("/test_notifications/")
async def test_notifications(current_user: dict = Depends(get_current_user)):
    try:
        # Directly use the _send_notification method for testing
        await notification_scheduler._send_notification(str(current_user['_id']))
        return {"message": "Test notification sent successfully"}
    except Exception as e:
        return {"error": f"Failed to send test notification: {str(e)}"}
    
# @app.post("/api/chat/{summary_id}")
# async def chat_endpoint(request:Request, summary_id: str, current_user: dict = Depends(get_current_user)):
#     try:
#         body_bytes = await request.body()
#         body_str = body_bytes.decode('utf-8')
#         body = json.loads(body_str)

#         query = body.get('query')
#         chat_history = body.get('chat_history', [])
#         if not query:
#             raise HTTPException(status_code=400, detail="Query is required")
        
#         if not isinstance(chat_history, list):
#             raise HTTPException(status_code=400, detail="Chat history must be a list")
        
#         # Verify user has access to this summary
#         # Convert chat history to expected format if needed
#         parsed_chat_history = [
#             {'role': item.get('role'), 'content': item.get('content')}
#             for item in chat_history if item.get('role') and item.get('content')
#         ] if chat_history else None

#         summary = get_summary_by_id(summary_id)

#         print(summary.keys())

#         rag_service.process_combined_text(
#             summary_id, 
#             summary['combined_summaries']
#         )
        
#         # Generate response
#         response = rag_service.generate_chat_response(
#             summary_id, 
#             query, 
#             parsed_chat_history
#         )

#         print(response)
        
#         return {
#             "response": response,
#             "summary_id": summary_id
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/{summary_id}")
async def ask_question(request: Request, summary_id:str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user['_id'])
    try:
        question = await request.json()
        response = await graph.process_stream(question['question'], user_id=user_id)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/summaries/{summary_id}/init-thread")
async def initialize_thread(summary_id: str, current_user: dict = Depends(get_current_user)):
    thread_id = str(uuid.uuid4())
    
    # Update the summary document with the thread_id
    result = await db.article_summaries.update_one(
        {"_id": ObjectId(summary_id)},
        {"$set": {"thread_id": thread_id}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Summary not found")
        
    return {"thread_id": thread_id}


# @app.post("/api/chat/{summary_id}")
# async def chat_endpoint(request: Request, summary_id: str, current_user: dict = Depends(get_current_user)):
#     try:
#         # Parse request body
#         body_bytes = await request.body()
#         body_str = body_bytes.decode('utf-8')
#         body = json.loads(body_str)

#         query = body.get('query')
#         if not query:
#             raise HTTPException(status_code=400, detail="Query is required")
        
#         # Verify user has access to this summary
#         summary = get_summary_by_id(summary_id)

#         # Initialize RAG service (ensure this is done per request to maintain isolation)
#         rag_service = RAGChatService(
#             openai_api_key=OPENAI_API_KEY,
#             tavily_api_key=TAVILY_API_KEY
#         )

#         # Prepare context using summary and source articles
#         rag_service.prepare_context(
#             source_articles=summary
#         )
        
#         # Generate response
#         response = rag_service.generate_chat_response(query)
#         print(response)
#         # Optional: cleanup after response generation
#         rag_service.cleanup()
        
#         return {
#             "response": response,
#             "summary_id": summary_id
#         }

#     except Exception as e:
#         # Log the error for debugging
#         logger.error(f"Chat endpoint error: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

@app.get("/user_notifications/")
async def user_notifications(current_user: dict = Depends(get_current_user)):
    """Fetch the notification history for the current user."""
    user_id = str(current_user['_id'])  # Convert ObjectId to string
    
    # Retrieve all notifications for the current user, sorted by timestamp
    notifications = list(db['notifications'].find(
        {'user_id': user_id},
        {'summary_id': 1, 'timestamp': 1}
    ).sort('timestamp', -1))
    
    # Convert ObjectIds to strings
    for notification in notifications:
        notification['_id'] = str(notification['_id'])

    print(notifications)
    
    return notifications

@app.get("/notification_summary/{notification_id}")
async def notification_summary(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch the summary associated with a specific notification."""
    user_id = str(current_user['_id'])
    
    # Find the specific notification
    notification = db['notifications'].find_one({
        '_id': ObjectId(notification_id), 
        'user_id': user_id
    })
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Retrieve the associated summary
    summary = get_summary_by_id(notification['summary_id'])
    
    if not summary:
        raise HTTPException(status_code=404, detail="Associated summary not found")
    
    return summary

# @app.get("/summary_by_notification/{notification_id}")
# async def summary_by_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
#     """Fetch the summary related to a specific notification for the current user."""
#     user_id = str(current_user['_id'])
#     summary = get_summary_by_notification(notification_id, user_id)

#     if summary and '_id' in summary and isinstance(summary['_id'], ObjectId):
#         summary['_id'] = str(summary['_id'])

#     return summary
    
@fcm_router.post("/trigger_notification/{user_id}")
async def trigger_notification(user_id: str):
    """Manually trigger a notification for a user."""
    try:
        # Initialize NotificationScheduler
        scheduler = NotificationScheduler()
        
        # Call the private method to send notification
        await scheduler._send_notification(user_id)
        
        return {"success": True, "message": f"Notification manually triggered for user {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    

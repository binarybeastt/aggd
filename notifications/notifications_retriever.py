from typing import Dict, Optional
from bson import ObjectId
from database.db_setup import get_mongo_client
from fastapi.exceptions import HTTPException

def get_user_notifications(user_id: str):
    """Fetch the notification history for a specific user."""

    db = get_mongo_client()
    return db['notifications'].find({'user_id': user_id}).sort('timestamp', -1)

def get_summary_by_notification(notification_id: str, user_id: str):
    """Fetch the summary related to a specific notification for the current user."""

    db = get_mongo_client()
    notification = db['notifications'].find_one({'_id': ObjectId(notification_id), 'user_id': user_id})
    
    if notification:
        summary_id = notification.get('summary_id')
        summary = db['article_summaries'].find_one({'_id': ObjectId(summary_id)})
        if summary:
            return summary
    raise HTTPException(status_code=404, detail="Notification or related summary not found")
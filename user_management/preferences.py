from datetime import datetime
from bson import ObjectId
import json
from pymongo import MongoClient
from fastapi import HTTPException
from config.config_loader import MONGO_URI
from database.db_setup import get_mongo_client

db = get_mongo_client() 
preferences_collection = db["user_preferences"] 

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

def update_user_preferences(current_user: dict, topics: list[str], sources: list[str], notification_times: list[str]):
    preferences = {
        "user_id": {
            "_id": ObjectId(current_user['_id']),
            "email": current_user['email'],
            "username": current_user['username'],
            "created_at": current_user['created_at']
        },
        "topics": topics,
        "sources": sources,
        "notification_times": notification_times,
        "updated_at": datetime.utcnow().isoformat(),
    }
    preferences_collection.update_one(
        {"user_id._id": ObjectId(current_user['_id'])}, 
        {"$set": preferences}, 
        upsert=True
    )
    return {"message": "Preferences updated successfully!"}

def get_user_preferences(current_user: dict):
    preferences = preferences_collection.find_one({"user_id._id": ObjectId(current_user['_id'])})
    
    if not preferences:
        raise HTTPException(status_code=404, detail="User preferences not found.")
    
    # Convert ObjectId to string in the entire document
    preferences['_id'] = str(preferences['_id'])
    preferences['user_id']['_id'] = str(preferences['user_id']['_id'])
    
    return preferences

from pymongo import MongoClient
import os
from config.config_loader import MONGO_URI

def get_mongo_client():
    client = MongoClient(MONGO_URI)
    return client["content_db"]

mongo_client = get_mongo_client()


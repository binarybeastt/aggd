from pymongo import MongoClient
import os

def get_mongo_client():
    client = MongoClient(os.getenv("MONGO_URI", "mongodb+srv://devintechy:inqR1pIdtsUbjgGp@cluster0.b9w9m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"))
    return client["content_db"]


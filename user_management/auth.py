from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, FastAPI, Form
from fastapi.security import OAuth2PasswordBearer
from pymongo import MongoClient
from passlib.context import CryptContext
from jose import jwt, JWTError
from typing import Optional
from bson import ObjectId
from config.config_loader import MONGO_URI
from database.db_setup import get_mongo_client

# OAuth2PasswordBearer setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # Changed from "login" to match standard convention

# JWT Configuration
SECRET_KEY = "your_secret_key"  # Should be moved to environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Added token expiration

# MongoDB Setup
db = get_mongo_client()
users_collection = db["users"]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt(user_id: str, email: str) -> str:
    # Added proper expiration time
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow()  # Added issued at time
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_jwt(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:  # Changed return type
    payload = verify_jwt(token)
    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token or expired token",
            headers={"WWW-Authenticate": "Bearer"}  # Added proper headers
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found in token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify the user exists in the database
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})  # Added ObjectId conversion
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Remove password hash before returning
        user.pop("password_hash", None)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )

def signup_user(email: str, username: Optional[str], password: str):
    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    try:
        hashed_password = hash_password(password)
        user = {
            "email": email,
            "username": username,
            "password_hash": hashed_password,
            "created_at": datetime.utcnow()
        }
        result = users_collection.insert_one(user)
        
        # Return user without password hash
        user["_id"] = str(result.inserted_id)
        user.pop("password_hash", None)
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error creating user")

def login_user(email: str = Form(...), password: str = Form(...)):
    user = users_collection.find_one({"email": email})
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create access token
    token = create_jwt(user_id=str(user["_id"]), email=user["email"])
    return {
        "access_token": token,
        "token_type": "bearer"
    }
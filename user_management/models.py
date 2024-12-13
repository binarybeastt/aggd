from pydantic import BaseModel, EmailStr
from typing import Optional, List

# Schema for user creation
class UserCreate(BaseModel):
    email: EmailStr
    username: Optional[str]
    password: str

# Schema for user login
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Schema for storing user in database
class UserInDB(BaseModel):
    id: str
    email: EmailStr
    username: Optional[str]
    password_hash: str
    created_at: str

# Schema for updating user preferences
class PreferencesUpdate(BaseModel):
    topics: List[str]
    sources: List[str]
    notification_times: List[str]

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from database.db_setup import get_mongo_client
from user_management.auth import get_current_user

fcm_router = APIRouter()

class FCMTokenRequest(BaseModel):
    fcm_token: str

@fcm_router.post("/register-fcm-token")
async def register_fcm_token(
    request: FCMTokenRequest, 
    current_user: dict = Depends(get_current_user)
):
    db = get_mongo_client()
    
    result = db['users'].update_one(
        {'_id': current_user['_id']},
        {'$set': {'fcm_token': request.fcm_token}}
    )
    
    return {"success": result.modified_count > 0}
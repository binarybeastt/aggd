from typing import Dict, Optional
from bson import ObjectId
from database.db_setup import get_mongo_client

def get_summary_by_id(summary_id: str) -> Optional[Dict]:
    """
    Retrieve a summary document by its unique ID
    
    Args:
        summary_id (str): Unique MongoDB ObjectId of the summary
    
    Returns:
        Optional[Dict]: Complete summary document or None if not found
    """
    try:
        db = get_mongo_client()
        summary = db['article_summaries'].find_one({'_id': ObjectId(summary_id)})
        
        if summary:
            # Convert ObjectId to string for JSON serialization
            summary['_id'] = str(summary['_id'])
            summary['user_id']['_id'] = str(summary['user_id']['_id'])
        
        return summary
    
    except Exception as e:
        # Log the error if needed
        print(f"Error retrieving summary: {str(e)}")
        return None
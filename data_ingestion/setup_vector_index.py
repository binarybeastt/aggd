from pymongo.operations import SearchIndexModel
from pymongo import MongoClient

def get_mongo_client():
    client = MongoClient("")
    return client["content_db"]

def setup_vector_index():
    """
    Creates a vector search index for news articles.
    Only needs to be run once during initial setup or if the index needs to be rebuilt.
    """
    try:
        db = get_mongo_client()
        collection = db["news_articles"]
        
        # Check if index already exists
        existing_indexes = collection.list_search_indexes()
        for index in existing_indexes:
            if index.get("name") == "vector_index":
                print("Vector index already exists.")
                return

        # Create the search index model
        search_index_model = SearchIndexModel(
            definition={
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": 1536,  # text-embedding-3-small dimension
                        "similarity": "cosine"  # or "dotProduct" based on your preference
                    }
                ]
            },
            name="vector_index",
            type="vectorSearch"
        )

        # Create the index
        collection.create_search_index(model=search_index_model)
        print("Vector index created successfully.")

    except Exception as e:
        print(f"Error creating vector index: {e}")

def verify_or_rebuild_index():
    """
    Utility function to verify index health and rebuild if necessary.
    Can be used for maintenance or troubleshooting.
    """
    try:
        db = get_mongo_client()
        collection = db["news_articles"]
        
        # Check existing indexes
        existing_indexes = collection.list_search_indexes()
        index_exists = False
        index_healthy = True
        
        for index in existing_indexes:
            if index.get("name") == "vector_index":
                index_exists = True
                # Add any additional health checks here if needed
                if not index.get("status") == "READY":
                    index_healthy = False
                break
        
        if not index_exists or not index_healthy:
            print("Index needs to be created or rebuilt.")
            # Drop existing index if it exists but is unhealthy
            if index_exists:
                collection.drop_search_index("vector_index")
                print("Dropped existing unhealthy index.")
            
            setup_vector_index()
        else:
            print("Vector index is healthy and ready to use.")
            
    except Exception as e:
        print(f"Error verifying or rebuilding index: {e}")
        raise 

if __name__ == "__main__":
    # Run this script once during initial setup
    setup_vector_index()
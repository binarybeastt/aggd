from typing import List, AsyncGenerator
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableConfig
from pymongo import MongoClient
from contextlib import contextmanager

class CustomMongoDBRetriever:
    def __init__(self, mongo_uri: str, embedding_model: Embeddings, search_kwargs: dict = None):
        self.client = MongoClient(mongo_uri)
        self.db = self.client["content_db"]
        self.collection = self.db["news_articles"]
        self.embedding_model = embedding_model
        self.search_kwargs = search_kwargs or {
            "k": 4,
            "numCandidates": 100
        }

    async def ainvoke(self, query: str, config: RunnableConfig) -> List[Document]:
        """Async invoke method that matches the exact interface expected by the retrieve function."""
        # Generate embedding for the query
        embedding = self.embedding_model.embed_query(query)
        
        # Perform vector search
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": embedding,
                    "numCandidates": self.search_kwargs.get("numCandidates", 100),
                    "limit": self.search_kwargs.get("k", 4)
                }
            },
            {
                "$project": {
                    "score": {"$meta": "vectorSearchScore"},
                    "text": 1,
                    "content": 1,
                    "page_content": 1,
                    "title": 1,
                    "_id": 0
                }
            }
        ]

        results = list(self.collection.aggregate(pipeline))
        
        # Convert to Documents
        documents = []
        for doc in results:
            content = (
                doc.get("content") or 
                doc.get("text") or 
                doc.get("page_content") or 
                doc.get("title", "")
            )
            if content:
                documents.append(Document(
                    page_content=content,
                    metadata={"score": doc.get("score")}
                ))
        
        return documents

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
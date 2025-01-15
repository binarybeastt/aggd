import os
import uuid
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import tavily
from openai import OpenAI
import chromadb
from chromadb import PersistentClient
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

class TemporaryVectorStoreManager:
    def __init__(self, base_storage_path="./chroma_storage", expiration_hours=24):
        self.base_storage_path = base_storage_path
        self.expiration_hours = expiration_hours
        self._cleanup_old_stores()
    
    def _cleanup_old_stores(self):
        """Remove vector stores older than the expiration time"""
        if not os.path.exists(self.base_storage_path):
            os.makedirs(self.base_storage_path)
        
        for folder in os.listdir(self.base_storage_path):
            full_path = os.path.join(self.base_storage_path, folder)
            
            try:
                folder_time = datetime.fromtimestamp(float(folder))
                if datetime.now() - folder_time > timedelta(hours=self.expiration_hours):
                    shutil.rmtree(full_path)
            except (ValueError, OSError):
                try:
                    shutil.rmtree(full_path)
                except OSError:
                    pass
    
    def create_vector_store(self, embeddings):
        """
        Create a new temporary vector store with a unique path
        
        Args:
            embeddings: Embedding function to use
        
        Returns:
            Tuple of (vector_store, store_path)
        """
        unique_timestamp = str(datetime.now().timestamp())
        store_path = os.path.join(self.base_storage_path, unique_timestamp)
        
        chroma_client = PersistentClient(path=store_path)
        collection_name = f"chat_{uuid.uuid4().hex}"
        
        vector_store = Chroma(
            client=chroma_client,
            collection_name=collection_name,
            embedding_function=embeddings
        )
        
        return vector_store, store_path

class ArticleExtractor:
    def __init__(self, tavily_api_key):
        self.tavily_client = tavily.TavilyClient(api_key=tavily_api_key)
    
    def extract_articles(self, source_articles: List[Dict], max_tokens: int = 4000) -> List[Dict]:
        """
        Extract content for unique URLs from the 'source_articles' list.
        
        Args:
            source_articles (List[Dict]): List of source articles
            max_tokens (int): Maximum tokens to extract per article
        
        Returns:
            List of extracted article contents
        """
        unique_urls = {article['url'] for article in source_articles}
        
        extracted_contents = []
        for url in unique_urls:
            try:
                extract_result = self.tavily_client.extract(
                    urls=[url],  # Extract content for each unique URL
                    max_tokens=max_tokens
                )
                
                # Find the article title from the source articles
                title = next((art['title'] for art in source_articles if art['url'] == url), '')
                
                extracted_contents.append({
                    'url': url,
                    'content': extract_result.get('content', ''),
                    'title': title
                })
            
            except Exception as e:
                print(f"Error extracting {url}: {e}")
        
        return extracted_contents

class RAGChatService:
    def __init__(self, openai_api_key: str, tavily_api_key: str):
        """
        Initialize RAG Chat Service
        
        Args:
            openai_api_key (str): OpenAI API Key
            tavily_api_key (str): Tavily API Key
        """
        # Managers and Clients
        self.article_extractor = ArticleExtractor(tavily_api_key)
        self.vector_store_manager = TemporaryVectorStoreManager()
        
        # Embeddings
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=openai_api_key,
            model="text-embedding-3-small"
        )
        
        # OpenAI Client
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Current chat context
        self.current_vector_store = None
        self.current_store_path = None
    
    def prepare_context(self, source_articles: List[Dict]):
        """
        Prepare context by extracting full article contents
        
        Args:
            source_articles (List[Dict]): List of source articles
        
        Returns:
            Prepared vector store
        """
        # Extract full article contents
        extracted_articles = self.article_extractor.extract_articles(source_articles)
        
        # Combine article contents
        combined_texts = [
            f"Article from {art['url']}:\n{art['content']}" 
            for art in extracted_articles
        ]
        
        # Create vector store
        self.current_vector_store, self.current_store_path = self.vector_store_manager.create_vector_store(self.embeddings)
        
        # Add texts to vector store
        self.current_vector_store.add_texts(
            texts=combined_texts,
            metadatas=[
                {
                    'type': 'article', 
                    'url': art['url'], 
                    'title': art['title']
                } 
                for art in extracted_articles
            ]
        )
        
        return self.current_vector_store
    
    def retrieve_context(self, query: str, top_k: int = 3) -> List[str]:
        """
        Retrieve the most relevant context for a query
        
        Args:
            query (str): User's query
            top_k (int): Number of context chunks to retrieve
        
        Returns:
            List of most relevant context chunks
        """
        if not self.current_vector_store:
            return []
        
        # Perform similarity search
        results = self.current_vector_store.similarity_search(query, k=top_k)
        
        return [result.page_content for result in results]
    
    def generate_chat_response(
        self, 
        query: str, 
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate a contextual response using RAG
        
        Args:
            query (str): User's query
            chat_history (Optional[List[Dict]]): Previous conversation context
        
        Returns:
            str: Generated response
        """
        # Retrieve context
        context = self.retrieve_context(query)
        
        # Prepare context string
        context_str = "\n---\n".join(context) if context else "No additional context available."
        
        # Prepare chat history
        history_str = ""
        if chat_history:
            history_str = "\n".join(
                [f"{msg['role']}: {msg['content']}" for msg in chat_history[-5:]]
            )
        
        # Construct comprehensive prompt
        full_prompt = f"""
        Context: {context_str}
        Previous Chat History: {history_str}
        
        User Query: {query}
        
        Provide a helpful, contextually relevant response that:
        - Directly addresses the user's query
        - Leverages information from the context
        - Maintains conversation coherence
        """
        # Generate response
        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": full_prompt},
            ],
        )
        
        return response.choices[0].message.content
    
    def cleanup(self):
        """
        Cleanup current vector store
        """
        if self.current_store_path and os.path.exists(self.current_store_path):
            shutil.rmtree(self.current_store_path)
        
        self.current_vector_store = None
        self.current_store_path = None

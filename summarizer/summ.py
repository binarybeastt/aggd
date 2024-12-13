from database.db_setup import get_mongo_client
from config.config_loader import OPENAI_API_KEY
from openai import OpenAI
import os
import json
import logging
from bson import ObjectId
from datetime import datetime

class UserContentSummarizer:
    def __init__(self):
        """
        Initialize summarizer with MongoDB and OpenAI clients
        """
        self.db = get_mongo_client()
        self.news_collection = self.db['news_articles']
        self.summary_collection = self.db['article_summaries']
        
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def summarize_recent_user_articles(self, user_id: str, limit: int = 10):
        """
        Create a combined summary of recent articles with references and a brief highlight
        """
        try:
            # Get recent articles
            recent_articles = list(self.news_collection.find(
                {'user_id._id': ObjectId(user_id)}
            ).sort('publishedAt', -1).limit(limit))
            
            if not recent_articles:
                return None
                
            # First get individual summaries and keep track of articles for references
            article_summaries = []
            for article in recent_articles:
                text = article.get('content')
                if not text:
                    continue
                    
                article_summaries.append({
                    'summary': self._generate_single_summary(text),
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'id': str(article['_id'])  # Convert ObjectId to string
                })

            # Create text for overall summarization with reference points
            combined_text = "Here are the key points from multiple articles:\n\n"
            for i, article in enumerate(article_summaries, 1):
                combined_text += f"Article {i}: {article['summary']}\n\n"

            # Generate overall summary with reference points and highlight
            overall_summary = self._generate_overall_summary(combined_text, article_summaries)
            print(overall_summary)
            
            # Create summary document with string IDs
            summary_doc = {
                'user_id': {
                    '_id': str(recent_articles[0]['user_id']['_id']),  # Convert ObjectId to string
                    'email': recent_articles[0]['user_id']['email'],
                    'username': recent_articles[0]['user_id']['username'],
                    'created_at': recent_articles[0]['user_id']['created_at']
                },
                'combined_summaries': combined_text, # For the concatenated summaries  
                'detailed_summary': overall_summary['detailed_summary'],
                'highlight_summary': overall_summary['highlight'],
                'source_articles': [{
                    'article_id': art['id'],
                    'title': art['title'],
                    'url': art['url']
                } for art in article_summaries],
                'created_at': datetime.utcnow()
            }
            
            # Store in MongoDB - the stored version will have ObjectIds
            stored_doc = self.summary_collection.insert_one(summary_doc)
            
            # For the return value, make sure we have the stored document's ID as a string
            summary_doc['_id'] = str(stored_doc.inserted_id)
            
            return summary_doc
            
        except Exception as e:
            self.logger.error(f"Error in summarize_recent_user_articles: {e}")
            raise


    def _generate_single_summary(self, text: str):
        """Generate a simple summary for a single article"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Create a concise one-paragraph summary of the key points."
                    },
                    {
                        "role": "user",
                        "content": f"Summarize this text:\n\n{text[:4000]}"
                    }
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"Error generating single summary: {e}")
            return "Summary generation failed"

    def _generate_overall_summary(self, combined_text: str, articles: list):
        """Generate overall summary with references and a highlight"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Create a JSON response with two elements:
                        1. detailed_summary: A comprehensive summary (2-3 paragraphs) that synthesizes 
                        all the information. Insert [CITE_X] tags (where X is the article number) 
                        at appropriate points to reference source articles.
                        2. highlight: A very concise (2 sentences max) summary of the most important 
                        overall points, the highlight doesn't need citations."""
                    },
                    {
                        "role": "user",
                        "content": f"Create a summary with citations from these articles:\n\n{combined_text}"
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            summary_data = json.loads(response.choices[0].message.content)
            
            # Replace citation tags with actual links
            detailed_summary = summary_data['detailed_summary']
            for i, article in enumerate(articles, 1):
                cite_tag = f"[CITE_{i}]"
                if cite_tag in detailed_summary:
                    detailed_summary = detailed_summary.replace(
                        cite_tag,
                        f"[{article['title']}]({article['url']})"
                    )
            
            return {
                "detailed_summary": detailed_summary,
                "highlight": summary_data['highlight']
            }
            
        except Exception as e:
            self.logger.error(f"Error generating overall summary: {e}")
            return {
                "detailed_summary": "Error generating overall summary",
                "highlight": "Error generating highlight"
            }
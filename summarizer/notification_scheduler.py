import firebase_admin
from firebase_admin import credentials, messaging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database.db_setup import get_mongo_client
from datetime import datetime
import logging
import pytz
from typing import List, Dict
from bson import ObjectId

class NotificationScheduler:
    def __init__(self):
        self.db = get_mongo_client()
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger(__name__)
        
        # Collections
        self.users_collection = self.db['users']
        self.summary_collection = self.db['article_summaries']

        # Initialize Firebase Admin SDK
        cred = credentials.Certificate('/etc/secrets/smart-notifications-9caa0-firebase-adminsdk-xt9d4-0ed2832b13.json')
        firebase_admin.initialize_app(cred)

        
        # Initialize scheduler
        self._init_scheduler()

    def _init_scheduler(self):
        """Initialize the scheduler and add default jobs"""
        if not self.scheduler.running:
            self.scheduler.start()
            # Add a job to check and update user schedules daily
            self.scheduler.add_job(
                self._update_user_schedules,
                CronTrigger(hour=0, minute=0),  # Run at midnight
                id='update_schedules',
                replace_existing=True
            )

    async def _update_user_schedules(self):
        """Update notification schedules for all users"""
        users = self.users_collection.find({})
        for user in users:
            await self.schedule_user_notifications(user)

    async def schedule_user_notifications(self, user: Dict):
        """Schedule notifications for a specific user based on their preferences"""
        try:
            user_id = str(user['_id'])
            notification_times = user.get('preferences', {}).get('notification_times', [])
            
            # Remove existing schedules for this user
            existing_jobs = [job for job in self.scheduler.get_jobs() 
                           if job.id.startswith(f'notify_user_{user_id}')]
            for job in existing_jobs:
                self.scheduler.remove_job(job.id)
            
            # Schedule new notifications
            for time in notification_times:
                hour, minute = map(int, time.split(':'))
                job_id = f'notify_user_{user_id}_{time}'
                
                self.scheduler.add_job(
                    self._send_notification,
                    CronTrigger(hour=hour, minute=minute),
                    id=job_id,
                    args=[user_id],
                    replace_existing=True
                )
                
            self.logger.info(f"Scheduled notifications for user {user_id} at times: {notification_times}")
            
        except Exception as e:
            self.logger.error(f"Error scheduling notifications for user {user_id}: {e}")

    async def _send_notification(self, user_id: str):
        """Send notification to user with recent summaries"""
        # try:
        # Get recent summaries for user
        recent_summaries = list(self.summary_collection.find(
        {'user_id._id': user_id}
    ).sort('created_at', -1).limit(5))


        print(recent_summaries)
        
        if not recent_summaries:
            return
        
        # Format notification content
        notification_content = self._format_notification_content(recent_summaries)
        
        # Here you would integrate with your preferred notification service
        # Examples: Email, Push Notifications, SMS, etc.
        await self._send_to_notification_service(user_id, notification_content)
            
        # except Exception as e:
        #     self.logger.error(f"Error sending notification to user {user_id}: {e}")

    def _format_notification_content(self, summaries: List[Dict]) -> Dict:
        return {
            "title": "Your Recent Article Summaries",
            "body": "\n\n".join([
                f"📰 {summary['highlight_summary']}"
                for summary in summaries
            ]),
            "data": {
                "summary_id": str(summaries[0]['_id'])
            }
        }

    async def _send_to_notification_service(self, user_id: str, content: Dict):
        """Send Firebase Cloud Messaging notification and log the result with summary_id."""
        # Fetch user's FCM token from the database
        db = get_mongo_client()
        user = db['users'].find_one({'_id': ObjectId(user_id)})

        if not user or 'fcm_token' not in user:
            self.logger.warning(f"No FCM token found for user {user_id}")
            return

        # Add the `data` field to the FCM message (with summary_id included)
        message = messaging.Message(
            notification=messaging.Notification(
                title=content['title'],
                body=content['body']
            ),
            data=content['data'],  # 'summary_id' is part of content['data']
            token=user['fcm_token']
        )

        # Send a message to the device corresponding to the provided registration token
        try:
            response = messaging.send(message)
            self.logger.info(f"Successfully sent message to {user_id}: {response}")

            # Log the notification as 'sent' in the notifications collection
            notification_data = {
                "user_id": user_id,
                "summary_id": content['data']['summary_id'],  # Store the summary_id
                "status": "sent",
                "timestamp": datetime.utcnow(),
                "response": response  # Log the Firebase response
            }
            # Insert notification log into the database
            db['notifications'].insert_one(notification_data)
        except Exception as e:
            # Log the notification as 'failed' in the notifications collection
            self.logger.error(f"Error sending notification to user {user_id}: {e}")
            notification_data = {
                "user_id": user_id,
                "summary_id": content['data']['summary_id'],  # Store the summary_id
                "status": "failed",
                "timestamp": datetime.utcnow(),
                "response": str(e)  # Log the error message
            }
            # Insert failed notification log into the database
            db['notifications'].insert_one(notification_data)


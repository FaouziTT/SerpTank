"""
Notification service for managing and sending notifications.

This service handles various types of notifications including
in-app notifications, email notifications, and real-time updates.
"""
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import asyncio
from collections import defaultdict
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload

from app.core.structured_logging import get_logger
from app.models.user import User

logger = get_logger(__name__)


class NotificationType(str, Enum):
    """Types of notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRAWL_COMPLETE = "crawl_complete"
    CRAWL_FAILED = "crawl_failed"
    REPORT_READY = "report_ready"
    SYSTEM_ALERT = "system_alert"
    PROJECT_UPDATE = "project_update"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    WEBSOCKET = "websocket"


class NotificationService:
    """Service for managing notifications."""
    
    def __init__(self):
        self.websocket_handlers = defaultdict(list)
        self.pending_notifications = defaultdict(list)
        self.notification_queue = asyncio.Queue()
        self._processing_task = None
        
    async def send_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None,
        priority: str = "normal",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Send a notification to a user.
        
        Args:
            user_id: ID of the user to notify
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional data for the notification
            channels: Channels to use (defaults to in-app and websocket)
            priority: Notification priority (low, normal, high)
            db: Database session (optional)
            
        Returns:
            Notification data
        """
        if channels is None:
            channels = [NotificationChannel.IN_APP, NotificationChannel.WEBSOCKET]
            
        notification = {
            "id": f"notif_{user_id}_{datetime.now(timezone.utc).timestamp()}",
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "channels": channels,
            "priority": priority,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False
        }
        
        # Add to queue for processing
        await self.notification_queue.put(notification)
        
        # Log the notification
        logger.info(
            f"Notification queued: {notification_type} for user {user_id}",
            extra={
                "notification": notification,
                "user_id": user_id
            }
        )
        
        return notification
        
    async def send_bulk_notifications(
        self,
        user_ids: List[int],
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None,
        priority: str = "normal"
    ) -> List[Dict[str, Any]]:
        """
        Send notifications to multiple users.
        
        Args:
            user_ids: List of user IDs to notify
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional data for the notification
            channels: Channels to use
            priority: Notification priority
            
        Returns:
            List of notification data
        """
        notifications = []
        
        for user_id in user_ids:
            notification = await self.send_notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data,
                channels=channels,
                priority=priority
            )
            notifications.append(notification)
            
        return notifications
        
    async def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        notification_types: Optional[List[NotificationType]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            notification_types: Filter by notification types
            limit: Maximum number of notifications to return
            
        Returns:
            List of notifications
        """
        # Get pending notifications for the user
        user_notifications = self.pending_notifications.get(user_id, [])
        
        # Apply filters
        if unread_only:
            user_notifications = [n for n in user_notifications if not n.get("read", False)]
            
        if notification_types:
            user_notifications = [
                n for n in user_notifications 
                if n.get("type") in notification_types
            ]
            
        # Sort by created_at (newest first) and apply limit
        user_notifications.sort(
            key=lambda n: n.get("created_at", ""),
            reverse=True
        )
        
        return user_notifications[:limit]
        
    async def mark_notification_read(
        self,
        user_id: int,
        notification_id: str
    ) -> bool:
        """
        Mark a notification as read.
        
        Args:
            user_id: User ID
            notification_id: Notification ID
            
        Returns:
            True if notification was marked as read
        """
        user_notifications = self.pending_notifications.get(user_id, [])
        
        for notification in user_notifications:
            if notification.get("id") == notification_id:
                notification["read"] = True
                notification["read_at"] = datetime.now(timezone.utc).isoformat()
                return True
                
        return False
        
    async def mark_all_read(self, user_id: int) -> int:
        """
        Mark all notifications as read for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of notifications marked as read
        """
        user_notifications = self.pending_notifications.get(user_id, [])
        count = 0
        
        for notification in user_notifications:
            if not notification.get("read", False):
                notification["read"] = True
                notification["read_at"] = datetime.now(timezone.utc).isoformat()
                count += 1
                
        return count
        
    def register_websocket_handler(
        self,
        user_id: int,
        handler: callable
    ) -> None:
        """
        Register a WebSocket handler for real-time notifications.
        
        Args:
            user_id: User ID
            handler: Async function to handle notifications
        """
        self.websocket_handlers[user_id].append(handler)
        logger.debug(f"WebSocket handler registered for user {user_id}")
        
    def unregister_websocket_handler(
        self,
        user_id: int,
        handler: callable
    ) -> None:
        """
        Unregister a WebSocket handler.
        
        Args:
            user_id: User ID
            handler: Handler function to remove
        """
        if handler in self.websocket_handlers.get(user_id, []):
            self.websocket_handlers[user_id].remove(handler)
            logger.debug(f"WebSocket handler unregistered for user {user_id}")
            
            # Clean up empty lists
            if not self.websocket_handlers[user_id]:
                del self.websocket_handlers[user_id]
                
    async def _process_notifications(self) -> None:
        """
        Process notifications from the queue.
        
        This method runs continuously to process notifications.
        """
        while True:
            try:
                # Get notification from queue with timeout
                notification = await asyncio.wait_for(
                    self.notification_queue.get(),
                    timeout=1.0
                )
                
                user_id = notification["user_id"]
                channels = notification.get("channels", [])
                
                # Process each channel
                if NotificationChannel.IN_APP in channels:
                    # Store in-app notification
                    self.pending_notifications[user_id].append(notification)
                    
                    # Limit stored notifications per user
                    if len(self.pending_notifications[user_id]) > 100:
                        self.pending_notifications[user_id].pop(0)
                        
                if NotificationChannel.WEBSOCKET in channels:
                    # Send via WebSocket if handlers are registered
                    handlers = self.websocket_handlers.get(user_id, [])
                    if handlers:
                        # Send to all handlers concurrently
                        tasks = [
                            asyncio.create_task(handler(notification))
                            for handler in handlers
                        ]
                        
                        # Wait with timeout
                        try:
                            await asyncio.wait_for(
                                asyncio.gather(*tasks, return_exceptions=True),
                                timeout=5.0
                            )
                        except asyncio.TimeoutError:
                            logger.warning(
                                f"Timeout sending WebSocket notification to user {user_id}"
                            )
                            
                if NotificationChannel.EMAIL in channels:
                    # TODO: Implement email sending
                    logger.info(
                        f"Email notification queued for user {user_id}: {notification['title']}"
                    )
                    
            except asyncio.TimeoutError:
                # No notifications to process
                continue
            except Exception as e:
                logger.error(f"Error processing notification: {e}", exc_info=True)
                
    async def start_processing(self) -> None:
        """Start the notification processing task."""
        if self._processing_task is None:
            self._processing_task = asyncio.create_task(self._process_notifications())
            logger.info("Notification processing started")
            
    async def stop_processing(self) -> None:
        """Stop the notification processing task."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("Notification processing stopped")
            
    async def get_notification_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get notification statistics.
        
        Args:
            user_id: Optional user ID for user-specific stats
            
        Returns:
            Notification statistics
        """
        if user_id:
            notifications = self.pending_notifications.get(user_id, [])
            unread_count = sum(1 for n in notifications if not n.get("read", False))
            
            return {
                "user_id": user_id,
                "total_notifications": len(notifications),
                "unread_count": unread_count,
                "has_websocket": user_id in self.websocket_handlers
            }
        else:
            # Global stats
            total_notifications = sum(
                len(notifs) for notifs in self.pending_notifications.values()
            )
            total_unread = sum(
                sum(1 for n in notifs if not n.get("read", False))
                for notifs in self.pending_notifications.values()
            )
            
            return {
                "total_users": len(self.pending_notifications),
                "total_notifications": total_notifications,
                "total_unread": total_unread,
                "websocket_connections": len(self.websocket_handlers),
                "queue_size": self.notification_queue.qsize()
            }


# Global notification service instance
notification_service = NotificationService()
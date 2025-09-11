"""
Notification Service for managing user notifications.

This service handles creating, sending, and managing notifications
with support for real-time WebSocket delivery.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.models.notification import (
    Notification, NotificationType, NotificationCategory,
    UserNotificationPreference
)
from app.models.user import User
from app.core.websocket import manager
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications."""
    
    async def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        category: NotificationCategory = NotificationCategory.GENERAL,
        data: Optional[Dict[str, Any]] = None,
        action_url: Optional[str] = None,
        organization_id: Optional[int] = None,
        project_id: Optional[int] = None,
        site_id: Optional[int] = None,
        priority: int = 0,
        expires_in_hours: Optional[int] = None,
        send_email: bool = False,
        send_realtime: bool = True
    ) -> Notification:
        """
        Create a new notification for a user.
        
        Args:
            user_id: ID of the user to notify
            title: Notification title
            message: Notification message
            type: Type of notification
            category: Category for grouping
            data: Additional JSON data
            action_url: URL to navigate to when clicked
            organization_id: Related organization ID
            project_id: Related project ID
            site_id: Related site ID
            priority: Priority level (higher = more important)
            expires_in_hours: Auto-delete after this many hours
            send_email: Whether to also send email
            send_realtime: Whether to send via WebSocket
            
        Returns:
            Created notification
        """
        try:
            async with async_session_factory() as db:
                # Check user preferences
                prefs = await self._get_user_preferences(db, user_id)
                
                # Determine delivery methods based on preferences
                deliver_email = send_email and self._should_send_email(prefs, category)
                
                # Create notification
                notification = Notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    type=type,
                    category=category,
                    data=data,
                    action_url=action_url,
                    organization_id=organization_id,
                    project_id=project_id,
                    site_id=site_id,
                    priority=priority,
                    deliver_email=deliver_email,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours) if expires_in_hours else None
                )
                
                db.add(notification)
                await db.commit()
                await db.refresh(notification)
                
                # Send real-time notification if enabled
                if send_realtime and manager.is_user_online(user_id):
                    await self._send_realtime_notification(notification)
                
                # Queue email notification if needed
                if deliver_email:
                    await self._queue_email_notification(notification)
                
                logger.info(f"Created notification {notification.id} for user {user_id}")
                return notification
                
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            raise
    
    async def create_bulk_notifications(
        self,
        user_ids: List[int],
        title: str,
        message: str,
        **kwargs
    ) -> List[Notification]:
        """Create notifications for multiple users."""
        notifications = []
        
        for user_id in user_ids:
            try:
                notification = await self.create_notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    **kwargs
                )
                notifications.append(notification)
            except Exception as e:
                logger.error(f"Error creating notification for user {user_id}: {e}")
                
        return notifications
    
    async def create_organization_notification(
        self,
        organization_id: int,
        title: str,
        message: str,
        **kwargs
    ) -> List[Notification]:
        """Create notifications for all users in an organization."""
        async with async_session_factory() as db:
            # Get all active users in the organization
            result = await db.execute(
                select(User.id).where(
                    and_(
                        User.organization_id == organization_id,
                        User.is_active == True
                    )
                )
            )
            user_ids = [row[0] for row in result]
            
        return await self.create_bulk_notifications(
            user_ids=user_ids,
            title=title,
            message=message,
            organization_id=organization_id,
            **kwargs
        )
    
    async def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        category: Optional[NotificationCategory] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get notifications for a user."""
        async with async_session_factory() as db:
            query = select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_archived == False
                )
            )
            
            if unread_only:
                query = query.where(Notification.is_read == False)
                
            if category:
                query = query.where(Notification.category == category)
                
            query = query.order_by(
                Notification.priority.desc(),
                Notification.created_at.desc()
            ).limit(limit).offset(offset)
            
            result = await db.execute(query)
            return result.scalars().all()
    
    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(func.count(Notification.id)).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read == False,
                        Notification.is_archived == False
                    )
                )
            )
            return result.scalar() or 0
    
    async def mark_as_read(
        self,
        notification_ids: List[int],
        user_id: int
    ) -> int:
        """Mark notifications as read."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.id.in_(notification_ids),
                        Notification.user_id == user_id
                    )
                )
            )
            notifications = result.scalars().all()
            
            count = 0
            for notification in notifications:
                if not notification.is_read:
                    notification.mark_as_read()
                    count += 1
                    
            await db.commit()
            
            # Send real-time update
            if count > 0 and manager.is_user_online(user_id):
                await manager.send_user_message(
                    {
                        "type": "notifications_read",
                        "notification_ids": notification_ids,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    user_id
                )
            
            return count
    
    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(Notification.id).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read == False,
                        Notification.is_archived == False
                    )
                )
            )
            notification_ids = [row[0] for row in result]
            
        if notification_ids:
            return await self.mark_as_read(notification_ids, user_id)
        return 0
    
    async def archive_notifications(
        self,
        notification_ids: List[int],
        user_id: int
    ) -> int:
        """Archive notifications."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.id.in_(notification_ids),
                        Notification.user_id == user_id
                    )
                )
            )
            notifications = result.scalars().all()
            
            count = 0
            for notification in notifications:
                notification.is_archived = True
                count += 1
                
            await db.commit()
            return count
    
    async def cleanup_expired_notifications(self) -> int:
        """Delete expired notifications."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.expires_at.isnot(None),
                        Notification.expires_at < datetime.now(timezone.utc)
                    )
                )
            )
            notifications = result.scalars().all()
            
            count = len(notifications)
            for notification in notifications:
                await db.delete(notification)
                
            await db.commit()
            logger.info(f"Cleaned up {count} expired notifications")
            return count
    
    async def _get_user_preferences(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Optional[UserNotificationPreference]:
        """Get user notification preferences."""
        result = await db.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
    
    def _should_send_email(
        self,
        prefs: Optional[UserNotificationPreference],
        category: NotificationCategory
    ) -> bool:
        """Check if email should be sent based on preferences."""
        if not prefs or not prefs.email_enabled:
            return False
            
        category_map = {
            NotificationCategory.PERFORMANCE: prefs.email_performance_alerts,
            NotificationCategory.SECURITY: prefs.email_security_alerts,
            NotificationCategory.BILLING: prefs.email_billing_alerts,
            NotificationCategory.TEAM: prefs.email_team_updates,
        }
        
        return category_map.get(category, True)
    
    async def _send_realtime_notification(self, notification: Notification) -> None:
        """Send notification via WebSocket."""
        await manager.send_user_message(
            {
                "type": "notification",
                "notification": notification.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            notification.user_id
        )
    
    async def _queue_email_notification(self, notification: Notification) -> None:
        """Queue notification for email delivery."""
        # This would integrate with your email service
        # For now, just log it
        logger.info(f"Email notification queued: {notification.id}")


# Create singleton instance
notification_service = NotificationService()


# Notification creation helpers
async def notify_performance_alert(
    user_id: int,
    site_name: str,
    metric: str,
    value: float,
    threshold: float,
    site_id: int
) -> Notification:
    """Create a performance alert notification."""
    return await notification_service.create_notification(
        user_id=user_id,
        title=f"Performance Alert: {site_name}",
        message=f"{metric} has exceeded threshold: {value:.2f} (threshold: {threshold:.2f})",
        type=NotificationType.ALERT,
        category=NotificationCategory.PERFORMANCE,
        site_id=site_id,
        action_url=f"/sites/{site_id}/performance",
        priority=2,
        send_email=True
    )


async def notify_security_event(
    user_id: int,
    event_type: str,
    description: str,
    organization_id: Optional[int] = None
) -> Notification:
    """Create a security event notification."""
    return await notification_service.create_notification(
        user_id=user_id,
        title=f"Security Alert: {event_type}",
        message=description,
        type=NotificationType.SECURITY,
        category=NotificationCategory.SECURITY,
        organization_id=organization_id,
        priority=3,
        send_email=True
    )


async def notify_team_update(
    user_ids: List[int],
    title: str,
    message: str,
    project_id: Optional[int] = None,
    organization_id: Optional[int] = None
) -> List[Notification]:
    """Create team update notifications."""
    return await notification_service.create_bulk_notifications(
        user_ids=user_ids,
        title=title,
        message=message,
        type=NotificationType.INFO,
        category=NotificationCategory.TEAM,
        project_id=project_id,
        organization_id=organization_id,
        send_email=False
    )
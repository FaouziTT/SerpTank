"""
Activity tracking service for monitoring user and system events.

This service provides real-time activity tracking and notification
capabilities for various events in the application.
"""
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from enum import Enum
import asyncio
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.core.structured_logging import get_logger
from app.models.user import User
from app.models.project import Project
from app.models.crawl import Crawl
from app.models.audit_log import AuditLog

logger = get_logger(__name__)


class ActivityType(str, Enum):
    """Types of activities that can be tracked."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"
    CRAWL_STARTED = "crawl_started"
    CRAWL_COMPLETED = "crawl_completed"
    CRAWL_FAILED = "crawl_failed"
    REPORT_GENERATED = "report_generated"
    SETTINGS_UPDATED = "settings_updated"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"


class ActivityService:
    """Service for tracking and managing activity events."""
    
    def __init__(self):
        self.activity_listeners = defaultdict(list)
        self.recent_activities = []
        self.max_recent_activities = 100
        
    async def track_activity(
        self,
        activity_type: ActivityType,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Track an activity event.
        
        Args:
            activity_type: Type of activity
            user_id: ID of the user performing the activity
            project_id: ID of the related project (if applicable)
            resource_id: ID of the related resource
            metadata: Additional metadata about the activity
            db: Database session (optional)
            
        Returns:
            Activity event data
        """
        activity = {
            "type": activity_type,
            "user_id": user_id,
            "project_id": project_id,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add to recent activities (in-memory)
        self.recent_activities.append(activity)
        if len(self.recent_activities) > self.max_recent_activities:
            self.recent_activities.pop(0)
            
        # Notify listeners
        await self._notify_listeners(activity_type, activity)
        
        # Log the activity
        logger.info(
            f"Activity tracked: {activity_type}",
            extra={
                "activity": activity,
                "user_id": user_id,
                "project_id": project_id
            }
        )
        
        return activity
        
    async def get_recent_activities(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[int] = None,
        activity_types: Optional[List[ActivityType]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent activities based on filters.
        
        Args:
            user_id: Filter by user ID
            project_id: Filter by project ID
            activity_types: Filter by activity types
            limit: Maximum number of activities to return
            
        Returns:
            List of recent activities
        """
        activities = self.recent_activities.copy()
        activities.reverse()  # Most recent first
        
        # Apply filters
        if user_id is not None:
            activities = [a for a in activities if a.get("user_id") == user_id]
            
        if project_id is not None:
            activities = [a for a in activities if a.get("project_id") == project_id]
            
        if activity_types:
            activities = [a for a in activities if a.get("type") in activity_types]
            
        # Apply limit
        return activities[:limit]
        
    async def get_user_activity_summary(
        self,
        user_id: int,
        db: AsyncSession,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get a summary of user activities.
        
        Args:
            user_id: User ID
            db: Database session
            days: Number of days to look back
            
        Returns:
            Activity summary
        """
        # Get recent activities for the user
        recent_activities = await self.get_recent_activities(
            user_id=user_id,
            limit=100
        )
        
        # Count activities by type
        activity_counts = defaultdict(int)
        for activity in recent_activities:
            activity_counts[activity["type"]] += 1
            
        # Get project count
        project_result = await db.execute(
            select(Project).where(Project.user_id == user_id)
        )
        project_count = len(project_result.scalars().all())
        
        # Get recent crawl count
        crawl_result = await db.execute(
            select(Crawl)
            .join(Project)
            .where(Project.user_id == user_id)
            .limit(50)
        )
        crawl_count = len(crawl_result.scalars().all())
        
        return {
            "user_id": user_id,
            "activity_counts": dict(activity_counts),
            "total_activities": len(recent_activities),
            "project_count": project_count,
            "crawl_count": crawl_count,
            "period_days": days
        }
        
    def subscribe_to_activity(
        self,
        activity_type: ActivityType,
        callback: callable
    ) -> None:
        """
        Subscribe to activity events.
        
        Args:
            activity_type: Type of activity to subscribe to
            callback: Async function to call when activity occurs
        """
        self.activity_listeners[activity_type].append(callback)
        logger.debug(f"Subscribed to activity type: {activity_type}")
        
    def unsubscribe_from_activity(
        self,
        activity_type: ActivityType,
        callback: callable
    ) -> None:
        """
        Unsubscribe from activity events.
        
        Args:
            activity_type: Type of activity to unsubscribe from
            callback: Callback function to remove
        """
        if callback in self.activity_listeners[activity_type]:
            self.activity_listeners[activity_type].remove(callback)
            logger.debug(f"Unsubscribed from activity type: {activity_type}")
            
    async def _notify_listeners(
        self,
        activity_type: ActivityType,
        activity: Dict[str, Any]
    ) -> None:
        """
        Notify all listeners of an activity event.
        
        Args:
            activity_type: Type of activity
            activity: Activity data
        """
        listeners = self.activity_listeners.get(activity_type, [])
        
        # Also notify global listeners (listening to all activity types)
        global_listeners = self.activity_listeners.get("*", [])
        all_listeners = listeners + global_listeners
        
        if all_listeners:
            # Run all callbacks concurrently
            tasks = [
                asyncio.create_task(callback(activity))
                for callback in all_listeners
            ]
            
            # Wait for all callbacks with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout notifying listeners for activity: {activity_type}"
                )
                
    async def get_activity_stats(
        self,
        db: AsyncSession,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get overall activity statistics.
        
        Args:
            db: Database session
            days: Number of days to look back
            
        Returns:
            Activity statistics
        """
        # Get total counts from recent activities
        activity_counts = defaultdict(int)
        for activity in self.recent_activities:
            activity_counts[activity["type"]] += 1
            
        # Get unique users
        unique_users = len(set(
            a["user_id"] for a in self.recent_activities 
            if a.get("user_id") is not None
        ))
        
        # Get unique projects
        unique_projects = len(set(
            a["project_id"] for a in self.recent_activities 
            if a.get("project_id") is not None
        ))
        
        return {
            "total_activities": len(self.recent_activities),
            "activity_breakdown": dict(activity_counts),
            "unique_users": unique_users,
            "unique_projects": unique_projects,
            "period_days": days
        }


# Global activity service instance
activity_service = ActivityService()
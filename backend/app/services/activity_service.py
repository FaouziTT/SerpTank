"""
Activity Service for managing activity feeds.

This service handles creating and retrieving activity feed items
with support for real-time updates via WebSocket.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from app.models.activity_feed import ActivityFeed, ActivityType, ActivitySummary
from app.models.user import User
from app.core.websocket import manager
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


class ActivityService:
    """Service for managing activity feeds."""
    
    async def log_activity(
        self,
        type: ActivityType,
        title: str,
        description: Optional[str] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        project_id: Optional[int] = None,
        site_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        is_public: bool = True,
        is_system: bool = False,
        broadcast: bool = True
    ) -> ActivityFeed:
        """
        Log an activity to the feed.
        
        Args:
            type: Type of activity
            title: Activity title
            description: Optional description
            user_id: ID of the user who performed the activity
            organization_id: Related organization ID
            project_id: Related project ID
            site_id: Related site ID
            data: Additional activity data
            url: Related URL
            ip_address: IP address for security activities
            user_agent: User agent string
            is_public: Whether visible to all org members
            is_system: Whether system-generated
            broadcast: Whether to broadcast via WebSocket
            
        Returns:
            Created activity feed item
        """
        try:
            async with async_session_factory() as db:
                # Get user details if user_id provided
                user_name = None
                user_avatar = None
                
                if user_id:
                    user = await db.get(User, user_id)
                    if user:
                        user_name = user.full_name or user.email
                        user_avatar = user.avatar_url
                
                # Create activity
                activity = ActivityFeed(
                    type=type,
                    title=title,
                    description=description,
                    user_id=user_id,
                    user_name=user_name,
                    user_avatar=user_avatar,
                    organization_id=organization_id,
                    project_id=project_id,
                    site_id=site_id,
                    data=data,
                    url=url,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    is_public=is_public,
                    is_system=is_system
                )
                
                db.add(activity)
                await db.commit()
                await db.refresh(activity)
                
                # Broadcast to relevant channels if enabled
                if broadcast:
                    await self._broadcast_activity(activity)
                
                # Update daily summary
                await self._update_activity_summary(activity)
                
                logger.info(f"Logged activity {activity.id}: {type}")
                return activity
                
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            raise
    
    async def get_activity_feed(
        self,
        organization_id: Optional[int] = None,
        project_id: Optional[int] = None,
        user_id: Optional[int] = None,
        activity_types: Optional[List[ActivityType]] = None,
        limit: int = 50,
        offset: int = 0,
        include_system: bool = False
    ) -> List[ActivityFeed]:
        """Get activity feed with filters."""
        async with async_session_factory() as db:
            query = select(ActivityFeed)
            
            # Apply filters
            conditions = []
            
            if organization_id:
                conditions.append(ActivityFeed.organization_id == organization_id)
            
            if project_id:
                conditions.append(ActivityFeed.project_id == project_id)
                
            if user_id:
                conditions.append(ActivityFeed.user_id == user_id)
                
            if activity_types:
                conditions.append(ActivityFeed.type.in_(activity_types))
                
            if not include_system:
                conditions.append(ActivityFeed.is_system == False)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Order by most recent first
            query = query.order_by(desc(ActivityFeed.created_at))
            query = query.limit(limit).offset(offset)
            
            # Include user relationship
            query = query.options(selectinload(ActivityFeed.user))
            
            result = await db.execute(query)
            return result.scalars().all()
    
    async def get_activity_summary(
        self,
        organization_id: int,
        date: Optional[datetime] = None
    ) -> Optional[ActivitySummary]:
        """Get activity summary for a specific date."""
        if not date:
            date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        async with async_session_factory() as db:
            result = await db.execute(
                select(ActivitySummary).where(
                    and_(
                        ActivitySummary.organization_id == organization_id,
                        ActivitySummary.date == date
                    )
                )
            )
            return result.scalar_one_or_none()
    
    async def get_recent_activities_by_type(
        self,
        organization_id: int,
        activity_type: ActivityType,
        limit: int = 10
    ) -> List[ActivityFeed]:
        """Get recent activities of a specific type."""
        return await self.get_activity_feed(
            organization_id=organization_id,
            activity_types=[activity_type],
            limit=limit
        )
    
    async def _broadcast_activity(self, activity: ActivityFeed) -> None:
        """Broadcast activity via WebSocket."""
        activity_data = activity.to_dict()
        
        # Broadcast to organization channel
        if activity.organization_id:
            await manager.broadcast_to_organization(
                {
                    "type": "activity",
                    "activity": activity_data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                activity.organization_id
            )
        
        # Broadcast to project channel
        if activity.project_id:
            await manager.broadcast_to_project(
                {
                    "type": "activity",
                    "activity": activity_data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                activity.project_id
            )
    
    async def _update_activity_summary(self, activity: ActivityFeed) -> None:
        """Update daily activity summary."""
        if not activity.organization_id:
            return
            
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        try:
            async with async_session_factory() as db:
                # Get or create summary
                result = await db.execute(
                    select(ActivitySummary).where(
                        and_(
                            ActivitySummary.organization_id == activity.organization_id,
                            ActivitySummary.date == today
                        )
                    )
                )
                summary = result.scalar_one_or_none()
                
                if not summary:
                    summary = ActivitySummary(
                        date=today,
                        organization_id=activity.organization_id
                    )
                    db.add(summary)
                
                # Update counts
                summary.total_activities += 1
                
                # Update type-specific counts
                if activity.type.startswith("user_"):
                    summary.user_activities += 1
                elif activity.type.startswith("site_"):
                    summary.site_activities += 1
                elif activity.type.startswith("performance_"):
                    summary.performance_activities += 1
                elif activity.type.startswith("serp_") or activity.type.startswith("keyword_"):
                    summary.seo_activities += 1
                elif activity.type.startswith("content_"):
                    summary.content_activities += 1
                elif activity.type.startswith("member_") or activity.type.startswith("permission_"):
                    summary.team_activities += 1
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error updating activity summary: {e}")


# Create singleton instance
activity_service = ActivityService()


# Activity logging helpers
async def log_user_activity(
    user_id: int,
    type: ActivityType,
    title: str,
    organization_id: Optional[int] = None,
    **kwargs
) -> ActivityFeed:
    """Log a user activity."""
    return await activity_service.log_activity(
        type=type,
        title=title,
        user_id=user_id,
        organization_id=organization_id,
        **kwargs
    )


async def log_performance_activity(
    site_id: int,
    title: str,
    data: Dict[str, Any],
    organization_id: int,
    user_id: Optional[int] = None
) -> ActivityFeed:
    """Log a performance-related activity."""
    return await activity_service.log_activity(
        type=ActivityType.PERFORMANCE_ANALYZED,
        title=title,
        site_id=site_id,
        organization_id=organization_id,
        user_id=user_id,
        data=data
    )


async def log_seo_activity(
    type: ActivityType,
    title: str,
    site_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    data: Optional[Dict[str, Any]] = None
) -> ActivityFeed:
    """Log an SEO-related activity."""
    return await activity_service.log_activity(
        type=type,
        title=title,
        site_id=site_id,
        organization_id=organization_id,
        data=data
    )
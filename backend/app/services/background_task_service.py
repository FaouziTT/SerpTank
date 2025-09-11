"""
Service for managing and tracking background tasks.

This module provides functionality to create, update, and monitor
background tasks across the application.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.background_task import BackgroundTask, TaskStatus, TaskType
from app.db.session import async_session_factory
from app.core.websocket import broadcast_task_update

logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """Service for managing background tasks."""
    
    async def create_task(
        self,
        user_id: int,
        task_type: TaskType,
        task_name: str,
        description: Optional[str] = None,
        site_id: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        celery_task_id: Optional[str] = None,
    ) -> str:
        """
        Create a new background task record.
        
        Args:
            user_id: ID of the user who initiated the task
            task_type: Type of the task
            task_name: Human-readable name of the task
            description: Optional description
            site_id: Optional site ID if task is site-specific
            parameters: Input parameters for the task
            celery_task_id: Optional Celery task ID
            
        Returns:
            The ID of the created task
        """
        task_id = str(uuid.uuid4())
        
        async with async_session_factory() as db:
            task = BackgroundTask(
                id=task_id,
                user_id=user_id,
                site_id=site_id,
                task_type=task_type,
                task_name=task_name,
                description=description,
                parameters=parameters or {},
                celery_task_id=celery_task_id,
                status=TaskStatus.PENDING,
                progress=0,
            )
            
            db.add(task)
            await db.commit()
            
            logger.info(f"Created background task {task_id} of type {task_type} for user {user_id}")
            
            # Broadcast task creation
            await self._broadcast_update(task)
            
            return task_id
    
    async def start_task(self, task_id: str) -> None:
        """Mark a task as started."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                task.status = TaskStatus.STARTED
                task.started_at = datetime.now(timezone.utc)
                task.status_message = "Task started"
                await db.commit()
                await self._broadcast_update(task)
    
    async def update_progress(
        self, 
        task_id: str, 
        progress: int, 
        status_message: Optional[str] = None
    ) -> None:
        """Update task progress."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                task.status = TaskStatus.PROGRESS
                task.progress = min(100, max(0, progress))
                if status_message:
                    task.status_message = status_message
                await db.commit()
                await self._broadcast_update(task)
    
    async def complete_task(
        self, 
        task_id: str, 
        result: Optional[Dict[str, Any]] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> None:
        """Mark a task as completed."""
        async with async_session_factory() as db:
            db_result = await db.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = db_result.scalar_one_or_none()
            
            if task:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now(timezone.utc)
                task.progress = 100
                task.status_message = "Task completed successfully"
                task.result = result
                task.resource_id = resource_id
                task.resource_type = resource_type
                await db.commit()
                await self._broadcast_update(task)
                
                logger.info(f"Task {task_id} completed successfully")
    
    async def fail_task(self, task_id: str, error_message: str) -> None:
        """Mark a task as failed."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc)
                task.error = error_message
                task.status_message = "Task failed"
                await db.commit()
                await self._broadcast_update(task)
                
                logger.error(f"Task {task_id} failed: {error_message}")
    
    async def get_task(self, task_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(BackgroundTask)
                .where(
                    and_(
                        BackgroundTask.id == task_id,
                        BackgroundTask.user_id == user_id
                    )
                )
            )
            task = result.scalar_one_or_none()
            
            return task.to_dict() if task else None
    
    async def get_user_tasks(
        self,
        user_id: int,
        task_type: Optional[TaskType] = None,
        status: Optional[TaskStatus] = None,
        site_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get tasks for a user with optional filters."""
        async with async_session_factory() as db:
            query = select(BackgroundTask).where(
                BackgroundTask.user_id == user_id
            )
            
            if task_type:
                query = query.where(BackgroundTask.task_type == task_type)
            
            if status:
                query = query.where(BackgroundTask.status == status)
            
            if site_id:
                query = query.where(BackgroundTask.site_id == site_id)
            
            query = query.order_by(BackgroundTask.created_at.desc()).limit(limit)
            
            result = await db.execute(query)
            tasks = result.scalars().all()
            
            return [task.to_dict() for task in tasks]
    
    async def get_active_tasks(
        self,
        user_id: int,
        site_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all active (non-terminal) tasks for a user."""
        async with async_session_factory() as db:
            query = select(BackgroundTask).where(
                and_(
                    BackgroundTask.user_id == user_id,
                    BackgroundTask.status.in_([
                        TaskStatus.PENDING,
                        TaskStatus.STARTED,
                        TaskStatus.PROGRESS
                    ])
                )
            )
            
            if site_id:
                query = query.where(BackgroundTask.site_id == site_id)
            
            query = query.order_by(BackgroundTask.created_at.desc())
            
            result = await db.execute(query)
            tasks = result.scalars().all()
            
            return [task.to_dict() for task in tasks]
    
    async def check_task_completion(
        self,
        user_id: int,
        task_type: TaskType,
        site_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> bool:
        """
        Check if a task of specific type has completed recently.
        
        Args:
            user_id: User ID
            task_type: Type of task to check
            site_id: Optional site ID
            since: Check for tasks completed after this time
            
        Returns:
            True if a completed task exists
        """
        async with async_session_factory() as db:
            query = select(BackgroundTask).where(
                and_(
                    BackgroundTask.user_id == user_id,
                    BackgroundTask.task_type == task_type,
                    BackgroundTask.status == TaskStatus.COMPLETED
                )
            )
            
            if site_id:
                query = query.where(BackgroundTask.site_id == site_id)
            
            if since:
                query = query.where(BackgroundTask.completed_at >= since)
            
            result = await db.execute(query.limit(1))
            return result.scalar_one_or_none() is not None
    
    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """Clean up old completed tasks."""
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        async with async_session_factory() as db:
            result = await db.execute(
                select(BackgroundTask).where(
                    and_(
                        BackgroundTask.status.in_([
                            TaskStatus.COMPLETED,
                            TaskStatus.FAILED,
                            TaskStatus.CANCELLED
                        ]),
                        BackgroundTask.completed_at < cutoff_date
                    )
                )
            )
            
            tasks_to_delete = result.scalars().all()
            count = len(tasks_to_delete)
            
            for task in tasks_to_delete:
                await db.delete(task)
            
            await db.commit()
            
            logger.info(f"Cleaned up {count} old tasks")
            return count
    
    async def _broadcast_update(self, task: BackgroundTask) -> None:
        """Broadcast task update via WebSocket."""
        try:
            await broadcast_task_update(
                user_id=task.user_id,
                task_data=task.to_dict()
            )
        except Exception as e:
            logger.error(f"Error broadcasting task update: {e}")


# Create singleton instance
background_task_service = BackgroundTaskService()
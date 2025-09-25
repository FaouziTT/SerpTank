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

                # Log completion activity for crawl tasks
                if task.task_type == TaskType.CRAWL:
                    await self._log_crawl_completion_activity(task)

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

    async def get_task_progress_status(
        self,
        user_id: int,
        task_type: TaskType,
        site_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed progress status for the most recent task of a given type.
        This is specifically designed for loading bars and progress indicators.

        Returns:
            Dict with 'status' (pending/in_progress/completed) and 'progress' (0-100)
        """
        async with async_session_factory() as db:
            # [FIX] Check for active (STARTED, PROGRESS) tasks FIRST.
            # We always want to know if something is currently running.
            active_query = select(BackgroundTask).where(
                and_(
                    BackgroundTask.user_id == user_id,
                    BackgroundTask.task_type == task_type,
                    BackgroundTask.status.in_([TaskStatus.STARTED, TaskStatus.PROGRESS])
                )
            ).order_by(BackgroundTask.created_at.desc())

            if site_id:
                active_query = active_query.where(BackgroundTask.site_id == site_id)

            active_result = await db.execute(active_query.limit(1))
            active_task = active_result.scalar_one_or_none()

            if active_task:
                return {
                    "status": "in_progress",
                    "progress": active_task.progress,
                    "message": active_task.status_message or "Task in progress..."
                }

            # [FIX] If no active task, check for a PENDING task.
            # This means it's been queued but not started by a worker yet.
            pending_query = select(BackgroundTask).where(
                and_(
                    BackgroundTask.user_id == user_id,
                    BackgroundTask.task_type == task_type,
                    BackgroundTask.status == TaskStatus.PENDING
                )
            ).order_by(BackgroundTask.created_at.desc())

            if site_id:
                pending_query = pending_query.where(BackgroundTask.site_id == site_id)

            pending_result = await db.execute(pending_query.limit(1))
            pending_task = pending_result.scalar_one_or_none()

            if pending_task:
                return {
                    "status": "pending",
                    "progress": 0,
                    "message": pending_task.status_message or "Task is pending..."
                }

            # [FIX] Only if nothing is active or pending, check for the latest completed task.
            completed_query = select(BackgroundTask).where(
                and_(
                    BackgroundTask.user_id == user_id,
                    BackgroundTask.task_type == task_type,
                    BackgroundTask.status == TaskStatus.COMPLETED
                )
            ).order_by(BackgroundTask.created_at.desc())

            if site_id:
                completed_query = completed_query.where(BackgroundTask.site_id == site_id)

            completed_result = await db.execute(completed_query.limit(1))
            completed_task = completed_result.scalar_one_or_none()

            if completed_task:
                return {
                    "status": "completed",
                    "progress": 100,
                    "message": completed_task.status_message or "Task completed successfully"
                }

            # Default to a "not found" or "pending" state if no task of this type has ever run.
            return {
                "status": "pending",
                "progress": 0,
                "message": "Waiting for task to be created..."
            }

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

    async def _log_crawl_completion_activity(self, task: BackgroundTask) -> None:
        """Log activity when a crawl task completes."""
        try:
            from app.services.activity_service import activity_service
            from app.models.activity_feed import ActivityType

            # Extract metrics from task result if available
            result = task.result or {}
            health_score = result.get('health_score', 'N/A')
            issues_count = result.get('issues_count', 0)
            pages_crawled = result.get('pages_crawled', 0)

            # Get the URL from task parameters
            url = task.parameters.get('url', 'your site')

            await activity_service.log_activity(
                type=ActivityType.SITE_CRAWLED,
                title="Site Diagnostic Completed",
                description=f"Analysis complete for {url} - Health Score: {health_score}%, Pages: {pages_crawled}, Issues: {issues_count}",
                user_id=task.user_id,
                site_id=task.site_id,
                data={
                    "task_id": task.id,
                    "crawl_result": result,
                    "status": "completed"
                },
                broadcast=True
            )

        except Exception as e:
            logger.error(f"Error logging crawl completion activity: {e}")


# Create singleton instance
background_task_service = BackgroundTaskService()
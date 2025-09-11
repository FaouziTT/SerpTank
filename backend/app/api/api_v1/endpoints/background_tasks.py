"""
API endpoints for background task management.

This module provides endpoints for checking task status and managing
background operations.
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.db.session import get_db
from app.models.background_task import TaskStatus, TaskType
from app.services.background_task_service import background_task_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: UserProfile = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Get the status of a specific background task.
    
    Args:
        task_id: The ID of the task
        current_user: The authenticated user
        
    Returns:
        Task status and details
    """
    logger.info(f"Getting task status for {task_id} by user {current_user.email}")
    
    task = await background_task_service.get_task(task_id, current_user.id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    return task


@router.get("/tasks")
async def get_user_tasks(
    task_type: Optional[TaskType] = Query(None, description="Filter by task type"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of tasks to return"),
    current_user: UserProfile = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """
    Get tasks for the current user with optional filters.
    
    Args:
        task_type: Optional task type filter
        status: Optional status filter
        site_id: Optional site ID filter
        limit: Maximum number of tasks to return
        current_user: The authenticated user
        
    Returns:
        List of tasks
    """
    logger.info(f"Getting tasks for user {current_user.email}")
    
    tasks = await background_task_service.get_user_tasks(
        user_id=current_user.id,
        task_type=task_type,
        status=status,
        site_id=site_id,
        limit=limit
    )
    
    return tasks


@router.get("/tasks/active")
async def get_active_tasks(
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    current_user: UserProfile = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    """
    Get all active (non-completed) tasks for the current user.
    
    Args:
        site_id: Optional site ID filter
        current_user: The authenticated user
        
    Returns:
        List of active tasks
    """
    logger.info(f"Getting active tasks for user {current_user.email}")
    
    tasks = await background_task_service.get_active_tasks(
        user_id=current_user.id,
        site_id=site_id
    )
    
    return tasks


@router.get("/tasks/check-completion")
async def check_task_completion(
    task_type: TaskType = Query(..., description="Type of task to check"),
    site_id: Optional[int] = Query(None, description="Site ID to check"),
    minutes: int = Query(5, ge=1, le=60, description="Check tasks completed in last N minutes"),
    current_user: UserProfile = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Check if a specific type of task has completed recently.
    
    This endpoint is useful for checking if background analysis tasks
    have completed without knowing the specific task ID.
    
    Args:
        task_type: Type of task to check
        site_id: Optional site ID
        minutes: Time window to check (in minutes)
        current_user: The authenticated user
        
    Returns:
        Completion status and task details if found
    """
    logger.info(
        f"Checking {task_type} completion for user {current_user.email}, "
        f"site {site_id}, last {minutes} minutes"
    )
    
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    
    # Check if task completed
    completed = await background_task_service.check_task_completion(
        user_id=current_user.id,
        task_type=task_type,
        site_id=site_id,
        since=since
    )
    
    # Get the most recent task of this type
    tasks = await background_task_service.get_user_tasks(
        user_id=current_user.id,
        task_type=task_type,
        site_id=site_id,
        limit=1
    )
    
    latest_task = tasks[0] if tasks else None
    
    return {
        "completed": completed,
        "latest_task": latest_task,
        "checked_since": since.isoformat(),
        "task_type": task_type.value,
        "site_id": site_id
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: UserProfile = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Cancel a running task.
    
    Args:
        task_id: The ID of the task to cancel
        current_user: The authenticated user
        db: Database session
        
    Returns:
        Updated task status
    """
    logger.info(f"Cancelling task {task_id} by user {current_user.email}")
    
    # Get the task first
    task = await background_task_service.get_task(task_id, current_user.id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    if task["status"] in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task in {task['status']} state"
        )
    
    # TODO: Implement actual task cancellation logic
    # This would need to interact with Celery to revoke the task
    
    return {
        "message": "Task cancellation not yet implemented",
        "task_id": task_id
    }
"""
Audit trail functionality for tracking user actions and system events.

This module provides decorators and utilities for creating an audit trail
of important actions in the system.
"""
import json
from typing import Any, Dict, Optional, Union
from datetime import datetime, timezone
from functools import wraps
import asyncio
import inspect

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import HttpUrl

from app.models.audit_log import AuditLog
from app.core.structured_logging import get_logger, user_id_var, organization_id_var, request_id_var

logger = get_logger(__name__)


class AuditJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles special types for audit logging."""
    
    def default(self, obj):
        if isinstance(obj, HttpUrl):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'dict'):
            # Handle Pydantic models
            return obj.dict()
        return super().default(obj)


class AuditTrail:
    """Service for managing audit trail entries."""
    
    @staticmethod
    async def log_action(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: Optional[Union[int, str]] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Log an action to the audit trail.
        
        Args:
            db: Database session
            action: Action performed (e.g., "create", "update", "delete", "login")
            resource_type: Type of resource affected (e.g., "project", "user", "site")
            resource_id: ID of the affected resource
            user_id: ID of the user performing the action
            organization_id: ID of the organization
            old_value: Previous state (for updates)
            new_value: New state (for creates/updates)
            metadata: Additional metadata about the action
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created AuditLog entry
        """
        # Get context from context variables if not provided
        if user_id is None:
            user_id = user_id_var.get()
        if organization_id is None:
            organization_id = organization_id_var.get()
            
        request_id = request_id_var.get()
        
        audit_log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            user_id=user_id,
            organization_id=organization_id,
            old_value=json.dumps(old_value, cls=AuditJSONEncoder) if old_value else None,
            new_value=json.dumps(new_value, cls=AuditJSONEncoder) if new_value else None,
            extra_data=json.dumps(metadata, cls=AuditJSONEncoder) if metadata else None,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc)
        )
        
        db.add(audit_log)
        await db.commit()
        
        # Log to structured logging as well
        logger.info(
            f"Audit: {action} on {resource_type}",
            extra={
                'extra_fields': {
                    'audit': {
                        'action': action,
                        'resource_type': resource_type,
                        'resource_id': resource_id,
                        'user_id': user_id,
                        'organization_id': organization_id,
                        'request_id': request_id
                    }
                }
            }
        )
        
        return audit_log
    
    @staticmethod
    async def get_audit_logs(
        db: AsyncSession,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[AuditLog]:
        """
        Retrieve audit logs based on filters.
        
        Args:
            db: Database session
            user_id: Filter by user ID
            organization_id: Filter by organization ID
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            action: Filter by action
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of AuditLog entries
        """
        query = select(AuditLog)
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if organization_id:
            query = query.where(AuditLog.organization_id == organization_id)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if action:
            query = query.where(AuditLog.action == action)
        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)
        
        query = query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()


def audit_action(
    action: str,
    resource_type: str,
    get_resource_id: Optional[callable] = None,
    get_old_value: Optional[callable] = None,
    get_new_value: Optional[callable] = None,
    include_metadata: bool = True
):
    """
    Decorator for automatically creating audit trail entries.
    
    Args:
        action: Action being performed
        resource_type: Type of resource being acted upon
        get_resource_id: Function to extract resource ID from function arguments
        get_old_value: Function to get old value (for updates)
        get_new_value: Function to get new value (for creates/updates)
        include_metadata: Whether to include function metadata
        
    Example:
        @audit_action("create", "project", get_resource_id=lambda result: result.id)
        async def create_project(db: AsyncSession, project_data: dict):
            # Create project logic
            return project
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Find database session in arguments
            db = None
            for arg in args:
                if isinstance(arg, AsyncSession):
                    db = arg
                    break
            if not db:
                db = kwargs.get('db')
            
            # Get old value if applicable
            old_value = None
            if get_old_value:
                try:
                    old_value = await get_old_value(*args, **kwargs) if asyncio.iscoroutinefunction(get_old_value) else get_old_value(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Failed to get old value for audit: {e}")
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Get resource ID
            resource_id = None
            if get_resource_id:
                try:
                    resource_id = get_resource_id(result)
                except Exception as e:
                    logger.warning(f"Failed to get resource ID for audit: {e}")
            
            # Get new value if applicable
            new_value = None
            if get_new_value:
                try:
                    new_value = await get_new_value(result) if asyncio.iscoroutinefunction(get_new_value) else get_new_value(result)
                except Exception as e:
                    logger.warning(f"Failed to get new value for audit: {e}")
            
            # Create metadata
            metadata = None
            if include_metadata:
                metadata = {
                    "function": func.__name__,
                    "module": func.__module__
                }
                
                # Add function arguments (excluding sensitive data)
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                
                metadata["arguments"] = {}
                for param_name, param_value in bound.arguments.items():
                    if param_name not in ['db', 'password', 'token', 'secret']:
                        if hasattr(param_value, 'dict'):
                            metadata["arguments"][param_name] = param_value.dict()
                        elif isinstance(param_value, (str, int, float, bool, list, dict)):
                            metadata["arguments"][param_name] = param_value
                        else:
                            metadata["arguments"][param_name] = str(param_value)
            
            # Log to audit trail
            if db:
                try:
                    await AuditTrail.log_action(
                        db=db,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        old_value=old_value,
                        new_value=new_value,
                        metadata=metadata
                    )
                except Exception as e:
                    logger.error(f"Failed to create audit log: {e}", exc_info=True)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, just log to structured logging
            result = func(*args, **kwargs)
            
            logger.info(
                f"Audit (sync): {action} on {resource_type}",
                extra={
                    'extra_fields': {
                        'audit': {
                            'action': action,
                            'resource_type': resource_type,
                            'function': func.__name__
                        }
                    }
                }
            )
            
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Common audit actions
class AuditActions:
    # CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_RESET = "password_reset"
    
    # Authorization
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    
    # Data operations
    EXPORT = "export"
    IMPORT = "import"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    
    # Configuration
    SETTINGS_CHANGED = "settings_changed"
    CONFIG_UPDATED = "config_updated"
    
    # Integration
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    INTEGRATION_CONNECTED = "integration_connected"
    INTEGRATION_DISCONNECTED = "integration_disconnected"


# Common resource types
class ResourceTypes:
    USER = "user"
    PROJECT = "project"
    SITE = "site"
    ORGANIZATION = "organization"
    CRAWL = "crawl"
    REPORT = "report"
    API_KEY = "api_key"
    SETTINGS = "settings"
    CACHE = "cache"
    INTEGRATION = "integration"
from pydantic import BaseModel, HttpUrl, EmailStr, field_validator
from typing import Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import json

from .user import User

class SetupTaskStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class SetupTask(BaseModel):
    status: SetupTaskStatus
    progress: Optional[int] = None  # 0-100
    message: Optional[str] = None
    error: Optional[str] = None
    
    @field_validator('status', mode='before')
    @classmethod
    def validate_status(cls, v):
        """Ensure status is properly converted to SetupTaskStatus enum."""
        if isinstance(v, str):
            try:
                return SetupTaskStatus(v)
            except ValueError:
                # If the string is not a valid enum value, default to NOT_STARTED
                return SetupTaskStatus.NOT_STARTED
        elif isinstance(v, SetupTaskStatus):
            return v
        else:
            # For any other type, default to NOT_STARTED
            return SetupTaskStatus.NOT_STARTED
    
class ProjectSetupStatus(BaseModel):
    crawl: SetupTask
    core_web_vitals: SetupTask
    search_console: SetupTask
    google_analytics: SetupTask

class ProjectCreate(BaseModel):
    name: str  # Making name required
    url: HttpUrl
    organization_id: str  # Required - projects must belong to an organization
    description: Optional[str] = None
    # GA4 Configuration (optional during creation)
    ga4_property_id: Optional[str] = None
    ga4_measurement_id: Optional[str] = None
    analytics_enabled: bool = True
    profitability_tracking: bool = True
    # Initial analysis options
    run_initial_crawl: bool = True
    run_initial_core_web_vitals: bool = True

class ProjectOut(BaseModel):
    id: int
    user_id: int
    organization_id: Optional[str] = None
    name: Optional[str]
    url: HttpUrl
    description: Optional[str] = None
    # GA4 Configuration
    ga4_property_id: Optional[str] = None
    ga4_measurement_id: Optional[str] = None
    ga4_configured: bool = False
    analytics_enabled: bool = True
    profitability_tracking: bool = True
    setup_status: Optional[ProjectSetupStatus] = None
    created_at: datetime
    updated_at: datetime

    @field_validator('setup_status', mode='before')
    @classmethod
    def validate_setup_status(cls, v):
        """Convert JSON string to ProjectSetupStatus object if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                # Parse JSON string to dict
                setup_data = json.loads(v)
                # Convert dict to ProjectSetupStatus
                return ProjectSetupStatus(**setup_data)
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                # If JSON parsing fails, return None rather than failing validation
                return None
        elif isinstance(v, dict):
            # If it's already a dict, convert to ProjectSetupStatus
            try:
                return ProjectSetupStatus(**v)
            except (ValueError, TypeError):
                return None
        elif isinstance(v, ProjectSetupStatus):
            # If it's already a ProjectSetupStatus object, return as is
            return v
        else:
            # For any other type, return None
            return None

    class Config:
        from_attributes = True

class ProjectSettingsUpdate(BaseModel):
    """Schema for updating project settings, including GA4 configuration"""
    ga4_property_id: Optional[str] = None
    ga4_measurement_id: Optional[str] = None
    analytics_enabled: Optional[bool] = None
    profitability_tracking: Optional[bool] = None

# --- Project Team Member Schemas ---
class ProjectTeamMemberCreate(BaseModel):
    email: EmailStr
    can_edit: bool = False

class ProjectTeamMemberUpdate(BaseModel):
    can_edit: Optional[bool] = None

class ProjectTeamMemberOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    can_edit: bool
    created_at: datetime
    user: User

    class Config:
        from_attributes = True 
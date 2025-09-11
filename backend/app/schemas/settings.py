from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


class UserUpdate(BaseModel):
    organization_name: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    timezone: Optional[str] = None


class TeamMember(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    status: str
    last_active: datetime
    avatar_url: Optional[str] = None


class TeamMemberCreate(BaseModel):
    name: str
    email: EmailStr
    role: str


class TeamMemberUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class Integration(BaseModel):
    id: str
    name: str
    description: str
    type: str
    status: str
    last_sync: Optional[datetime] = None
    config: Optional[dict] = None


class IntegrationUpdate(BaseModel):
    status: Optional[str] = None
    config: Optional[dict] = None


class IntegrationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    status: Optional[str] = None
    last_sync: Optional[datetime] = None
    config: Optional[dict] = None


class NotificationPreference(BaseModel):
    id: str
    type: str
    description: str
    enabled: bool
    frequency: str
    channels: List[str] = []


class NotificationUpdate(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[str] = None
    channels: Optional[List[str]] = None


class UsageStats(BaseModel):
    api_requests: int
    api_requests_limit: int
    data_storage_gb: float
    data_storage_limit_gb: float
    team_members: int
    team_members_limit: int
    websites_monitored: int
    websites_limit: int


class ApiKey(BaseModel):
    id: str
    name: str
    key_preview: str
    last_used: Optional[datetime] = None
    rate_limit: int
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str


class SecuritySettings(BaseModel):
    two_factor_enabled: bool
    password_last_changed: Optional[datetime] = None
    login_attempts: int
    account_locked: bool


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class TwoFactorUpdate(BaseModel):
    enabled: Optional[bool] = None

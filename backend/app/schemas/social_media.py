from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class SocialMediaCredentialBase(BaseModel):
    platform: str  # twitter, facebook, linkedin, instagram
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    access_token_secret: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None


class SocialMediaCredentialCreate(SocialMediaCredentialBase):
    pass


class SocialMediaCredentialUpdate(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    access_token_secret: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None


class SocialMediaCredentialInDB(SocialMediaCredentialBase):
    id: int
    project_id: int
    is_connected: bool
    last_verified_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class SocialMediaCredentialResponse(BaseModel):
    id: int
    project_id: int
    platform: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    is_connected: bool
    last_verified_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Never expose secrets in response
    has_api_key: bool = False
    has_api_secret: bool = False
    has_access_token: bool = False
    has_access_token_secret: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class SocialMediaTestResponse(BaseModel):
    success: bool
    message: str
    account_info: Optional[dict] = None


# Webhook schemas
class WebhookBase(BaseModel):
    name: str
    url: str
    events: List[str]


class WebhookCreate(WebhookBase):
    pass


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    active: Optional[bool] = None


class WebhookInDB(WebhookBase):
    id: int
    project_id: int
    secret: str
    active: bool
    last_triggered_at: Optional[datetime] = None
    last_status_code: Optional[int] = None
    last_error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class WebhookResponse(WebhookInDB):
    pass


class WebhookTestResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None


# Domain verification schemas
class DomainVerificationCreate(BaseModel):
    method: str  # dns_txt, html_file, meta_tag
    domain: Optional[str] = None


class DomainVerificationResponse(BaseModel):
    id: int
    project_id: int
    domain: str
    verified: bool
    verification_method: Optional[str] = None
    verification_token: Optional[str] = None
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DomainVerificationCheckResponse(BaseModel):
    verified: bool
    message: str
    checked_at: datetime
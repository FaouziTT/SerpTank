"""
Settings endpoints for managing user preferences, team, integrations, and account settings.
"""
import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.core.dependencies import get_current_active_user
from app.auth.schemas.auth import UserProfile
from app.db.session import get_db
from app.core.config import settings
from app.models.user import User
from app.models.settings import TeamMember, Integration, NotificationSetting, UsageStatistics, ApiKey
from app.schemas.settings import (
    UserUpdate, TeamMember as TeamMemberSchema, TeamMemberCreate, TeamMemberUpdate,
    Integration as IntegrationSchema, IntegrationUpdate,
    NotificationPreference as NotificationSchema, NotificationUpdate,
    UsageStats, ApiKey as ApiKeySchema, ApiKeyCreate, SecuritySettings, PasswordUpdate, IntegrationCreate, TwoFactorUpdate
)
from app.schemas.user import UserProfileUpdate, UserProfileSchema

router = APIRouter()


@router.get("/profile")
def get_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Get current user profile and settings."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "organization_name": current_user.organization_name or "Your Organization",
        "website_url": current_user.website_url,
        "industry": current_user.industry or "Technology",
        "timezone": current_user.timezone or "UTC-8 (Pacific Standard Time)",
        "created_at": current_user.created_at,
        "last_login": current_user.last_login,
    }


@router.put("/profile", response_model=UserProfileSchema)
async def update_profile(
    profile_update: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Update user profile and settings."""
    update_data = profile_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return {"message": "Profile updated successfully"}


@router.get("/team", response_model=List[TeamMemberSchema])
async def get_team_members(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Get all team members."""
    result = await db.execute(select(TeamMember).where(TeamMember.user_id == current_user.id))
    team_members = result.scalars().all()
    
    if not team_members:
        default_member = TeamMember(
            user_id=current_user.id,
            name=current_user.full_name or "Demo User",
            email=current_user.email,
            role="Owner",
            status="Active",
            last_active=datetime.utcnow(),
            avatar_url=None,
        )
        db.add(default_member)
        await db.commit()
        team_members = [default_member]
    
    return team_members


@router.post("/team", response_model=TeamMemberSchema)
async def create_team_member(
    member_data: TeamMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Add a new team member."""
    from sqlalchemy import select
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.user_id == current_user.id,
            TeamMember.email == member_data.email
        )
    )
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team member with this email already exists"
        )
    
    team_member = TeamMember(
        user_id=current_user.id,
        **member_data.dict(),
        status="Active",
        last_active=datetime.utcnow()
    )
    
    db.add(team_member)
    await db.commit()
    await db.refresh(team_member)
    
    return team_member


@router.put("/team/{member_id}", response_model=TeamMemberSchema)
async def update_team_member(
    member_id: int,
    member_update: TeamMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Update a team member."""
    from sqlalchemy import select
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.id == member_id,
            TeamMember.user_id == current_user.id
        )
    )
    team_member = result.scalars().first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    
    update_data = member_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team_member, field, value)
    
    db.add(team_member)
    await db.commit()
    await db.refresh(team_member)
    
    return team_member


@router.delete("/team/{member_id}")
async def delete_team_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Remove a team member."""
    from sqlalchemy import select
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.id == member_id,
            TeamMember.user_id == current_user.id
        )
    )
    team_member = result.scalars().first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team member not found"
        )
    
    await db.delete(team_member)
    await db.commit()
    
    return {"message": "Team member removed successfully"}


@router.get("/integrations", response_model=List[IntegrationSchema])
async def get_integrations(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Get all integrations."""
    result = await db.execute(select(Integration).where(Integration.user_id == current_user.id))
    integrations = result.scalars().all()
    
    # If no integrations, create default ones
    if not integrations:
        default_integrations = [
            Integration(
                id="google_analytics",
                user_id=current_user.id,
                name="Google Analytics 4",
                description="Track website performance and user behavior",
                type="Analytics",
                status="Connected" if settings.GOOGLE_ANALYTICS_PROPERTY_ID else "Disconnected",
                last_sync=datetime.utcnow() - timedelta(minutes=5) if settings.GOOGLE_ANALYTICS_PROPERTY_ID else None
            ),
            Integration(
                id="google_search_console",
                user_id=current_user.id,
                name="Google Search Console",
                description="Monitor search performance and indexing",
                type="Search",
                status="Connected" if settings.GOOGLE_SEARCH_CONSOLE_SITE_URL else "Disconnected",
                last_sync=datetime.utcnow() - timedelta(minutes=15) if settings.GOOGLE_SEARCH_CONSOLE_SITE_URL else None
            ),
            Integration(
                id="pagespeed_insights",
                user_id=current_user.id,
                name="PageSpeed Insights",
                description="Core Web Vitals and performance analysis",
                type="Performance",
                status="Connected" if settings.GOOGLE_API_KEY else "Disconnected",
                last_sync=datetime.utcnow() - timedelta(minutes=30) if settings.GOOGLE_API_KEY else None
            ),
            Integration(
                id="screaming_frog",
                user_id=current_user.id,
                name="Screaming Frog",
                description="Technical SEO crawling and analysis",
                type="Crawling",
                status="Disconnected",
                last_sync=None
            ),
            Integration(
                id="semrush",
                user_id=current_user.id,
                name="SEMrush",
                description="Keyword research and competitive analysis",
                type="Research",
                status="Disconnected",
                last_sync=None
            ),
        ]
        
        for integration in default_integrations:
            db.add(integration)
        await db.commit()
        
        integrations = default_integrations
    
    return integrations


@router.post("/integrations", response_model=IntegrationSchema)
async def create_integration(
    integration_create: IntegrationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Add a new integration."""
    integration = Integration(
        user_id=current_user.id,
        **integration_create.dict()
    )
    
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    
    return integration


@router.put("/integrations/{integration_id}", response_model=IntegrationSchema)
async def update_integration(
    integration_id: str,
    integration_update: IntegrationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Update an integration."""
    result = await db.execute(select(Integration).where(
        Integration.id == integration_id,
        Integration.user_id == current_user.id
    ))
    integration = result.scalars().first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    update_data = integration_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "config" and value:
            setattr(integration, field, json.dumps(value))
        else:
            setattr(integration, field, value)
    
    if integration_update.status == "Connected":
        integration.last_sync = datetime.utcnow()
    
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    
    return {"message": "Integration updated successfully"}


@router.delete("/integrations/{integration_id}")
async def delete_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Remove an integration."""
    result = await db.execute(select(Integration).where(
        Integration.id == integration_id,
        Integration.user_id == current_user.id
    ))
    integration = result.scalars().first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    db.delete(integration)
    await db.commit()
    
    return {"message": "Integration removed successfully"}


@router.get("/notifications", response_model=List[NotificationSchema])
async def get_notification_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Get notification preferences."""
    result = await db.execute(select(NotificationSetting).where(
        NotificationSetting.user_id == current_user.id
    ))
    preferences = result.scalars().all()
    
    # If no preferences, create defaults
    if not preferences:
        default_preferences = [
            NotificationSetting(
                id="performance_alert",
                user_id=current_user.id,
                type="Performance Alert",
                description="Get notified when Core Web Vitals scores drop below threshold",
                enabled=True,
                frequency="Real-time",
                channels=json.dumps(["email", "dashboard"])
            ),
            NotificationSetting(
                id="ranking_changes",
                user_id=current_user.id,
                type="Ranking Changes",
                description="Track significant changes in keyword rankings",
                enabled=True,
                frequency="Daily",
                channels=json.dumps(["email"])
            ),
            NotificationSetting(
                id="content_opportunities",
                user_id=current_user.id,
                type="Content Opportunities",
                description="Receive alerts for new content opportunities",
                enabled=False,
                frequency="Weekly",
                channels=json.dumps(["email"])
            ),
            NotificationSetting(
                id="competitor_updates",
                user_id=current_user.id,
                type="Competitor Updates",
                description="Monitor competitor SEO changes and new content",
                enabled=True,
                frequency="Weekly",
                channels=json.dumps(["email"])
            ),
            NotificationSetting(
                id="technical_issues",
                user_id=current_user.id,
                type="Technical Issues",
                description="Get alerts for crawl errors and technical problems",
                enabled=True,
                frequency="Real-time",
                channels=json.dumps(["email", "dashboard"])
            ),
        ]
        
        for pref in default_preferences:
            db.add(pref)
        await db.commit()
        
        preferences = default_preferences
    
    # Parse channels JSON
    for pref in preferences:
        if pref.channels:
            pref.channels = json.loads(pref.channels)
        else:
            pref.channels = []
    
    return preferences


@router.put("/notifications/{notification_id}", response_model=NotificationSchema)
async def update_notification_preference(
    notification_id: str,
    notification_update: NotificationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Update notification preference."""
    result = await db.execute(select(NotificationSetting).where(
        NotificationSetting.id == notification_id,
        NotificationSetting.user_id == current_user.id
    ))
    preference = result.scalars().first()
    
    if not preference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification preference not found"
        )
    
    update_data = notification_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "channels" and value:
            setattr(preference, field, json.dumps(value))
        else:
            setattr(preference, field, value)
    
    db.add(preference)
    await db.commit()
    
    return {"message": "Notification preference updated successfully"}


@router.get("/usage", response_model=UsageStats)
async def get_usage_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Get usage statistics."""
    result = await db.execute(select(UsageStatistics).where(
        UsageStatistics.user_id == current_user.id
    ))
    usage = result.scalars().first()
    
    if not usage:
        # Create default usage stats
        team_count_result = await db.execute(select(TeamMember).where(TeamMember.user_id == current_user.id))
        team_count = len(team_count_result.scalars().all())
        
        usage = UsageStatistics(
            user_id=current_user.id,
            api_requests=24847,
            api_requests_limit=50000,
            data_storage_gb=12.4,
            data_storage_limit_gb=25.0,
            team_members=max(team_count, 1),
            team_members_limit=10,
            websites_monitored=3,
            websites_limit=5
        )
        
        db.add(usage)
        await db.commit()
        await db.refresh(usage)
    
    return usage


@router.get("/api-keys", response_model=List[ApiKeySchema])
async def get_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Get user's API keys."""
    result = await db.execute(select(ApiKey).where(
        ApiKey.user_id == current_user.id,
        ApiKey.is_active == True
    ))
    api_keys = result.scalars().all()
    
    return api_keys


@router.post("/api-keys", response_model=ApiKeySchema)
async def create_api_key(
    api_key_data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Create a new API key."""
    # Generate API key
    key = f"vx_sk_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    key_preview = f"{key[:12]}...{key[-4:]}"
    
    api_key = ApiKey(
        id=secrets.token_urlsafe(16),
        user_id=current_user.id,
        name=api_key_data.name,
        key_hash=key_hash,
        key_preview=key_preview,
        rate_limit=1000
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    # Return the actual key only once
    api_key.actual_key = key
    return api_key


@router.delete("/api-keys/{api_key_id}")
async def delete_api_key(
    api_key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Revoke an API key."""
    result = await db.execute(select(ApiKey).where(
        ApiKey.id == api_key_id,
        ApiKey.user_id == current_user.id
    ))
    api_key = result.scalars().first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = False
    db.add(api_key)
    await db.commit()
    
    return {"message": "API key revoked successfully"}


@router.get("/security", response_model=SecuritySettings)
def get_security_settings(
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Get security settings."""
    return SecuritySettings(
        two_factor_enabled=current_user.two_factor_enabled,
        password_last_changed=current_user.password_last_changed,
        login_attempts=0,
        account_locked=False
    )


@router.put("/security/password", response_model=SecuritySettings)
async def update_password(
    password_update: PasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Update user password."""
    from app.auth.core.security import verify_password, get_password_hash
    
    # Verify current password
    if not verify_password(password_update.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_update.new_password)
    current_user.password_last_changed = datetime.utcnow()
    current_user.updated_at = datetime.utcnow()
    
    db.add(current_user)
    await db.commit()
    
    return {"message": "Password updated successfully"}


@router.put("/security/2fa", response_model=SecuritySettings)
async def update_two_factor(
    two_factor_update: TwoFactorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserProfile = Depends(get_current_active_user),
):
    """Toggle two-factor authentication."""
    current_user.two_factor_enabled = not current_user.two_factor_enabled
    current_user.updated_at = datetime.utcnow()
    
    db.add(current_user)
    await db.commit()
    
    status_text = "enabled" if current_user.two_factor_enabled else "disabled"
    return {"message": f"Two-factor authentication {status_text} successfully"}

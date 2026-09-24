"""Organization, membership and invitation API models."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from serptank.core.models import MemberRole


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OrganizationCreate(StrictModel):
    name: str = Field(min_length=2, max_length=120)


class OrganizationUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    require_mfa: bool | None = None


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan_code: str
    require_mfa: bool
    created_at: datetime


class OrganizationWithRole(OrganizationOut):
    role: MemberRole


class MemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: MemberRole
    mfa_enabled: bool
    joined_at: datetime


class MemberUpdate(StrictModel):
    role: MemberRole


class InvitationCreate(StrictModel):
    email: EmailStr
    role: MemberRole


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: MemberRole
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None


class InvitationAccept(StrictModel):
    token: str = Field(min_length=10, max_length=128)

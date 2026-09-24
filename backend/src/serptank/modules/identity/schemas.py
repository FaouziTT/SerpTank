"""Request/response models for the identity API. Inputs forbid unknown fields."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from serptank.core.models import MemberRole
from serptank.modules.identity.api_keys import ApiScope

Password = Field(min_length=1, max_length=256)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CsrfResponse(BaseModel):
    csrf_token: str


class RegisterRequest(StrictModel):
    email: EmailStr
    password: str = Password
    full_name: str = Field(min_length=1, max_length=200)


class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Password
    remember_me: bool = False
    captcha_token: str | None = Field(default=None, max_length=4096)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    email_verified: bool
    mfa_enabled: bool
    has_password: bool
    google_linked: bool


class MembershipOut(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    role: MemberRole


class LoginResponse(BaseModel):
    status: Literal["authenticated", "mfa_required"]
    csrf_token: str
    user: UserOut | None = None
    mfa_methods: list[str] = []


class SessionResponse(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]
    reauth_valid_until: datetime | None


class MfaVerifyRequest(StrictModel):
    code: str | None = Field(default=None, max_length=12)
    recovery_code: str | None = Field(default=None, max_length=20)


class SessionInfo(BaseModel):
    id: str
    current: bool
    created_at: datetime
    last_seen_at: datetime
    ip: str | None
    user_agent: str | None
    auth_methods: list[str]


class EmailRequest(StrictModel):
    email: EmailStr


class TokenRequest(StrictModel):
    token: str = Field(min_length=10, max_length=128)


class ResetPasswordRequest(StrictModel):
    token: str = Field(min_length=10, max_length=128)
    new_password: str = Password


class ChangePasswordRequest(StrictModel):
    current_password: str = Password
    new_password: str = Password


class ReauthRequest(StrictModel):
    password: str | None = Field(default=None, max_length=256)
    code: str | None = Field(default=None, max_length=12)


class TotpSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class CodeRequest(StrictModel):
    code: str = Field(min_length=6, max_length=12)


class RecoveryCodesResponse(BaseModel):
    codes: list[str]


class PasskeyRegisterRequest(StrictModel):
    credential: dict[str, Any]
    name: str = Field(default="Passkey", max_length=80)


class PasskeyLoginRequest(StrictModel):
    credential: dict[str, Any]
    remember_me: bool = False


class PasskeyOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    last_used_at: datetime | None
    backed_up: bool


class ApiKeyCreateRequest(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    scopes: list[ApiScope] = Field(min_length=1)
    expires_in_days: int | None = Field(default=90, ge=1, le=365)


class ApiKeyOut(BaseModel):
    id: uuid.UUID
    name: str
    prefix: str
    scopes: list[str]
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None


class ApiKeyCreatedResponse(ApiKeyOut):
    key: str = Field(description="Shown once. Store it securely.")


class AuditEventOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    action: str
    actor_user_id: uuid.UUID | None
    target_type: str | None
    target_id: str | None
    ip_address: str | None
    details: dict[str, Any]

    @field_validator("ip_address", mode="before")
    @classmethod
    def _ip_to_str(cls, value: object) -> str | None:
        return None if value is None else str(value)

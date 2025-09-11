"""Configuration for request signing."""

from typing import Optional
from pydantic import BaseSettings, Field


class SigningSettings(BaseSettings):
    """Settings for request signing."""
    
    # Enable request signing
    enable_request_signing: bool = Field(
        default=False,
        env="ENABLE_REQUEST_SIGNING",
        description="Enable HMAC request signing"
    )
    
    # Signing secret key (should be different from JWT secret)
    signing_secret_key: Optional[str] = Field(
        default=None,
        env="SIGNING_SECRET_KEY",
        description="Secret key for HMAC signing"
    )
    
    # Signing algorithm
    signing_algorithm: str = Field(
        default="sha256",
        env="SIGNING_ALGORITHM",
        description="Algorithm for request signing (sha256 or sha512)"
    )
    
    # Timestamp tolerance in seconds
    timestamp_tolerance: int = Field(
        default=300,  # 5 minutes
        env="SIGNING_TIMESTAMP_TOLERANCE",
        description="Maximum age of request timestamp in seconds"
    )
    
    # Nonce cache settings
    enable_nonce_validation: bool = Field(
        default=True,
        env="ENABLE_NONCE_VALIDATION",
        description="Enable nonce validation to prevent replay attacks"
    )
    
    nonce_cache_ttl: int = Field(
        default=600,  # 10 minutes
        env="NONCE_CACHE_TTL",
        description="TTL for nonce cache in seconds"
    )
    
    # Paths to exclude from signing
    exclude_paths: set = Field(
        default={
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/verify",
            "/api/v1/health",
            "/api/v1/csrf/token",
            "/docs",
            "/redoc",
            "/openapi.json"
        },
        description="Paths to exclude from signature verification"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Singleton instance
_signing_settings: Optional[SigningSettings] = None


def get_signing_settings() -> SigningSettings:
    """Get signing settings singleton."""
    global _signing_settings
    if _signing_settings is None:
        _signing_settings = SigningSettings()
    return _signing_settings
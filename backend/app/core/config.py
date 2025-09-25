"""
Configuration settings for the Voltex DSE application.

This module defines the settings for the application, including environment variables,
database connections, and other configuration parameters.
"""
import os
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # API configuration
    API_V1_STR: str = "/api/v1"
    # SECURITY: Secret key must be set via environment variable
    SECRET_KEY: str = Field(
        ...,
        description="JWT secret key - MUST be set via SECRET_KEY environment variable"
    )
    PROJECT_NAME: str = "Voltex SEO Decision Superiority Engine"
    
    # JWT Configuration
    JWT_ALGORITHM: str = "HS256"  # Algorithm for JWT encoding/decoding
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes for access tokens (security best practice)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days for refresh tokens
    
    # Environment detection
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    
    # CORS configuration - Environment-aware security
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8000", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000"
        ],
        description="Allowed CORS origins - automatically secure in production"
    )
    
    # Trusted hosts configuration - Environment-aware
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "*.localhost"],
        description="Allowed host headers - automatically secure in production"
    )
    
    # SSL configuration - Environment-aware
    SSL_ENABLED: bool = Field(
        default=False,
        description="Enable SSL/TLS - auto-enabled in production"
    )
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None
    
    # Database configuration
    POSTGRES_SERVER: str = Field(default="localhost", env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(default="postgres", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(default="voltex", env="POSTGRES_DB")
    POSTGRES_PORT: str = Field(default="5432", env="POSTGRES_PORT")
    DATABASE_URI: Optional[PostgresDsn] = None

    # Database connection pool settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Model config - consolidated with full configuration below
    
    def get_database_uri(self) -> str:
        """Build the database URI."""
        if self.DATABASE_URI:
            return str(self.DATABASE_URI)
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    def get_sync_database_uri(self) -> str:
        """Build the synchronous database URI for migrations."""
        if self.DATABASE_URI:
            return str(self.DATABASE_URI).replace("+asyncpg", "+psycopg2")
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis configuration
    REDIS_HOST: str = "localhost"  # Docker container name
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Vector database configuration
    VECTOR_DB_TYPE: str = "pinecone"  # or "weaviate"
    VECTOR_DB_API_KEY: Optional[str] = None
    VECTOR_DB_ENVIRONMENT: Optional[str] = None
    
    # Crawler configuration
    CRAWLER_USER_AGENT: str = "VoltexBot/1.0 (+https://voltex.ai/bot)"
    CRAWLER_CONCURRENCY: int = 5
    CRAWLER_RESPECT_ROBOTS_TXT: bool = True
    
    # ML model configuration
    ML_MODEL_PATH: str = "models"
    
    # First superuser configuration - SECURITY FIX: Force environment variables
    FIRST_SUPERUSER_EMAIL: str = Field(
        default="admin@voltex.ai",
        description="Default admin email address"
    )
    FIRST_SUPERUSER_PASSWORD: str = Field(
        ...,
        min_length=12,
        description="Admin password - MUST be set via ADMIN_PASSWORD environment variable"
    )
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    
    # External API keys (read-only integrations)
    GOOGLE_SEARCH_CONSOLE_CLIENT_ID: Optional[str] = None
    GOOGLE_SEARCH_CONSOLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_SEARCH_CONSOLE_SITE_URL: Optional[str] = None  # <-- THIS IS THE FIX
    GOOGLE_ANALYTICS_CLIENT_ID: Optional[str] = None
    GOOGLE_ANALYTICS_CLIENT_SECRET: Optional[str] = None
      # Google API Configuration
    GOOGLE_SERVICE_ACCOUNT_FILE: Optional[str] = None
    GOOGLE_OAUTH_CREDENTIALS_FILE: Optional[str] = None
      # Google Analytics 4 Data API
    GOOGLE_ANALYTICS_API_KEY: Optional[str] = None
    GOOGLE_ANALYTICS_PROPERTY_ID: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # PageSpeed Insights API
    GOOGLE_PAGESPEED_API_KEY: Optional[str] = None

    # Chrome UX Report API
    GOOGLE_CRUX_API_KEY: Optional[str] = None
    
    # Programmable Search Element Control API
    GOOGLE_PROGRAMMABLE_SEARCH_API_KEY: Optional[str] = None
    GOOGLE_PROGRAMMABLE_SEARCH_ENGINE_ID: Optional[str] = None
      # SerpAPI for keyword research
    SERPAPI_KEY: Optional[str] = None
      # OpenAI API for AI features
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"  # Premium model for comprehensive content
    OPENAI_MAX_TOKENS: int = 4000  # Increased for comprehensive content generation
    OPENAI_TEMPERATURE: float = 0.7  # Creativity level (0.0-2.0)
    
    # Google Trends API (uses same credentials as other Google services)
    GOOGLE_TRENDS_ENABLED: bool = True
    
    # YouTube Data API
    YOUTUBE_DATA_API_KEY: Optional[str] = None  # Can use same key as PageSpeed
    
    # Google OAuth for User Authentication (separate from Search Console)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None  
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/oauth/google/callback"
    
    # Backend and Frontend URLs for OAuth
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Social Media APIs
    # Twitter/X API v2
    TWITTER_BEARER_TOKEN: Optional[str] = None
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    TWITTER_ACCESS_TOKEN: Optional[str] = None
    TWITTER_ACCESS_TOKEN_SECRET: Optional[str] = None
    
    # Facebook Graph API
    FACEBOOK_ACCESS_TOKEN: Optional[str] = None
    FACEBOOK_PAGE_ID: Optional[str] = None
    
    # LinkedIn API
    LINKEDIN_ACCESS_TOKEN: Optional[str] = None
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None
    
    # Twitter API Rate Limiting Configuration
    TWITTER_REQUESTS_PER_WINDOW: int = 75  # Twitter API v2 search limit: 75 per 15min
    TWITTER_WINDOW_DURATION: int = 900  # 15 minutes in seconds
    TWITTER_MIN_REQUEST_INTERVAL: int = 2  # Minimum seconds between requests
    TWITTER_MAX_BACKOFF_TIME: int = 900  # Maximum 15 minutes backoff
    TWITTER_ENABLE_SMART_RETRY: bool = True  # Enable intelligent retry logic
    
    # Default site URL for analysis
    DEFAULT_SITE_URL: Optional[str] = None
    DEFAULT_SITE_PROPERTY: Optional[str] = None
    
    # SEO Analysis Configuration
    SEO_ANALYSIS_DEPTH: int = 10  # Number of pages to analyze
    KEYWORD_RESEARCH_LIMIT: int = 100  # Max keywords to research
    
    # File Upload Configuration
    UPLOAD_DIR: str = "/app/uploads"  # Base directory for file uploads
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB max file size
    ALLOWED_EXTENSIONS: List[str] = [
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", 
        ".csv", ".txt", ".json", ".xml",
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
        ".zip"
    ]
    TEMP_FILE_RETENTION_DAYS: int = 7  # Days to keep temporary files
    FILE_CLEANUP_INTERVAL_HOURS: int = 24  # How often to run file cleanup
      # Model config - complete configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        validate_assignment=True,
        # Environment variable mappings
        env_prefix="",
        env_nested_delimiter="__"
    )
    
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Handle comma-separated string
            if v.startswith("[") and v.endswith("]"):
                # Try to parse as JSON
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Fallback to comma-separated parsing
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return [str(v)]
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    def validate_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse and validate allowed hosts."""
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [host.strip() for host in v.split(",") if host.strip()]
        elif isinstance(v, list):
            return v
        return [str(v)]
    
    def __init__(self, **kwargs):
        """Initialize settings with environment-aware security."""
        super().__init__(**kwargs)
        self._apply_environment_security()
    
    def _apply_environment_security(self):
        """Apply security settings based on environment."""
        if self.ENVIRONMENT.lower() == "production":
            # Force secure settings in production
            if not self.SSL_ENABLED:
                import warnings
                warnings.warn(
                    "SSL_ENABLED is False in production environment. "
                    "This is insecure and should be fixed.",
                    UserWarning
                )
            
            # Validate production CORS origins don't include localhost
            if isinstance(self.CORS_ORIGINS, list):
                insecure_origins = [
                    origin for origin in self.CORS_ORIGINS 
                    if "localhost" in origin or "127.0.0.1" in origin
                ]
                if insecure_origins:
                    import warnings
                    warnings.warn(
                        f"Production CORS origins contain localhost/127.0.0.1: {insecure_origins}. "
                        "This is insecure in production.",
                        UserWarning
                    )
            
            # Validate production allowed hosts
            insecure_hosts = [
                host for host in self.ALLOWED_HOSTS 
                if host in ["localhost", "127.0.0.1"]
            ]
            if insecure_hosts:
                import warnings
                warnings.warn(
                    f"Production allowed hosts contain localhost/127.0.0.1: {insecure_hosts}. "
                    "This may be insecure in production.",
                    UserWarning
                )


# Create settings instance
settings = Settings()

# --- PASTE THIS EXACT CODE AT THE VERY BOTTOM OF config.py ---

class CacheConfig:
    """
    Configuration class for the cache backend (Redis).
    """
    # This is a CLASS attribute. It will be available on the instance.
    API_RESPONSE_TTL: int = 3600  # Cache API responses for 1 hour (in seconds)

    def __init__(self, config: Settings):
        # This is an INSTANCE attribute, created when the object is made.
        if config.REDIS_PASSWORD:
            self.REDIS_URL = f"redis://:{config.REDIS_PASSWORD}@{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"
        else:
            self.REDIS_URL = f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"

# This line creates the instance and makes the attributes available
cache_config = CacheConfig(settings)
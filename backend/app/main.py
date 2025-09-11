"""
Voltex SEO Decision Superiority Engine - FastAPI Application Entry Point

This module initializes and configures the FastAPI application for the Voltex DSE.
It sets up middleware, routers, and other application-wide configurations.
"""
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from app.core.config import settings
from app.api.api_v1.api import api_router
from app.auth.api_router import auth_routes
from app.core.logging import setup_logging
from app.core.structured_logging import get_logger
from app.middleware.logging_middleware import LoggingMiddleware
from app.core.middleware import GlobalExceptionHandlerMiddleware
from app.core.csrf import CSRFProtectionMiddleware
from app.core.rate_limiter import create_redis_rate_limiter
from app.core.rate_limit_dependencies import set_redis_client
from app.core.cache import cache_manager
from app.core.cache_headers import CacheHeadersMiddleware
from app.core.metrics import metrics_endpoint
from app.core.performance_monitoring import performance_metrics
from app.core.cache_warming import start_cache_warming_scheduler
from app.core.exceptions import create_error_response

# Set up logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown events."""
    # Startup
    logger.info("Starting Voltex DSE API")
    
    # Store Redis connection for proper cleanup
    redis_fastapi_cache = None

    try:
        redis_fastapi_cache = aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}", 
            encoding="utf-8", 
            decode_responses=True,
            max_connections=10,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        FastAPICache.init(RedisBackend(redis_fastapi_cache), prefix="fastapi-cache")
        app.state.redis_fastapi_cache = redis_fastapi_cache
        logger.info("FastAPI-Cache initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize FastAPI-Cache: {e}")
    
    # Initialize Redis client for rate limiting
    redis_client = await create_redis_rate_limiter()
    app.state.redis_rate_limiter = redis_client
    
    # Set Redis client for rate limiting dependencies
    set_redis_client(redis_client)
    
    # Initialize cache manager
    await cache_manager.initialize()
    app.state.cache_manager = cache_manager
    
    # Start cache warming scheduler if enabled
    if getattr(settings, 'ENABLE_CACHE_WARMING', True):
        import asyncio
        cache_warming_task = asyncio.create_task(start_cache_warming_scheduler())
        app.state.cache_warming_task = cache_warming_task
        logger.info("Cache warming scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Voltex DSE API")
    
    # Stop cache warming scheduler
    if hasattr(app.state, 'cache_warming_task'):
        app.state.cache_warming_task.cancel()
        try:
            await app.state.cache_warming_task
        except asyncio.CancelledError:
            pass
    
    # Clear and close FastAPI cache
    try:
        # Don't clear cache on shutdown - just close connections
        if hasattr(app.state, 'redis_fastapi_cache'):
            await app.state.redis_fastapi_cache.close()
            logger.info("FastAPI-Cache Redis connection closed.")
    except Exception as e:
        logger.error(f"Error closing FastAPI cache Redis connection: {e}")
    
    # Close cache manager
    if hasattr(app.state, 'cache_manager'):
        try:
            await app.state.cache_manager.close()
        except Exception as e:
            logger.error(f"Error closing cache manager: {e}")
    
    # Close Redis connection
    if hasattr(app.state, 'redis_rate_limiter'):
        try:
            await app.state.redis_rate_limiter.close()
        except Exception as e:
            logger.error(f"Error closing Redis rate limiter: {e}")

# Performance monitoring middleware
async def performance_monitoring_middleware(request: Request, call_next):
    """
    Middleware to track API performance and record metrics.
    """
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Record performance metrics
        performance_metrics.record_api_call(
            endpoint=request.url.path,
            method=request.method,
            duration=process_time,
            status_code=response.status_code
        )
        
        # Add process time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        
        # Record error metrics
        performance_metrics.record_api_call(
            endpoint=request.url.path,
            method=request.method,
            duration=process_time,
            status_code=500
        )
        
        raise

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="SEO Decision Superiority Engine API",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    redirect_slashes=False  # Disable automatic trailing slash redirects
)



# Performance monitoring middleware (add first for accurate timing)
app.middleware("http")(performance_monitoring_middleware)

# SECURITY FIX: Proper CORS configuration
# CORS must be added BEFORE exception handlers to ensure CORS headers
# are present even on error responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global exception handler - after CORS to ensure headers are preserved
app.add_middleware(GlobalExceptionHandlerMiddleware)

# SECURITY FIX: Proper trusted host middleware with specific hosts
app.add_middleware(ProxyHeadersMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Note: Rate limiting will be implemented via dependency injection in endpoints
# to avoid middleware initialization issues with async Redis setup

# SECURITY: CSRF Protection for all state-changing operations
# Only exempt read-only endpoints and CSRF token endpoint
# 
# ⚠️ TEMPORARY TESTING CONFIGURATION - DO NOT USE IN PRODUCTION ⚠️
# Some authenticated endpoints are currently exempt from CSRF protection
# to facilitate testing during development. This configuration should be
# reviewed and updated before production deployment.
#
# Properly exempt endpoints:
# - Documentation and health checks (read-only)
# - CSRF token endpoint (needs to be accessible without token)
# - Auth endpoints (handle their own CSRF via rate limiting)
# - WebSocket connections (use different auth mechanism)
#
# TEMPORARILY EXEMPT FOR TESTING (should require CSRF in production):
# - /api/v1/projects
# - /api/v1/profitability
# - /api/v1/diagnostic/site-health
#
app.add_middleware(
    CSRFProtectionMiddleware,
    secret_key=settings.SECRET_KEY,
    secure=settings.SSL_ENABLED,
    exempt_paths={
        # Always exempt - documentation and infrastructure
        "/docs", "/redoc", "/openapi.json", "/health",
        "/api/v1/csrf/token",  # Must be exempt to allow fetching CSRF token
        "/api/v1/health",  # Read-only health checks
        "/ws",  # WebSocket connections use query param auth
        "/api/v1/websocket/ws",  # Actual WebSocket endpoint path
        
        # Auth endpoints - have their own rate limiting and security
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/refresh",
        "/api/v1/auth/complete-onboarding",  # Onboarding completion endpoint
        "/api/v1/auth/google/config",  # Google OAuth flow
        "/api/v1/auth/google/login",
        "/api/v1/auth/google/callback",
        "/api/v1/auth/google/authenticate",
        
        # Secure auth endpoints - register/login/logout exempt from CSRF for initial auth
        "/api/v1/auth/secure/register",
        "/api/v1/auth/secure/login", 
        "/api/v1/auth/secure/logout",
        "/api/v1/auth/secure/csrf-token",  # Must be exempt to allow fetching CSRF token
        
        # Data-intensive endpoints that may need CSRF exemption for API clients
        "/api/v1/diagnostic/site-health",  # Health check endpoint - read-only
    }
)

# Add browser cache headers middleware
app.add_middleware(CacheHeadersMiddleware)

# Add request/response logging middleware
app.add_middleware(
    LoggingMiddleware,
    exclude_paths=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
)

# Include API routers
app.include_router(auth_routes, prefix=settings.API_V1_STR)  # Auth routes first for priority
app.include_router(api_router, prefix=settings.API_V1_STR)

# Performance monitoring middleware is already added above in the middleware section

# Exception handlers for consistent error responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with consistent format."""
    # Extract validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"][1:]),  # Skip 'body' prefix
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=422,
            details={"errors": errors}
        )
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent format."""
    # Map common HTTP status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE"
    }
    
    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_code=error_code,
            message=exc.detail,
            status_code=exc.status_code
        ),
        headers=exc.headers
    )


@app.exception_handler(HTTPException)
async def fastapi_http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions with consistent format."""
    # Map common HTTP status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE"
    }
    
    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    
    # Add CORS headers to the response
    headers = getattr(exc, 'headers', {}) or {}
    headers.update({
        "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
        "Access-Control-Allow-Credentials": "true"
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_code=error_code,
            message=exc.detail,
            status_code=exc.status_code
        ),
        headers=headers
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy", "version": "0.1.0"}

@app.get("/metrics")
async def get_metrics(request: Request):
    return await metrics_endpoint(request)
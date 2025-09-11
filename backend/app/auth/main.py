"""Main auth app router for integration."""

from fastapi import APIRouter
from app.auth.routes.auth import router as auth_router
from app.auth.routes.google import router as google_router
from app.auth.routes.users import router as users_router

# Create main auth router
auth_api_router = APIRouter(prefix="/api/v1")

# Include auth routes
auth_api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
auth_api_router.include_router(google_router, prefix="/auth", tags=["google-oauth"])
auth_api_router.include_router(users_router, prefix="/users", tags=["user-management"])

__all__ = ["auth_api_router"]
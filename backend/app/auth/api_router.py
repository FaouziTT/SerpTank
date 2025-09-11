"""Auth router for main app integration."""

from fastapi import APIRouter
from app.auth.routes.auth import router as auth_router
from app.auth.routes.auth_secure import router as auth_secure_router
from app.auth.routes.google import router as google_router

# Create auth router without the /api/v1 prefix for integration into main app
auth_routes = APIRouter()

# Include auth routes (excluding users routes to avoid conflicts with existing users endpoints)
auth_routes.include_router(auth_router, prefix="/auth", tags=["authentication"])
auth_routes.include_router(auth_secure_router, tags=["secure-authentication"])  # Prefix already included in router
auth_routes.include_router(google_router, prefix="/auth", tags=["google-oauth"])

__all__ = ["auth_routes"]
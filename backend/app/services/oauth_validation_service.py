"""
OAuth Validation Service for enforcing Google OAuth connections.

This service provides validation functions to ensure users have the required
Google OAuth connections before creating projects and organizations.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.oauth_service import GoogleOAuthService, GOOGLE_SCOPES

logger = logging.getLogger(__name__)


class OAuthValidationService:
    """Service for validating OAuth connections and scopes."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.oauth_service = GoogleOAuthService()
    
    async def validate_google_search_console_connection(self, user_id: int) -> Dict[str, any]:
        """
        Validate that user has Google Search Console OAuth connection.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            Dict with validation status and details
        """
        try:
            user = await self.db.get(User, user_id)
            if not user:
                return {
                    "valid": False,
                    "error": "User not found",
                    "action_required": "user_not_found"
                }
            
            logger.info(f"Validating Search Console for user {user_id}")
            logger.info(f"User has access_token: {bool(user.google_access_token)}")
            logger.info(f"User has refresh_token: {bool(user.google_refresh_token)}")
            logger.info(f"User scopes: {user.google_scopes}")
            logger.info(f"Required scope: {GOOGLE_SCOPES['search_console']}")
            
            # Check if user has Google OAuth tokens
            if not user.google_access_token or not user.google_refresh_token:
                logger.info("Missing OAuth tokens")
                return {
                    "valid": False,
                    "error": "Google account not connected. Please connect your Google account to access Search Console data.",
                    "action_required": "connect_google_account",
                    "oauth_url": await self._get_search_console_oauth_url(user_id)
                }
            
            # Check if tokens are expired
            if user.google_token_expires_at and user.google_token_expires_at <= datetime.now(timezone.utc):
                logger.info("OAuth tokens expired")
                return {
                    "valid": False,
                    "error": "Google tokens have expired. Please reconnect your Google account.",
                    "action_required": "refresh_google_tokens",
                    "oauth_url": await self._get_search_console_oauth_url(user_id)
                }
            
            # Check if user has Search Console scope
            has_scope = self._has_required_scope(user.google_scopes, GOOGLE_SCOPES['search_console'])
            logger.info(f"Has required scope: {has_scope}")
            
            if not has_scope:
                logger.info("Missing Search Console scope")
                return {
                    "valid": False,
                    "error": "Google Search Console access not granted. Please reconnect with Search Console permissions.",
                    "action_required": "grant_search_console_scope",
                    "oauth_url": await self._get_search_console_oauth_url(user_id)
                }
            
            logger.info("Search Console validation passed")
            return {
                "valid": True,
                "message": "Google Search Console connection verified",
                "scopes": user.google_scopes,
                "expires_at": user.google_token_expires_at
            }
            
        except Exception as e:
            logger.error(f"Error validating Google Search Console connection: {e}")
            return {
                "valid": False,
                "error": f"Failed to validate Google connection: {str(e)}",
                "action_required": "system_error"
            }
    
    async def validate_google_analytics_connection(self, user_id: int) -> Dict[str, any]:
        """
        Validate that user has Google Analytics OAuth connection.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            Dict with validation status and details
        """
        try:
            user = await self.db.get(User, user_id)
            if not user:
                return {
                    "valid": False,
                    "error": "User not found",
                    "action_required": "user_not_found"
                }
            
            logger.info(f"Validating Analytics for user {user_id}")
            logger.info(f"User has access_token: {bool(user.google_access_token)}")
            logger.info(f"User has refresh_token: {bool(user.google_refresh_token)}")
            logger.info(f"User scopes: {user.google_scopes}")
            logger.info(f"Required scope: {GOOGLE_SCOPES['analytics']}")
            
            # Check if user has Google OAuth tokens
            if not user.google_access_token or not user.google_refresh_token:
                logger.info("Missing OAuth tokens")
                return {
                    "valid": False,
                    "error": "Google account not connected. Please connect your Google account to access Analytics data.",
                    "action_required": "connect_google_account",
                    "oauth_url": await self._get_analytics_oauth_url(user_id)
                }
            
            # Check if tokens are expired
            if user.google_token_expires_at and user.google_token_expires_at <= datetime.now(timezone.utc):
                logger.info("OAuth tokens expired")
                return {
                    "valid": False,
                    "error": "Google tokens have expired. Please reconnect your Google account.",
                    "action_required": "refresh_google_tokens",
                    "oauth_url": await self._get_analytics_oauth_url(user_id)
                }
            
            # Check if user has Analytics scope
            has_scope = self._has_required_scope(user.google_scopes, GOOGLE_SCOPES['analytics'])
            logger.info(f"Has required scope: {has_scope}")
            
            if not has_scope:
                logger.info("Missing Analytics scope")
                return {
                    "valid": False,
                    "error": "Google Analytics access not granted. Please reconnect with Analytics permissions.",
                    "action_required": "grant_analytics_scope",
                    "oauth_url": await self._get_analytics_oauth_url(user_id)
                }
            
            logger.info("Analytics validation passed")
            return {
                "valid": True,
                "message": "Google Analytics connection verified",
                "scopes": user.google_scopes,
                "expires_at": user.google_token_expires_at
            }
            
        except Exception as e:
            logger.error(f"Error validating Google Analytics connection: {e}")
            return {
                "valid": False,
                "error": f"Failed to validate Google connection: {str(e)}",
                "action_required": "system_error"
            }
    
    async def validate_all_required_connections(self, user_id: int) -> Dict[str, any]:
        """
        Validate that user has all required Google OAuth connections.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            Dict with validation status for all required connections
        """
        search_console_validation = await self.validate_google_search_console_connection(user_id)
        analytics_validation = await self.validate_google_analytics_connection(user_id)
        
        all_valid = search_console_validation["valid"] and analytics_validation["valid"]
        
        result = {
            "all_valid": all_valid,
            "search_console": search_console_validation,
            "analytics": analytics_validation
        }
        
        if not all_valid:
            missing_connections = []
            if not search_console_validation["valid"]:
                missing_connections.append("Google Search Console")
            if not analytics_validation["valid"]:
                missing_connections.append("Google Analytics")
            
            result["error"] = f"Missing required connections: {', '.join(missing_connections)}"
            result["action_required"] = "connect_missing_services"
        
        return result
    
    def _has_required_scope(self, user_scopes: Optional[str], required_scope: str) -> bool:
        """Check if user has the required OAuth scope."""
        logger.info(f"Checking if user has required scope: {required_scope}")
        logger.info(f"User scopes: {user_scopes}")
        
        if not user_scopes:
            logger.info("User scopes is None/empty")
            return False
        
        try:
            scopes_list = user_scopes.split(' ') if isinstance(user_scopes, str) else user_scopes
            logger.info(f"Scopes list: {scopes_list}")
            has_scope = required_scope in scopes_list
            logger.info(f"Has scope result: {has_scope}")
            return has_scope
        except Exception as e:
            logger.error(f"Error checking scope: {e}")
            return False
    
    async def _get_search_console_oauth_url(self, user_id: int) -> str:
        """Get OAuth URL for Search Console connection."""
        try:
            return self.oauth_service.get_authorization_url(
                scopes=[GOOGLE_SCOPES['search_console']],
                user_id=str(user_id),
                state_data={"service": "search_console"}
            )
        except Exception as e:
            logger.error(f"Error generating Search Console OAuth URL: {e}")
            return ""
    
    async def _get_analytics_oauth_url(self, user_id: int) -> str:
        """Get OAuth URL for Analytics connection."""
        try:
            return self.oauth_service.get_authorization_url(
                scopes=[GOOGLE_SCOPES['analytics']],
                user_id=str(user_id),
                state_data={"service": "analytics"}
            )
        except Exception as e:
            logger.error(f"Error generating Analytics OAuth URL: {e}")
            return ""
    
    async def _get_full_oauth_url(self, user_id: int) -> str:
        """Get OAuth URL for both Search Console and Analytics."""
        try:
            return self.oauth_service.get_authorization_url(
                scopes=[GOOGLE_SCOPES['search_console'], GOOGLE_SCOPES['analytics']],
                user_id=str(user_id),
                state_data={"service": "full"}
            )
        except Exception as e:
            logger.error(f"Error generating full OAuth URL: {e}")
            return ""
    
    async def get_user_oauth_status(self, user_id: int) -> Dict[str, any]:
        """
        Get detailed OAuth status for a user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Dict with detailed OAuth status information
        """
        try:
            user = await self.db.get(User, user_id)
            if not user:
                return {"connected": False, "error": "User not found"}
            
            status = {
                "connected": bool(user.google_access_token),
                "expires_at": user.google_token_expires_at,
                "scopes": user.google_scopes,
                "google_id": user.google_id,
                "avatar_url": user.avatar_url,
                "email_verified": user.email_verified
            }
            
            if user.google_token_expires_at:
                status["expires_in_seconds"] = int(
                    (user.google_token_expires_at - datetime.now(timezone.utc)).total_seconds()
                )
                status["is_expired"] = user.google_token_expires_at <= datetime.now(timezone.utc)
            
            # Check individual scope permissions
            if user.google_scopes:
                scopes_list = user.google_scopes.split(' ') if isinstance(user.google_scopes, str) else []
                status["permissions"] = {
                    "search_console": GOOGLE_SCOPES['search_console'] in scopes_list,
                    "analytics": GOOGLE_SCOPES['analytics'] in scopes_list,
                    "analytics_edit": GOOGLE_SCOPES['analytics_edit'] in scopes_list
                }
            else:
                status["permissions"] = {
                    "search_console": False,
                    "analytics": False,
                    "analytics_edit": False
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting OAuth status: {e}")
            return {"connected": False, "error": str(e)}


# Create singleton instance
oauth_validation_service: Optional[OAuthValidationService] = None


def get_oauth_validation_service(db: AsyncSession) -> OAuthValidationService:
    """Get OAuth validation service instance."""
    return OAuthValidationService(db)
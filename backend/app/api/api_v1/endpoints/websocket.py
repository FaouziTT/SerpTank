"""
WebSocket endpoints for real-time updates.

This module provides WebSocket endpoints for real-time features
like dashboard updates, notifications, and activity feeds.
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.core.config import settings
from app.core.websocket import manager, message_handler
from app.db.session import get_db, async_session_factory
from app.models.user import User
# WebSocket authentication is handled inline in this file

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_current_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """Verify WebSocket token and return user."""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
            
        # Get user from database
        user = await db.get(User, int(user_id))
        if user is None or not user.is_active:
            return None
            
        return user
        
    except JWTError:
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    Main WebSocket endpoint for real-time updates.
    
    Clients should connect with an authentication token:
    ws://localhost:8000/api/v1/websocket/ws?token=<jwt_token>
    
    Message format:
    {
        "type": "message_type",
        "data": {...}
    }
    
    Supported message types:
    - subscribe: Subscribe to channels
    - unsubscribe: Unsubscribe from channels
    - ping: Keep connection alive
    - dashboard_update: Request dashboard data update
    - notification_read: Mark notifications as read
    """
    user = None
    
    try:
        logger.info(f"WebSocket connection attempt from {websocket.client}")
        
        # Accept the WebSocket connection first (required by ASGI spec)
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Then check authentication
        if not token:
            logger.warning("WebSocket connection attempted without token")
            await websocket.send_json({
                "type": "error",
                "message": "Authentication required",
                "code": "AUTH_REQUIRED"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
            return
        
        # Create database session for WebSocket
        async with async_session_factory() as db:
            user = await get_current_user_from_token(token, db)
        if not user:
            logger.warning("WebSocket authentication failed - invalid token")
            await websocket.send_json({
                "type": "error",
                "message": "Invalid authentication token",
                "code": "AUTH_INVALID"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token")
            return
        
        # Connect the WebSocket
        await manager.connect(websocket, user.id)
        
        # Auto-subscribe to user's personal channel
        manager.join_room(websocket, f"user_{user.id}")
        
        # Note: Organization subscriptions should be handled via explicit subscribe messages
        # since users can belong to multiple organizations
        
        logger.info(f"WebSocket connected for user {user.id} ({user.email})")
        
        # Handle messages
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await message_handler.handle_message(websocket, message)
                
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Invalid JSON format",
                    },
                    websocket
                )
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Internal server error",
                    },
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if user:
            logger.info(f"WebSocket disconnected for user {user.id}")
            
            # Notify user's personal channel
            await manager.broadcast_to_room(
                {
                    "type": "user_offline",
                    "user_id": user.id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                f"user_{user.id}"
            )
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket server status."""
    online_users = manager.get_online_users()
    
    return {
        "status": "active",
        "online_users_count": len(online_users),
        "online_users": online_users[:10],  # Return first 10 for privacy
        "rooms": {
            room: manager.get_room_user_count(room)
            for room in ["general", "updates", "notifications"]
        }
    }


# Import datetime for the disconnect notification
from datetime import datetime, timezone
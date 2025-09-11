"""
WebSocket connection manager and message handlers.

This module provides WebSocket infrastructure for real-time features.
"""
import json
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timezone
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.services.activity import activity_service
from app.services.notification import notification_service

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message routing."""
    
    def __init__(self):
        # Connection storage: user_id -> list of WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Room subscriptions: room_name -> set of WebSocket connections
        self.rooms: Dict[str, Set[WebSocket]] = {}
        # WebSocket to user mapping
        self.connection_users: Dict[WebSocket, int] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Register an already accepted WebSocket connection."""
        # Note: WebSocket should already be accepted before calling this method
        
        # Add to user connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Map connection to user
        self.connection_users[websocket] = user_id
        
        logger.info(f"User {user_id} connected via WebSocket")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        # Get user ID for this connection
        user_id = self.connection_users.get(websocket)
        
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from all rooms
        for room_name, connections in self.rooms.items():
            if websocket in connections:
                connections.remove(websocket)
        
        # Clean up empty rooms
        empty_rooms = [room for room, conns in self.rooms.items() if not conns]
        for room in empty_rooms:
            del self.rooms[room]
        
        # Remove user mapping
        if websocket in self.connection_users:
            del self.connection_users[websocket]
        
        if user_id:
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    def join_room(self, websocket: WebSocket, room_name: str):
        """Add a WebSocket to a room."""
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
        self.rooms[room_name].add(websocket)
        logger.debug(f"WebSocket joined room: {room_name}")
    
    def leave_room(self, websocket: WebSocket, room_name: str):
        """Remove a WebSocket from a room."""
        if room_name in self.rooms and websocket in self.rooms[room_name]:
            self.rooms[room_name].remove(websocket)
            if not self.rooms[room_name]:
                del self.rooms[room_name]
            logger.debug(f"WebSocket left room: {room_name}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def send_user_message(self, message: Dict[str, Any], user_id: int):
        """Send a message to all connections of a specific user."""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)
    
    async def broadcast_to_room(self, message: Dict[str, Any], room_name: str):
        """Broadcast a message to all connections in a room."""
        if room_name in self.rooms:
            disconnected = []
            for connection in self.rooms[room_name]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to room {room_name}: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)
    
    async def broadcast_to_users(self, message: Dict[str, Any], user_ids: List[int]):
        """Broadcast a message to multiple users."""
        for user_id in user_ids:
            await self.send_user_message(message, user_id)
    
    def get_online_users(self) -> List[int]:
        """Get list of currently connected user IDs."""
        return list(self.active_connections.keys())
    
    def get_room_user_count(self, room_name: str) -> int:
        """Get the number of users in a room."""
        if room_name not in self.rooms:
            return 0
        return len(self.rooms[room_name])


class MessageHandler:
    """Handles incoming WebSocket messages."""
    
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.handlers = {
            "ping": self._handle_ping,
            "subscribe": self._handle_subscribe,
            "unsubscribe": self._handle_unsubscribe,
            "dashboard_update": self._handle_dashboard_update,
            "notification_read": self._handle_notification_read,
        }
    
    async def handle_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Route message to appropriate handler."""
        msg_type = message.get("type")
        
        if msg_type not in self.handlers:
            await self.manager.send_personal_message({
                "type": "error",
                "message": f"Unknown message type: {msg_type}",
            }, websocket)
            return
        
        try:
            await self.handlers[msg_type](websocket, message.get("data", {}))
        except Exception as e:
            logger.error(f"Error handling message type {msg_type}: {e}")
            await self.manager.send_personal_message({
                "type": "error",
                "message": f"Failed to process {msg_type} message",
            }, websocket)
    
    async def _handle_ping(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle ping message for connection keepalive."""
        await self.manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, websocket)
    
    async def _handle_subscribe(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle channel subscription requests."""
        channels = data.get("channels", [])
        
        for channel in channels:
            self.manager.join_room(websocket, channel)
        
        await self.manager.send_personal_message({
            "type": "subscribed",
            "channels": channels,
        }, websocket)
    
    async def _handle_unsubscribe(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle channel unsubscription requests."""
        channels = data.get("channels", [])
        
        for channel in channels:
            self.manager.leave_room(websocket, channel)
        
        await self.manager.send_personal_message({
            "type": "unsubscribed",
            "channels": channels,
        }, websocket)
    
    async def _handle_dashboard_update(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle dashboard update requests."""
        # This is typically triggered by backend services, not client requests
        # But we can handle client-initiated refresh requests here
        user_id = self.manager.connection_users.get(websocket)
        
        if user_id:
            await self.manager.send_personal_message({
                "type": "dashboard_refresh",
                "message": "Dashboard refresh initiated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, websocket)
    
    async def _handle_notification_read(self, websocket: WebSocket, data: Dict[str, Any]):
        """Handle notification read status updates."""
        notification_ids = data.get("notification_ids", [])
        user_id = self.manager.connection_users.get(websocket)
        
        if user_id and notification_ids:
            # Update notification status in database
            async with async_session_factory() as db:
                await notification_service.mark_as_read(
                    user_id=user_id,
                    notification_ids=notification_ids,
                    db=db
                )
            
            # Broadcast to all user connections
            await self.manager.send_user_message({
                "type": "notification_read",
                "data": {
                    "notification_ids": notification_ids,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            }, user_id)


# Create singleton instances
manager = ConnectionManager()
message_handler = MessageHandler(manager)


# Helper functions for broadcasting updates from services
async def broadcast_dashboard_update(
    site_id: int,
    update_data: Dict[str, Any],
    priority: str = "normal",
    description: Optional[str] = None
):
    """Broadcast dashboard update to all users watching a site."""
    message = {
        "type": "dashboard_update",
        "data": {
            "site_id": site_id,
            "update": update_data,
            "priority": priority,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }
    
    # Broadcast to site-specific room
    await manager.broadcast_to_room(message, f"site_{site_id}")
    
    # Also broadcast to general dashboard updates room
    await manager.broadcast_to_room(message, "dashboard_updates")


async def broadcast_notification(
    user_id: int,
    notification: Dict[str, Any]
):
    """Broadcast notification to a specific user."""
    message = {
        "type": "notification",
        "data": notification
    }
    
    await manager.send_user_message(message, user_id)


async def broadcast_activity(
    organization_id: int,
    activity: Dict[str, Any]
):
    """Broadcast activity to organization members."""
    message = {
        "type": "activity",
        "data": activity
    }
    
    # Broadcast to organization activity room
    await manager.broadcast_to_room(message, f"org_{organization_id}_activities")


async def broadcast_task_update(
    user_id: int,
    task_data: Dict[str, Any]
):
    """Broadcast background task update to a specific user."""
    message = {
        "type": "task_update",
        "data": task_data
    }
    
    await manager.send_user_message(message, user_id)
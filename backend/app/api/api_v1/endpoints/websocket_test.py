"""
Simple WebSocket test endpoint to debug connection issues.
"""
from fastapi import APIRouter, WebSocket
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/test")
async def test_websocket(websocket: WebSocket):
    """Simple WebSocket test endpoint without any dependencies."""
    logger.info(f"Test WebSocket connection attempt from {websocket.client}")
    await websocket.accept()
    logger.info("Test WebSocket connection accepted")
    
    await websocket.send_text("Hello from test WebSocket!")
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received: {data}")
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        logger.info(f"Test WebSocket closed: {e}")
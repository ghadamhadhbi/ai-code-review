"""
WebSocket API endpoints - Real-time review updates - FIXED
Provides WebSocket connections for live review status updates
Compatible with Kafka event structure
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set, Dict
import structlog
import asyncio
import json
from datetime import datetime

logger = structlog.get_logger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.review_subscriptions: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket connected", total_connections=len(self.active_connections))
        
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        # Remove from all review subscriptions
        for review_id in list(self.review_subscriptions.keys()):
            self.review_subscriptions[review_id].discard(websocket)
            if not self.review_subscriptions[review_id]:
                del self.review_subscriptions[review_id]
        logger.info("WebSocket disconnected", total_connections=len(self.active_connections))
        
    async def subscribe_to_review(self, websocket: WebSocket, review_id: str):
        """Subscribe a connection to updates for a specific review"""
        if review_id not in self.review_subscriptions:
            self.review_subscriptions[review_id] = set()
        self.review_subscriptions[review_id].add(websocket)
        logger.info("Subscribed to review", review_id=review_id)
        
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("Failed to send message", error=str(e))
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
            
    async def send_to_review_subscribers(self, review_id: str, message: dict):
        """Send message to all subscribers of a specific review"""
        if review_id not in self.review_subscriptions:
            logger.debug("No subscribers for review", review_id=review_id)
            return
            
        disconnected = set()
        subscriber_count = len(self.review_subscriptions[review_id])
        
        logger.info(
            "Sending to review subscribers",
            review_id=review_id,
            subscriber_count=subscriber_count,
            message_type=message.get("type")
        )
        
        for connection in self.review_subscriptions[review_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("Failed to send review update", review_id=review_id, error=str(e))
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/reviews")
async def websocket_reviews_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time review updates
    
    Clients can send:
    - {"action": "subscribe", "review_id": "abc-123"} - Subscribe to specific review
    - {"action": "ping"} - Keep connection alive
    
    Server sends:
    - Review status updates
    - Progress updates
    - Completion notifications
    """
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for messages with timeout for heartbeat
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Parse message
                try:
                    message = json.loads(data)
                    action = message.get("action")
                    
                    if action == "subscribe":
                        review_id = message.get("review_id")
                        if review_id:
                            await manager.subscribe_to_review(websocket, str(review_id))
                            await websocket.send_json({
                                "type": "subscribed",
                                "review_id": review_id,
                                "message": f"Subscribed to review {review_id}"
                            })
                            logger.info("Client subscribed", review_id=review_id)
                    
                    elif action == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    else:
                        logger.warning("Unknown WebSocket action", action=action)
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Unknown action: {action}"
                        })
                        
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON"
                    })
                    
            except asyncio.TimeoutError:
                # Send heartbeat if no message received
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error("WebSocket error", error=str(e), exc_info=True)
    finally:
        manager.disconnect(websocket)


@router.websocket("/ws/reviews/{review_id}")
async def websocket_specific_review(websocket: WebSocket, review_id: str):
    """
    WebSocket endpoint for a specific review
    Auto-subscribes to the specified review
    """
    await manager.connect(websocket)
    
    try:
        # Auto-subscribe to this review
        await manager.subscribe_to_review(websocket, str(review_id))
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "review_id": review_id,
            "message": f"Connected to review {review_id}",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info("Client connected to specific review", review_id=review_id)
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Echo back pings
                try:
                    message = json.loads(data)
                    if message.get("action") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", review_id=review_id)
    except Exception as e:
        logger.error("WebSocket error", review_id=review_id, error=str(e), exc_info=True)
    finally:
        manager.disconnect(websocket)


# =====================================================
# Helper functions for broadcasting updates
# Called by Kafka consumer when events are received
# =====================================================

async def broadcast_review_update(review_id: str, status: str, progress: int, message: str = None, **kwargs):
    """
    Broadcast a review status update to all subscribers
    
    Args:
        review_id: Review identifier (will be converted to string)
        status: New status
        progress: Progress percentage (0-100)
        message: Optional status message
        **kwargs: Additional data to include
    """
    # Ensure review_id is string
    review_id = str(review_id)
    
    broadcast_message = {
        "type": "review_update",
        "review_id": review_id,
        "status": status,
        "progress": progress,
        "message": message or f"Status: {status}",
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs
    }
    
    await manager.send_to_review_subscribers(review_id, broadcast_message)
    logger.info(
        "Broadcasted review update",
        review_id=review_id,
        status=status,
        progress=progress
    )


async def broadcast_review_completed(review_id: str, results: dict = None, **kwargs):
    """
    Broadcast review completion notification
    
    Args:
        review_id: Review identifier (will be converted to string)
        results: Dictionary containing overall_score, summary, suggestions, etc.
        **kwargs: Additional fields for backward compatibility
    """
    # Ensure review_id is string
    review_id = str(review_id)
    
    # Handle both new format (results dict) and old format (individual params)
    if results:
        overall_score = results.get("overall_score")
        summary = results.get("summary")
        suggestion_count = results.get("suggestion_count", 0)
        suggestions = results.get("suggestions", [])
        status = results.get("status", "completed")
        progress = results.get("progress", 100)
    else:
        # Backward compatibility - accept individual params
        overall_score = kwargs.get("overall_score")
        summary = kwargs.get("summary")
        suggestion_count = kwargs.get("suggestion_count", 0)
        suggestions = kwargs.get("suggestions", [])
        status = kwargs.get("status", "completed")
        progress = kwargs.get("progress", 100)
    
    broadcast_message = {
        "type": "review_completed",
        "review_id": review_id,
        "status": status,
        "progress": progress,
        "overall_score": overall_score,
        "summary": summary,
        "suggestion_count": suggestion_count,
        "suggestions": suggestions[:5] if suggestions else [],  # First 5 suggestions
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await manager.send_to_review_subscribers(review_id, broadcast_message)
    logger.info(
        "Broadcasted review completion",
        review_id=review_id,
        overall_score=overall_score,
        suggestion_count=suggestion_count
    )


async def broadcast_review_failed(review_id: str, error_message: str, **kwargs):
    """
    Broadcast review failure notification
    
    Args:
        review_id: Review identifier (will be converted to string)
        error_message: Error description
        **kwargs: Additional fields
    """
    # Ensure review_id is string
    review_id = str(review_id)
    
    broadcast_message = {
        "type": "review_failed",
        "review_id": review_id,
        "status": "failed",
        "progress": 0,
        "error_message": error_message,
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs
    }
    
    await manager.send_to_review_subscribers(review_id, broadcast_message)
    logger.info("Broadcasted review failure", review_id=review_id, error=error_message)


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    return manager


def get_active_connections_count() -> int:
    """Get count of active WebSocket connections"""
    return len(manager.active_connections)


def get_review_subscribers_count(review_id: str) -> int:
    """Get count of subscribers for a specific review"""
    review_id = str(review_id)
    return len(manager.review_subscriptions.get(review_id, set()))
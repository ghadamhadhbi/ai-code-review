"""
API Gateway - Kafka Producer Service - FIXED
Publishes events to Kafka topics for async processing
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError, KafkaConnectionError

from core.config import settings

logger = structlog.get_logger(__name__)


class KafkaProducerService:
    """Async Kafka producer for publishing events"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.is_connected = False
        self._connection_lock = asyncio.Lock()
        self._connect_timeout = 10  # Connection timeout in seconds
        
    async def start(self):
        """Initialize and start the Kafka producer"""
        async with self._connection_lock:
            if self.is_connected:
                logger.info("Kafka producer already connected")
                return
            
            try:
                logger.info(
                    "Starting Kafka producer",
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
                )
                
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    compression_type='gzip',
                    acks='all',  # Wait for all replicas
                    max_request_size=1048576,  # 1MB max request
                    request_timeout_ms=30000,
                    metadata_max_age_ms=300000,
                    connections_max_idle_ms=540000,
                    # Memory optimization settings
                    max_batch_size=16384,  # 16KB batches
                )
                
                # Add timeout to prevent hanging
                await asyncio.wait_for(
                    self.producer.start(),
                    timeout=self._connect_timeout
                )
                self.is_connected = True
                
                logger.info("Kafka producer started successfully")
                
            except asyncio.TimeoutError:
                logger.error(
                    "Kafka producer connection timeout",
                    timeout=self._connect_timeout
                )
                self.is_connected = False
                # Don't raise - allow service to run without Kafka
                
            except KafkaConnectionError as e:
                logger.error(
                    "Kafka connection error",
                    error=str(e),
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS
                )
                self.is_connected = False
                # Don't raise - allow service to run without Kafka
                
            except Exception as e:
                logger.error("Failed to start Kafka producer", error=str(e))
                self.is_connected = False
                # Don't raise - allow service to run without Kafka
    
    async def stop(self):
        """Stop the Kafka producer gracefully"""
        async with self._connection_lock:
            if self.producer and self.is_connected:
                try:
                    logger.info("Stopping Kafka producer")
                    await self.producer.stop()
                    self.is_connected = False
                    self.producer = None  # Free memory
                    logger.info("Kafka producer stopped")
                except Exception as e:
                    logger.error("Error stopping Kafka producer", error=str(e))
    
    async def _ensure_connected(self):
        """Ensure producer is connected before sending"""
        if not self.is_connected or not self.producer:
            await self.start()
            
        # If still not connected, raise error
        if not self.is_connected:
            raise RuntimeError("Kafka producer is not available")
    
    async def _send_event(
        self,
        topic: str,
        event_data: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send an event to Kafka topic
        
        Args:
            topic: Kafka topic name
            event_data: Event data to publish
            key: Optional partition key
            headers: Optional message headers
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await self._ensure_connected()
            
            # Add metadata to event
            enriched_event = {
                **event_data,
                "event_timestamp": datetime.utcnow().isoformat(),
                "producer": "api-gateway",
                "version": "1.0"
            }
            
            # Prepare headers
            kafka_headers = []
            if headers:
                kafka_headers = [(k, v.encode('utf-8')) for k, v in headers.items()]
            
            # Add default headers
            kafka_headers.extend([
                ("producer", b"api-gateway"),
                ("timestamp", datetime.utcnow().isoformat().encode('utf-8'))
            ])
            
            # Send to Kafka
            logger.info(
                "Sending event to Kafka",
                topic=topic,
                key=key,
                event_type=event_data.get("event_type")
            )
            
            future = await self.producer.send(
                topic,
                value=enriched_event,
                key=key,
                headers=kafka_headers
            )
            
            # Wait for confirmation with timeout
            record_metadata = await asyncio.wait_for(future, timeout=10.0)
            
            logger.info(
                "Event sent successfully",
                topic=record_metadata.topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset
            )
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(
                "Timeout sending event to Kafka",
                topic=topic
            )
            return False
            
        except KafkaError as e:
            logger.error(
                "Kafka error sending event",
                topic=topic,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
        except RuntimeError as e:
            logger.warning(
                "Kafka not available, event not sent",
                topic=topic,
                error=str(e)
            )
            return False
            
        except Exception as e:
            logger.error(
                "Failed to send event to Kafka",
                topic=topic,
                error=str(e)
            )
            return False
    
    # ✅ FIX: Add the missing publish_upload_event method
    async def publish_upload_event(self, upload_data: Dict[str, Any]) -> bool:
        """
        Publish upload event for processing (alias for publish_code_upload)
        
        Args:
            upload_data: Upload information including files and metadata
            
        Returns:
            True if published successfully
        """
        return await self.publish_code_upload(upload_data)
    
    async def publish_code_upload(self, upload_data: Dict[str, Any]) -> bool:
        """
        Publish code upload event for AI review processing
        
        Args:
            upload_data: Upload information including files and metadata
            
        Returns:
            True if published successfully
        """
        event_data = {
            "event_type": "code_upload",
            "upload_id": upload_data.get("upload_id"),
            "files": upload_data.get("files", []),
            "metadata": {
                "author_email": upload_data.get("author_email"),
                "language": upload_data.get("language"),
                "description": upload_data.get("description"),
                "file_count": len(upload_data.get("files", [])),
                "total_size_bytes": sum(
                    f.get("size_bytes", f.get("size", 0)) for f in upload_data.get("files", [])
                ),
            }
        }
        
        return await self._send_event(
            topic=settings.KAFKA_TOPIC_CODE_UPLOADS,
            event_data=event_data,
            key=upload_data.get("upload_id"),
            headers={
                "event_type": "code_upload",
                "upload_id": upload_data.get("upload_id")
            }
        )
    
    async def publish_upload_status_change(
        self,
        upload_id: str,
        status: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Publish upload status change event
        
        Args:
            upload_id: Upload identifier
            status: New status (uploaded, processing, completed, failed)
            metadata: Optional additional metadata
            
        Returns:
            True if published successfully
        """
        event_data = {
            "event_type": "upload_status_change",
            "upload_id": upload_id,
            "status": status,
            "metadata": metadata or {}
        }
        
        return await self._send_event(
            topic=settings.KAFKA_TOPIC_CODE_UPLOADS,
            event_data=event_data,
            key=upload_id,
            headers={
                "event_type": "upload_status_change",
                "status": status
            }
        )
    
    async def publish_review_request(
        self,
        review_id: int,
        upload_id: str,
        files_info: list,
        options: Optional[Dict] = None
    ) -> bool:
        """
        Publish review request event
        
        Args:
            review_id: Review identifier
            upload_id: Associated upload ID
            files_info: List of files to review
            options: Optional review options (priority, focus areas, etc.)
            
        Returns:
            True if published successfully
        """
        event_data = {
            "event_type": "review_request",
            "review_id": review_id,
            "upload_id": upload_id,
            "files": files_info,
            "options": options or {}
        }
        
        return await self._send_event(
            topic=settings.KAFKA_TOPIC_CODE_UPLOADS,
            event_data=event_data,
            key=str(review_id),
            headers={
                "event_type": "review_request",
                "review_id": str(review_id)
            }
        )
    
    async def publish_review_cancelled(
        self,
        review_id: int,
        reason: Optional[str] = None
    ) -> bool:
        """
        Publish review cancellation event
        
        Args:
            review_id: Review identifier
            reason: Optional cancellation reason
            
        Returns:
            True if published successfully
        """
        event_data = {
            "event_type": "review_cancelled",
            "review_id": review_id,
            "reason": reason,
            "cancelled_at": datetime.utcnow().isoformat()
        }
        
        return await self._send_event(
            topic=settings.KAFKA_TOPIC_REVIEW_RESULTS,
            event_data=event_data,
            key=str(review_id),
            headers={
                "event_type": "review_cancelled"
            }
        )
    
    async def publish_feedback_submitted(
        self,
        review_id: int,
        feedback_data: Dict[str, Any]
    ) -> bool:
        """
        Publish user feedback event
        
        Args:
            review_id: Review identifier
            feedback_data: Feedback information
            
        Returns:
            True if published successfully
        """
        event_data = {
            "event_type": "feedback_submitted",
            "review_id": review_id,
            "feedback": feedback_data
        }
        
        return await self._send_event(
            topic=settings.KAFKA_TOPIC_REVIEW_RESULTS,
            event_data=event_data,
            key=str(review_id),
            headers={
                "event_type": "feedback_submitted"
            }
        )
    
    async def publish_user_activity(
        self,
        user_id: str,
        activity_type: str,
        activity_data: Dict[str, Any]
    ) -> bool:
        """
        Publish user activity event for analytics
        
        Args:
            user_id: User identifier
            activity_type: Type of activity
            activity_data: Activity details
            
        Returns:
            True if published successfully
        """
        event_data = {
            "event_type": "user_activity",
            "user_id": user_id,
            "activity_type": activity_type,
            "activity_data": activity_data
        }
        
        return await self._send_event(
            topic="user-activities",
            event_data=event_data,
            key=user_id,
            headers={
                "event_type": "user_activity",
                "activity_type": activity_type
            }
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Kafka producer health
        
        Returns:
            Health status information
        """
        try:
            # Don't auto-connect on health check
            return {
                "status": "healthy" if self.is_connected else "disconnected",
                "connected": self.is_connected,
                "producer_ready": self.producer is not None,
                "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }


# Singleton instance
_kafka_producer: Optional[KafkaProducerService] = None


def get_kafka_producer() -> KafkaProducerService:
    """Get or create Kafka producer singleton"""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaProducerService()
    return _kafka_producer


async def initialize_kafka_producer():
    """Initialize Kafka producer on application startup"""
    producer = get_kafka_producer()
    try:
        await producer.start()
        logger.info("Kafka producer initialized")
    except Exception as e:
        logger.warning(
            "Kafka producer initialization failed (non-critical)",
            error=str(e)
        )


async def shutdown_kafka_producer():
    """Shutdown Kafka producer on application shutdown"""
    global _kafka_producer
    if _kafka_producer:
        await _kafka_producer.stop()
        _kafka_producer = None  # Free memory
        logger.info("Kafka producer shutdown complete")


async def test_connection() -> bool:
    """
    Test Kafka connection (used by health checks)
    
    Returns:
        True if connected, False otherwise
    """
    try:
        producer = get_kafka_producer()
        
        # If not connected, try to connect with short timeout
        if not producer.is_connected:
            await asyncio.wait_for(producer.start(), timeout=5.0)
        
        return producer.is_connected
        
    except asyncio.TimeoutError:
        logger.warning("Kafka connection test timeout")
        return False
    except Exception as e:
        logger.warning("Kafka connection test failed", error=str(e))
        return False
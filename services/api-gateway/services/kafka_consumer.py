"""
API Gateway Kafka Consumer - FIXED VERSION
Listens for Review Results and broadcasts via WebSocket
"""

import asyncio
import json
from typing import Optional, Dict, Any
import structlog
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from core.config import settings
from api.websocket import broadcast_review_update, broadcast_review_completed, broadcast_review_failed

logger = structlog.get_logger(__name__)


class KafkaConsumerService:
    """Async Kafka consumer for processing review result events"""
    
    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        
    async def start(self):
        """Initialize and start the Kafka consumer"""
        try:
            logger.info(
                "Starting Kafka result consumer",
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                topic=settings.KAFKA_TOPIC_REVIEW_RESULTS
            )
            
            self.consumer = AIOKafkaConsumer(
                settings.KAFKA_TOPIC_REVIEW_RESULTS,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id="api-gateway-websocket-broadcasters",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                max_poll_records=10,
                session_timeout_ms=30000,
            )
            
            await self.consumer.start()
            self.is_running = True
            
            logger.info("✅ Kafka result consumer started successfully")
            
            # Start consuming messages
            await self._consume_messages()
            
        except Exception as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop the Kafka consumer gracefully"""
        if self.consumer and self.is_running:
            try:
                logger.info("Stopping Kafka consumer")
                self._shutdown_event.set()
                self.is_running = False
                await self.consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error("Error stopping Kafka consumer", error=str(e))
    
    async def _consume_messages(self):
        """Main message consumption loop"""
        logger.info("🚀 Starting result message consumption loop")
        
        message_count = 0
        
        try:
            async for message in self.consumer:
                if self._shutdown_event.is_set():
                    break
                
                message_count += 1
                
                try:
                    logger.info(
                        "📨 Received result message",
                        message_number=message_count,
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset
                    )
                    
                    await self._process_message(message)
                    
                except Exception as e:
                    logger.error(
                        "Error processing message",
                        error=str(e),
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset
                    )
                    
        except asyncio.CancelledError:
            logger.info("Message consumption cancelled")
        except Exception as e:
            logger.error("Fatal error in consumption loop", error=str(e))
        finally:
            logger.info("Message consumption loop ended", messages_processed=message_count)
    
    async def _process_message(self, message):
        """Process a single Kafka message"""
        try:
            event_data = message.value
            
            if not event_data:
                logger.warning("Received empty message - skipping")
                return
            
            event_type = event_data.get("event_type")
            
            # Ignore heartbeat messages
            if event_type == "heartbeat":
                return
            
            upload_id = event_data.get("upload_id")
            review_id = event_data.get("review_id")
            
            logger.info(
                "Processing result event",
                event_type=event_type,
                upload_id=upload_id,
                review_id=review_id
            )
            
            # Route to appropriate handler based on event type
            if event_type == "review_status_update":
                await self._handle_status_update(event_data)
            elif event_type == "review_completed":
                await self._handle_review_completed(event_data)
            elif event_type == "review_failed":
                await self._handle_review_failed(event_data)
            else:
                logger.warning("Unknown event type", event_type=event_type)
                
        except Exception as e:
            logger.error("Error in _process_message", error=str(e), exc_info=True)
    
    async def _handle_status_update(self, event_data: Dict[str, Any]):
        """Handle review status update event"""
        try:
            review_id = str(event_data.get("review_id") or event_data.get("upload_id"))
            status = event_data.get("status", "processing")
            progress = event_data.get("progress", 0)
            message_text = event_data.get("message", "Processing...")
            
            logger.info(
                "📡 Broadcasting status update",
                review_id=review_id,
                status=status,
                progress=progress
            )
            
            await broadcast_review_update(
                review_id=review_id,
                status=status,
                progress=progress,
                message=message_text
            )
            
        except Exception as e:
            logger.error("Failed to handle status update", error=str(e))
    
    async def _handle_review_completed(self, event_data: Dict[str, Any]):
        """Handle review completion event - FIX: Ensure proper broadcasting"""
        try:
            review_id = str(event_data.get("review_id") or event_data.get("upload_id"))
            
            results = {
                "overall_score": event_data.get("overall_score"),
                "summary": event_data.get("summary"),
                "suggestion_count": event_data.get("suggestion_count", 0),
                "suggestions": event_data.get("suggestions", []),
                "status": "completed",
                "progress": 100
            }
            
            logger.info(
                "📡 Broadcasting review completion",
                review_id=review_id,
                overall_score=results["overall_score"],
                suggestion_count=results["suggestion_count"]
            )
            
            # ✅ FIX: Broadcast completion
            await broadcast_review_completed(
                review_id=review_id,
                results=results
            )
            
            logger.info(
                "✅ Review completion broadcasted successfully",
                review_id=review_id
            )
            
        except Exception as e:
            logger.error("Failed to handle review completion", error=str(e), exc_info=True)
    
    async def _handle_review_failed(self, event_data: Dict[str, Any]):
        """Handle review failure event"""
        try:
            review_id = str(event_data.get("review_id") or event_data.get("upload_id"))
            error_message = event_data.get("error_message", "Review failed")
            
            logger.info(
                "📡 Broadcasting review failure",
                review_id=review_id,
                error=error_message
            )
            
            await broadcast_review_failed(
                review_id=review_id,
                error_message=error_message
            )
            
        except Exception as e:
            logger.error("Failed to handle review failure", error=str(e))
    
    def health_check(self) -> Dict[str, Any]:
        """Check consumer health"""
        return {
            "status": "healthy" if self.is_running else "stopped",
            "running": self.is_running,
            "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "topic": settings.KAFKA_TOPIC_REVIEW_RESULTS
        }


# Singleton instance
_kafka_consumer: Optional[KafkaConsumerService] = None


def get_kafka_consumer() -> KafkaConsumerService:
    """Get or create Kafka consumer singleton"""
    global _kafka_consumer
    if _kafka_consumer is None:
        _kafka_consumer = KafkaConsumerService()
    return _kafka_consumer


async def start_kafka_consumer():
    """Start Kafka consumer (call this from a background task)"""
    consumer = get_kafka_consumer()
    await consumer.start()


async def stop_kafka_consumer():
    """Stop Kafka consumer"""
    global _kafka_consumer
    if _kafka_consumer:
        await _kafka_consumer.stop()
        _kafka_consumer = None
"""
AI Review Service - Kafka Consumer - FIXED
Listens for code upload events and processes them
"""

import asyncio
import json
from typing import Optional, Any
import structlog
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from core.config import settings
from services.review_processor import get_review_processor

logger = structlog.get_logger(__name__)


class KafkaConsumerService:
    """Async Kafka consumer for processing code upload events"""
    
    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[Any] = None
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self.review_processor = get_review_processor()
        
    async def start(self):
        """Initialize and start the Kafka consumer"""
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Attempting to start Kafka consumer",
                    attempt=attempt,
                    max_retries=max_retries,
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    topic=settings.KAFKA_TOPIC_CODE_UPLOADS
                )
                
                # Create consumer
                self.consumer = AIOKafkaConsumer(
                    settings.KAFKA_TOPIC_CODE_UPLOADS,
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    group_id="ai-review-service-processors",
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                    max_poll_records=5,
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=10000,
                )
                
                # Start consumer
                await self.consumer.start()
                self.is_running = True
                
                logger.info("✅ Kafka consumer and producer connected successfully", 
                           topic=settings.KAFKA_TOPIC_CODE_UPLOADS,
                           group_id="ai-review-service-processors")
                
                # Start consuming messages
                await self._consume_messages()
                break
                
            except Exception as e:
                logger.error(
                    "Failed to start Kafka consumer",
                    attempt=attempt,
                    error=str(e)
                )
                
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached. Kafka consumer not started.")
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
        logger.info("🚀 Starting message consumption loop - Ready for messages")
        
        message_count = 0
        
        try:
            async for message in self.consumer:
                if self._shutdown_event.is_set():
                    break
                
                message_count += 1
                
                try:
                    logger.info(
                        "📨 New message received",
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
            upload_id = event_data.get("upload_id")
            
            logger.info(
                "Processing message",
                event_type=event_type,
                upload_id=upload_id
            )
            
            # Process code upload event
            if event_type == "code_upload":
                await self.review_processor.process_upload(event_data)
            else:
                logger.warning("Unknown event type", event_type=event_type)
                
        except Exception as e:
            logger.error("Error in _process_message", error=str(e), exc_info=True)
    
    def health_check(self):
        """Check consumer health"""
        return {
            "status": "healthy" if self.is_running else "stopped",
            "running": self.is_running,
            "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "topic": settings.KAFKA_TOPIC_CODE_UPLOADS
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
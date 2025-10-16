# =====================================================
# services/notification/services/kafka_consumer.py
# =====================================================

import asyncio
import json
from datetime import datetime
from typing import Dict, Optional
import structlog
from aiokafka import AIOKafkaConsumer

from core.config import settings
from services.email_service import EmailService

logger = structlog.get_logger(__name__)


class NotificationConsumer:
    """Kafka consumer for processing notification events"""
    
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.is_running = False
        self.messages_processed = 0
        self.messages_failed = 0
        self.last_processed_time: Optional[datetime] = None
        self.start_time = datetime.utcnow()
    
    async def start(self):
        """Start the Kafka consumer"""
        try:
            logger.info("Starting Notification Kafka consumer")
            
            self.consumer = AIOKafkaConsumer(
                settings.KAFKA_TOPIC_REVIEW_RESULTS,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id="notification-service",
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
            )
            
            await self.consumer.start()
            self.is_running = True
            
            logger.info("Notification consumer started, listening for review results")
            
            # Start consuming messages
            async for message in self.consumer:
                if not self.is_running:
                    break
                
                try:
                    await self._process_message(message)
                    self.messages_processed += 1
                    self.last_processed_time = datetime.utcnow()
                    
                except Exception as e:
                    logger.error("Message processing failed", error=str(e))
                    self.messages_failed += 1
            
        except Exception as e:
            logger.error("Notification consumer failed", error=str(e))
            self.is_running = False
        
        finally:
            if self.consumer:
                await self.consumer.stop()
                logger.info("Notification consumer stopped")
    
    async def stop(self):
        """Stop the Kafka consumer"""
        logger.info("Stopping Notification consumer")
        self.is_running = False
        
        if self.consumer:
            await self.consumer.stop()
    
    async def _process_message(self, message):
        """Process a single Kafka message"""
        try:
            data = message.value
            
            logger.debug(
                "Processing notification message",
                event_type=data.get("event_type"),
                offset=message.offset
            )
            
            if data.get("event_type") == "review_completed":
                await self._process_review_completion(data)
            else:
                logger.debug("Ignoring non-completion event", 
                           event_type=data.get("event_type"))
            
        except Exception as e:
            logger.error("Message processing error", error=str(e))
            raise
    
    async def _process_review_completion(self, data: Dict):
        """Process review completion event"""
        try:
            # Send completion email
            success = await self.email_service.send_review_completion_email(data)
            
            if success:
                logger.info("Review completion notification sent", 
                          review_id=data.get("review_id"))
            else:
                logger.warning("Failed to send review completion notification", 
                             review_id=data.get("review_id"))
        
        except Exception as e:
            logger.error("Failed to process review completion", error=str(e))
    
    def get_uptime_seconds(self) -> int:
        """Get consumer uptime in seconds"""
        return int((datetime.utcnow() - self.start_time).total_seconds())


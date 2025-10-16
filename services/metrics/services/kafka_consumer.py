# =====================================================
# services/metrics/services/kafka_consumer.py
# =====================================================

import asyncio
import json
from aiokafka import AIOKafkaConsumer
import structlog

from core.config import settings

logger = structlog.get_logger(__name__)


class MetricsConsumer:
    def __init__(self, data_aggregator):
        self.data_aggregator = data_aggregator
        self.consumer = None
        self.is_running = False
        self.messages_processed = 0
        self.messages_failed = 0
        
    async def start(self):
        """Start Kafka consumer"""
        try:
            self.consumer = AIOKafkaConsumer(
                settings.KAFKA_TOPIC_REVIEW_RESULTS,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_CONSUMER_GROUP,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            
            await self.consumer.start()
            self.is_running = True
            logger.info("✅ Metrics consumer started")
            
            async for message in self.consumer:
                try:
                    await self.process_message(message.value)
                    self.messages_processed += 1
                except Exception as e:
                    logger.error("Error processing message", error=str(e))
                    self.messages_failed += 1
                    
        except Exception as e:
            logger.error("Kafka consumer error", error=str(e))
            self.is_running = False
            
    async def stop(self):
        """Stop Kafka consumer"""
        self.is_running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("Metrics consumer stopped")
            
    async def process_message(self, data):
        """Process incoming metrics message"""
        event_type = data.get("event_type")
        
        if event_type == "review_completed":
            await self.data_aggregator.record_review_completion(data)
        elif event_type == "review_failed":
            await self.data_aggregator.record_review_failure(data)
            
        logger.debug("Processed metrics event", event_type=event_type)

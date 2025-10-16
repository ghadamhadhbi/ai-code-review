"""
Metrics Service - Kafka Consumer and Data Aggregation Services
"""

# =====================================================
# services/metrics/services/kafka_consumer.py
# =====================================================

import asyncio
import json
from datetime import datetime
from typing import Dict, Optional
import structlog
from aiokafka import AIOKafkaConsumer

from core.config import settings
from services.data_aggregator import DataAggregator

logger = structlog.get_logger(__name__)


class MetricsConsumer:
    """Kafka consumer for processing review results and metrics events"""
    
    def __init__(self, data_aggregator: DataAggregator):
        self.data_aggregator = data_aggregator
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.is_running = False
        self.messages_processed = 0
        self.messages_failed = 0
        self.last_processed_time: Optional[datetime] = None
        self.start_time = datetime.utcnow()
    
    async def start(self):
        """Start the Kafka consumer"""
        try:
            logger.info("Starting Metrics Kafka consumer")
            
            self.consumer = AIOKafkaConsumer(
                settings.KAFKA_TOPIC_REVIEW_RESULTS,
                settings.KAFKA_TOPIC_METRICS,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id="metrics-service",
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
            )
            
            await self.consumer.start()
            self.is_running = True
            
            logger.info("Metrics consumer started, listening for events")
            
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
            logger.error("Metrics consumer failed", error=str(e))
            self.is_running = False
        
        finally:
            if self.consumer:
                await self.consumer.stop()
                logger.info("Metrics consumer stopped")
    
    async def stop(self):
        """Stop the Kafka consumer"""
        logger.info("Stopping Metrics consumer")
        self.is_running = False
        
        if self.consumer:
            await self.consumer.stop()
    
    async def _process_message(self, message):
        """Process a single Kafka message"""
        try:
            data = message.value
            topic = message.topic
            
            logger.debug(
                "Processing metrics message",
                topic=topic,
                event_type=data.get("event_type"),
                offset=message.offset
            )
            
            if topic == settings.KAFKA_TOPIC_REVIEW_RESULTS:
                await self._process_review_result(data)
            elif topic == settings.KAFKA_TOPIC_METRICS:
                await self._process_metric_event(data)
            else:
                logger.warning("Unknown topic", topic=topic)
            
        except Exception as e:
            logger.error("Message processing error", error=str(e))
            raise
    
    async def _process_review_result(self, data: Dict):
        """Process review completion events"""
        try:
            event_data = data.get("data", data)
            
            if data.get("event_type") == "review_completed":
                # Extract metrics from review completion
                metrics = {
                    "upload_id": event_data.get("upload_id"),
                    "review_id": event_data.get("review_id"),
                    "overall_score": event_data.get("overall_score"),
                    "suggestions_count": event_data.get("suggestions_count", 0),
                    "tokens_used": event_data.get("tokens_used", 0),
                    "processing_time_ms": event_data.get("processing_time_ms", 0),
                    "timestamp": event_data.get("timestamp")
                }
                
                await self.data_aggregator.process_review_metrics(metrics)
                
                logger.debug("Processed review completion metrics", 
                           review_id=metrics["review_id"])
        
        except Exception as e:
            logger.error("Failed to process review result", error=str(e))
    
    async def _process_metric_event(self, data: Dict):
        """Process general metric events"""
        try:
            event_data = data.get("data", data)
            
            await self.data_aggregator.process_metric_event(event_data)
            
            logger.debug("Processed metric event", 
                       metric_type=event_data.get("type"))
        
        except Exception as e:
            logger.error("Failed to process metric event", error=str(e))
    
    def get_uptime_seconds(self) -> int:
        """Get consumer uptime in seconds"""
        return int((datetime.utcnow() - self.start_time).total_seconds())


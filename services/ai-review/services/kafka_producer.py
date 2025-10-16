"""
AI Review Service - Kafka Producer - FIXED
Publishes review results and status updates
"""

import json
from typing import Dict, Optional
import structlog
from aiokafka import AIOKafkaProducer
from datetime import datetime

from core.config import settings

logger = structlog.get_logger(__name__)


class ReviewKafkaProducer:
    """Kafka producer for review service events"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
    
    async def _get_producer(self) -> AIOKafkaProducer:
        """Get or create Kafka producer"""
        if not self.producer:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                acks='all',
                compression_type='gzip'
            )
            await self.producer.start()
            logger.info("Kafka producer started", topic=settings.KAFKA_TOPIC_REVIEW_RESULTS)
        
        return self.producer
    
    async def publish_status_update(self, upload_id: str, status: str, progress: int, message: str = None) -> bool:
        """
        ✅ FIX: Publish status update with proper event structure
        """
        try:
            producer = await self._get_producer()
            
            event_data = {
                "event_type": "review_status_update",
                "upload_id": upload_id,
                "status": status,
                "progress": progress,
                "message": message or f"Status: {status}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await producer.send(
                topic=settings.KAFKA_TOPIC_REVIEW_RESULTS,
                value=event_data,
                key=upload_id
            )
            
            logger.info(
                "📤 Published status update",
                upload_id=upload_id,
                status=status,
                progress=progress
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to publish status update", error=str(e))
            return False
    
    async def publish_review_result(self, result_data: Dict) -> bool:
        """
        ✅ FIX: Publish review completion with proper event structure
        """
        try:
            producer = await self._get_producer()
            
            # Prepare event with all necessary fields
            event_data = {
                "event_type": "review_completed",
                "upload_id": result_data.get("upload_id"),
                "review_id": result_data.get("review_id"),
                "overall_score": result_data.get("overall_score"),
                "summary": result_data.get("summary"),
                "suggestions": result_data.get("suggestions", []),
                "suggestion_count": len(result_data.get("suggestions", [])),
                "tokens_used": result_data.get("tokens_used", 0),
                "processing_time_ms": result_data.get("processing_time_ms", 0),
                "model_used": result_data.get("model_used"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await producer.send(
                topic=settings.KAFKA_TOPIC_REVIEW_RESULTS,
                value=event_data,
                key=result_data.get("upload_id")
            )
            
            logger.info(
                "📤 Published review completion",
                upload_id=result_data.get("upload_id"),
                review_id=result_data.get("review_id"),
                overall_score=result_data.get("overall_score")
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to publish review result", error=str(e))
            return False
    
    async def publish_review_failed(self, upload_id: str, error_message: str) -> bool:
        """
        ✅ FIX: Publish review failure event
        """
        try:
            producer = await self._get_producer()
            
            event_data = {
                "event_type": "review_failed",
                "upload_id": upload_id,
                "error_message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await producer.send(
                topic=settings.KAFKA_TOPIC_REVIEW_RESULTS,
                value=event_data,
                key=upload_id
            )
            
            logger.info("📤 Published review failure", upload_id=upload_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to publish review failure", error=str(e))
            return False
    
    async def close(self):
        """Close the producer"""
        if self.producer:
            await self.producer.stop()
            self.producer = None
            logger.info("Kafka producer closed")


# Singleton instance
_kafka_producer_instance: Optional[ReviewKafkaProducer] = None


def get_kafka_producer() -> ReviewKafkaProducer:
    """Get Kafka producer instance"""
    global _kafka_producer_instance
    if _kafka_producer_instance is None:
        _kafka_producer_instance = ReviewKafkaProducer()
    return _kafka_producer_instance


async def close_kafka_producer():
    """Close Kafka producer"""
    global _kafka_producer_instance
    if _kafka_producer_instance:
        await _kafka_producer_instance.close()
        _kafka_producer_instance = None
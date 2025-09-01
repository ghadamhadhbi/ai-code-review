"""
Kafka Producer for publishing events
"""

import json
import structlog
from kafka import KafkaProducer as Producer
from kafka.errors import KafkaError as KafkaException
from typing import Dict, Any, Optional
import asyncio

from core.config import settings
from core.exceptions import KafkaError

logger = structlog.get_logger(__name__)


class KafkaProducer:
    """Kafka producer for publishing events"""
    
    def __init__(self):
        self.producer: Optional[Producer] = None
        self._connect()
    
    def _connect(self):
        """Initialize Kafka producer connection"""
        try:
            logger.info("Initializing Kafka producer", servers=settings.KAFKA_BOOTSTRAP_SERVERS)
            
            self.producer = Producer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                # Producer configuration for reliability
                acks='all',  # Wait for all replicas
                retries=3,
                retry_backoff_ms=1000,
                max_in_flight_requests_per_connection=1,
                enable_idempotence=True,
                # Batching for performance
                batch_size=16384,
                linger_ms=10,
                compression_type='gzip',
            )
            
            logger.info("Kafka producer initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Kafka producer", error=str(e))
            raise KafkaError(f"Kafka producer initialization failed: {str(e)}")
    
    async def publish_upload_event(self, upload_data: Dict[str, Any]) -> bool:
        """Publish code upload event to Kafka"""
        try:
            if not self.producer:
                self._connect()
            
            upload_id = upload_data.get("upload_id")
            
            logger.info(
                "Publishing upload event",
                upload_id=upload_id,
                topic=settings.KAFKA_TOPIC_CODE_UPLOADS,
            )
            
            # Send message asynchronously but wait for result
            future = self.producer.send(
                settings.KAFKA_TOPIC_CODE_UPLOADS,
                key=upload_id,
                value=upload_data,
            )
            
            # Wait for the message to be sent
            record_metadata = future.get(timeout=10)
            
            logger.info(
                "Upload event published successfully",
                upload_id=upload_id,
                topic=record_metadata.topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
            )
            
            return True
            
        except KafkaException as e:
            logger.error(
                "Failed to publish upload event",
                upload_id=upload_data.get("upload_id"),
                error=str(e),
            )
            raise KafkaError(f"Failed to publish upload event: {str(e)}")
        
        except Exception as e:
            logger.error(
                "Unexpected error publishing upload event",
                upload_id=upload_data.get("upload_id"),
                error=str(e),
            )
            raise KafkaError(f"Unexpected error publishing upload event: {str(e)}")
    
    async def publish_metrics_event(self, metrics_data: Dict[str, Any]) -> bool:
        """Publish metrics event to Kafka"""
        try:
            if not self.producer:
                self._connect()
            
            logger.debug("Publishing metrics event", data=metrics_data)
            
            future = self.producer.send(
                'metrics',  # Metrics topic
                value=metrics_data,
            )
            
            future.get(timeout=5)
            logger.debug("Metrics event published successfully")
            
            return True
            
        except Exception as e:
            logger.error("Failed to publish metrics event", error=str(e))
            return False
    
    def close(self):
        """Close Kafka producer connection"""
        if self.producer:
            logger.info("Closing Kafka producer")
            self.producer.close(timeout=5)
            self.producer = None


async def test_connection():
    """Test Kafka connection"""
    try:
        producer = KafkaProducer()
        
        # Test publishing a simple message
        test_data = {
            "test": True,
            "timestamp": str(asyncio.get_event_loop().time()),
            "message": "Connection test"
        }
        
        await producer.publish_metrics_event(test_data)
        producer.close()
        
        logger.info("Kafka connection test successful")
        return True
        
    except Exception as e:
        logger.error("Kafka connection test failed", error=str(e))
        raise KafkaError(f"Kafka connection test failed: {str(e)}")


# Global producer instance
_kafka_producer: Optional[KafkaProducer] = None


def get_kafka_producer() -> KafkaProducer:
    """Get global Kafka producer instance"""
    global _kafka_producer
    
    if not _kafka_producer:
        _kafka_producer = KafkaProducer()
    
    return _kafka_producer
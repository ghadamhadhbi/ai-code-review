# =====================================================
# services/shared/kafka/producer.py
# =====================================================

"""
Base Kafka producer for all services
"""

import json
from typing import Dict, Any, Optional
import structlog
from aiokafka import AIOKafkaProducer

logger = structlog.get_logger(__name__)


class BaseKafkaProducer:
    """Base Kafka producer with common functionality"""
    
    def __init__(self, bootstrap_servers: str, service_name: str):
        self.bootstrap_servers = bootstrap_servers
        self.service_name = service_name
        self.producer: Optional[AIOKafkaProducer] = None
    
    async def start(self):
        """Start the Kafka producer"""
        if not self.producer:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                enable_idempotence=True,
            )
            
            await self.producer.start()
            logger.info("Kafka producer started", service=self.service_name)
    
    async def stop(self):
        """Stop the Kafka producer"""
        if self.producer:
            await self.producer.stop()
            self.producer = None
            logger.info("Kafka producer stopped", service=self.service_name)
    
    async def publish(self, topic: str, message: Dict[str, Any], key: Optional[str] = None):
        """Publish a message to Kafka"""
        if not self.producer:
            await self.start()
        
        try:
            # Add metadata
            enriched_message = {
                "service": self.service_name,
                "timestamp": message.get("timestamp"),
                "data": message
            }
            
            await self.producer.send(topic, value=enriched_message, key=key)
            
            logger.debug(
                "Message published",
                topic=topic,
                key=key,
                service=self.service_name
            )
            
        except Exception as e:
            logger.error("Failed to publish message", topic=topic, error=str(e))
            raise


# =====================================================
# services/shared/kafka/consumer.py
# =====================================================

"""
Base Kafka consumer for all services
"""

import json
from typing import Dict, Any, Callable, Optional
import structlog
from aiokafka import AIOKafkaConsumer

logger = structlog.get_logger(__name__)


class BaseKafkaConsumer:
    """Base Kafka consumer with common functionality"""
    
    def __init__(self, bootstrap_servers: str, service_name: str, 
                 group_id: str, message_handler: Callable):
        self.bootstrap_servers = bootstrap_servers
        self.service_name = service_name
        self.group_id = group_id
        self.message_handler = message_handler
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.is_running = False
    
    async def start(self, topics: list):
        """Start consuming from topics"""
        try:
            self.consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
            )
            
            await self.consumer.start()
            self.is_running = True
            
            logger.info("Kafka consumer started", 
                       service=self.service_name, 
                       topics=topics)
            
            # Start consuming
            async for message in self.consumer:
                if not self.is_running:
                    break
                
                try:
                    await self.message_handler(message)
                except Exception as e:
                    logger.error("Message handler failed", error=str(e))
        
        except Exception as e:
            logger.error("Kafka consumer failed", error=str(e))
            raise
        
        finally:
            if self.consumer:
                await self.consumer.stop()
    
    async def stop(self):
        """Stop the consumer"""
        self.is_running = False
        if self.consumer:
            await self.consumer.stop()
        
        logger.info("Kafka consumer stopped", service=self.service_name)
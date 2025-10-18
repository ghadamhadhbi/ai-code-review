"""
Kafka Consumer for Metrics Service - FIXED VERSION
Listens to review results and updates metrics
"""

import asyncio
import json
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
import structlog

from core.config import settings
from core.database import is_db_available

logger = structlog.get_logger(__name__)

# Global consumer reference
consumer = None
is_running = False


async def start_kafka_consumer(aggregator):
    """Start Kafka consumer to listen for review results"""
    global consumer, is_running
    
    try:
        logger.info(
            "Initializing Kafka consumer",
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            topic=settings.KAFKA_TOPIC_REVIEW_RESULTS,
            group_id="metrics-service-group",
        )
        
        consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPIC_REVIEW_RESULTS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id="metrics-service-group",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        )
        
        await consumer.start()
        is_running = True
        logger.info("✅ Kafka consumer started successfully")
        
        # Consume messages
        async for message in consumer:
            try:
                if not is_running:
                    break
                
                data = message.value
                event_type = data.get("event_type")
                
                logger.debug(
                    "Received Kafka message",
                    event_type=event_type,
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                )
                
                # Skip if database not available
                if not is_db_available():
                    logger.debug("Database not available - skipping message processing")
                    continue
                
                # Process based on event type
                if event_type == "review_completed":
                    await aggregator.record_review_completion(data)
                elif event_type == "review_failed":
                    await aggregator.record_review_failure(data)
                elif event_type == "status_update":
                    await aggregator.record_status_update(data)
                else:
                    logger.warning("Unknown event type", event_type=event_type)
                    
            except Exception as e:
                logger.error(
                    "Error processing Kafka message",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                
    except KafkaError as e:
        logger.error(
            "Kafka error in consumer",
            error=str(e),
            error_type=type(e).__name__,
        )
    except Exception as e:
        logger.error(
            "Unexpected error in Kafka consumer",
            error=str(e),
            error_type=type(e).__name__,
        )
    finally:
        is_running = False
        if consumer:
            try:
                await consumer.stop()
                logger.info("Kafka consumer stopped")
            except Exception as e:
                logger.error("Error stopping consumer", error=str(e))


async def stop_kafka_consumer():
    """Stop the Kafka consumer"""
    global consumer, is_running
    
    is_running = False
    
    if consumer:
        try:
            await consumer.stop()
            logger.info("Kafka consumer stopped successfully")
        except Exception as e:
            logger.error("Error stopping Kafka consumer", error=str(e))
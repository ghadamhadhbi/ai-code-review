"""
AI Review Service - Services Package
"""

from .review_processor import get_review_processor, ReviewProcessor
from .kafka_consumer import get_kafka_consumer, start_kafka_consumer, stop_kafka_consumer
from .kafka_producer import get_kafka_producer, close_kafka_producer

__all__ = [
    "get_review_processor",
    "ReviewProcessor",
    "get_kafka_consumer",
    "start_kafka_consumer",
    "stop_kafka_consumer",
    "get_kafka_producer",
    "close_kafka_producer"
]
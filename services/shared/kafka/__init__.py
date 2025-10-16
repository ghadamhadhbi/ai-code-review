# =====================================================
# services/shared/kafka/__init__.py
# =====================================================

"""
Kafka utilities for all services
"""

from .producer import BaseKafkaProducer
from .consumer import BaseKafkaConsumer

__all__ = ["BaseKafkaProducer", "BaseKafkaConsumer"]
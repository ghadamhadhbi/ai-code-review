
# =====================================================
# services/metrics/core/config.py
# =====================================================

import os
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class Settings:
    """Metrics Service Configuration"""
    
    def __init__(self):
        # Database Configuration
        self.DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://admin:password123@postgres:5432/code_review"
        )
        
        # Kafka Configuration
        self.KAFKA_BOOTSTRAP_SERVERS = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "kafka:29092"
        )
        self.KAFKA_TOPIC_REVIEW_RESULTS = os.getenv(
            "KAFKA_TOPIC_REVIEW_RESULTS",
            "review-results"
        )
        self.KAFKA_TOPIC_METRICS = os.getenv(
            "KAFKA_TOPIC_METRICS",
            "metrics"
        )
        
        # Metrics Configuration
        self.AGGREGATION_INTERVAL_MINUTES = int(os.getenv("AGGREGATION_INTERVAL_MINUTES", "5"))
        self.RETENTION_DAYS = int(os.getenv("METRICS_RETENTION_DAYS", "90"))
        self.CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "10"))
        
        # Application Configuration
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        self._validate_settings()
    
    def _validate_settings(self):
        """Validate configuration"""
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        
        if not self.KAFKA_BOOTSTRAP_SERVERS:
            raise ValueError("KAFKA_BOOTSTRAP_SERVERS is required")
        
        logger.info(
            "Metrics service configuration loaded",
            aggregation_interval=self.AGGREGATION_INTERVAL_MINUTES,
            retention_days=self.RETENTION_DAYS,
            environment=self.ENVIRONMENT
        )
    
    @staticmethod
    def get_current_time() -> datetime:
        """Get current UTC timestamp"""
        return datetime.utcnow()


settings = Settings()


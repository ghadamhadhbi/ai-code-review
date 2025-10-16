
# =====================================================
# services/notification/core/config.py
# =====================================================

import os
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class Settings:
    """Notification Service Configuration"""
    
    def __init__(self):
        # Kafka Configuration
        self.KAFKA_BOOTSTRAP_SERVERS = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "kafka:29092"
        )
        self.KAFKA_TOPIC_REVIEW_RESULTS = os.getenv(
            "KAFKA_TOPIC_REVIEW_RESULTS",
            "review-results"
        )
        
        # SMTP Configuration
        self.SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME = os.getenv("SMTP_USERNAME")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        self.SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
        self.SMTP_TO_EMAIL = os.getenv("SMTP_TO_EMAIL")  # Default recipient
        
        # Email Configuration
        self.EMAIL_TIMEOUT_SECONDS = int(os.getenv("EMAIL_TIMEOUT_SECONDS", "30"))
        self.MAX_EMAIL_RETRIES = int(os.getenv("MAX_EMAIL_RETRIES", "3"))
        self.EMAIL_RATE_LIMIT = int(os.getenv("EMAIL_RATE_LIMIT", "10"))  # emails per minute
        
        # Application Configuration
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        self._validate_settings()
    
    def _validate_settings(self):
        """Validate configuration"""
        if not self.SMTP_USERNAME or not self.SMTP_PASSWORD:
            logger.warning("SMTP credentials not provided - email sending will be disabled")
        
        if not self.SMTP_FROM_EMAIL:
            logger.warning("SMTP_FROM_EMAIL not provided - using username as sender")
            self.SMTP_FROM_EMAIL = self.SMTP_USERNAME
        
        logger.info(
            "Notification service configuration loaded",
            smtp_server=self.SMTP_SERVER,
            smtp_port=self.SMTP_PORT,
            from_email=self.SMTP_FROM_EMAIL,
            environment=self.ENVIRONMENT
        )
    
    @staticmethod
    def get_current_time() -> datetime:
        """Get current UTC timestamp"""
        return datetime.utcnow()


settings = Settings()


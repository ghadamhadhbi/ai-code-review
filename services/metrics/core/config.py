
# =====================================================
# services/metrics/core/config.py
# =====================================================

import os
from datetime import datetime

class Settings:
    # Service
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aireviewer:SecurePass123!@postgres:5432/ai_code_review")
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    KAFKA_TOPIC_CODE_UPLOADS = os.getenv("KAFKA_TOPIC_CODE_UPLOADS", "code-uploads")
    KAFKA_TOPIC_REVIEW_RESULTS = os.getenv("KAFKA_TOPIC_REVIEW_RESULTS", "review-results")
    KAFKA_CONSUMER_GROUP = "metrics-service-group"
    
    @staticmethod
    def get_current_time():
        return datetime.utcnow().isoformat()

settings = Settings()

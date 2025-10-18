"""
Metrics Service Configuration
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://aireviewer:SecurePass123!@postgres:5432/ai_code_review"
    )
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 20
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    KAFKA_TOPIC_REVIEW_RESULTS: str = os.getenv("KAFKA_TOPIC_REVIEW_RESULTS", "review-results")
    KAFKA_CONSUMER_GROUP: str = "metrics-service-group"
    
    # Metrics Settings
    AGGREGATION_INTERVAL_SECONDS: int = 300  # 5 minutes
    CACHE_TTL_SECONDS: int = 60  # Cache results for 1 minute
    
    class Config:
        case_sensitive = True


settings = Settings()
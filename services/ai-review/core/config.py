"""
AI Review Service Configuration and Groq Client
"""

# =====================================================
# core/config.py - FIXED VERSION
# =====================================================

import os
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class Settings:
    """AI Review Service Configuration"""
    
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
        self.KAFKA_TOPIC_CODE_UPLOADS = os.getenv(
            "KAFKA_TOPIC_CODE_UPLOADS",
            "code-uploads"
        )
        self.KAFKA_TOPIC_REVIEW_RESULTS = os.getenv(
            "KAFKA_TOPIC_REVIEW_RESULTS",
            "review-results"
        )
        
        # Groq Configuration - ADD DEBUGGING
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.GROQ_KEY_NAME = os.getenv("GROQ_KEY_NAME", "")
        self.GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        self.GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "4000"))  # Fixed to 4000
        self.GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.1"))
        
        # Processing Configuration
        self.AI_REVIEW_TIMEOUT_SECONDS = int(os.getenv("AI_REVIEW_TIMEOUT_SECONDS", "60"))
        self.MAX_FILE_SIZE_FOR_REVIEW = int(os.getenv("MAX_FILE_SIZE_FOR_REVIEW", "50000"))
        self.MAX_FILES_PER_BATCH = int(os.getenv("MAX_FILES_PER_BATCH", "10"))
        
        # Application Configuration
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Debug: Log what environment variables are loaded
        self._debug_environment()
        
        self._validate_settings()
    
    def _debug_environment(self):
        """Debug environment variables"""
        groq_key_debug = self.GROQ_API_KEY
        if groq_key_debug:
            # Show first and last few characters for security
            key_preview = f"{groq_key_debug[:10]}...{groq_key_debug[-10:]}" if len(groq_key_debug) > 20 else "***"
        else:
            key_preview = "NOT SET"
            
        logger.info(
            "Environment debug",
            groq_api_key_set=bool(self.GROQ_API_KEY),
            groq_key_preview=key_preview,
            groq_model=self.GROQ_MODEL,
            groq_max_tokens=self.GROQ_MAX_TOKENS,
            database_url_set=bool(self.DATABASE_URL),
            kafka_servers_set=bool(self.KAFKA_BOOTSTRAP_SERVERS)
        )
    
    def _validate_settings(self):
        """Validate configuration - WITH BETTER ERROR MESSAGES"""
        missing_vars = []
        
        if not self.GROQ_API_KEY:
            missing_vars.append("GROQ_API_KEY")
            # Check if it might be named differently
            all_env_vars = dict(os.environ)
            groq_vars = {k: v for k, v in all_env_vars.items() if 'GROQ' in k.upper()}
            logger.error("GROQ_API_KEY not found. Available Groq-related env vars:", groq_vars=groq_vars)
        
        if not self.DATABASE_URL:
            missing_vars.append("DATABASE_URL")
        
        if not self.KAFKA_BOOTSTRAP_SERVERS:
            missing_vars.append("KAFKA_BOOTSTRAP_SERVERS")
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(
            "AI Review Service configuration validated successfully",
            model=self.GROQ_MODEL,
            max_tokens=self.GROQ_MAX_TOKENS,
            temperature=self.GROQ_TEMPERATURE,
            environment=self.ENVIRONMENT,
            groq_key_name=self.GROQ_KEY_NAME
        )
    
    @staticmethod
    def get_current_time() -> datetime:
        """Get current UTC timestamp"""
        return datetime.utcnow()


settings = Settings()
"""
API Gateway Configuration
Environment-based settings management
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Service Configuration
    ENVIRONMENT: str = Field(default="development", description="Environment: development, production")
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    
    # Database Configuration
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:9092", description="Kafka bootstrap servers")
    KAFKA_TOPIC_CODE_UPLOADS: str = Field(default="code-uploads", description="Topic for code upload events")
    KAFKA_TOPIC_REVIEW_RESULTS: str = Field(default="review-results", description="Topic for review results")
    KAFKA_AUTO_OFFSET_RESET: str = Field(default="earliest", description="Kafka consumer offset reset")
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB: int = Field(default=5, description="Maximum file size in MB")
    ALLOWED_FILE_EXTENSIONS: str = Field(
        default=".py,.js,.java,.cpp,.c,.h,.jsx,.tsx,.ts,.go,.rs,.php,.rb",
        description="Comma-separated list of allowed file extensions"
    )
    UPLOAD_TIMEOUT_SECONDS: int = Field(default=30, description="Upload timeout in seconds")
    MAX_FILES_PER_REVIEW: int = Field(default=10, description="Maximum files per review session")
    UPLOAD_DIR: str = Field(default="/tmp/uploads", description="Directory for temporary file storage")
    
    # API Configuration
    API_TIMEOUT_SECONDS: int = Field(default=30, description="API request timeout")
    MAX_REQUEST_SIZE: int = Field(default=50, description="Maximum request size in MB")
    
    # Security Configuration
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="CORS allowed origins"
    )
    
    # Service Dependencies
    AI_REVIEW_SERVICE_URL: str = Field(default="http://ai-review:8000", description="AI Review service URL")
    METRICS_SERVICE_URL: str = Field(default="http://metrics:8000", description="Metrics service URL")
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Parse allowed file extensions into a list"""
        return [ext.strip() for ext in self.ALLOWED_FILE_EXTENSIONS.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size to bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def kafka_config(self) -> dict:
        """Kafka configuration dictionary"""
        return {
            'bootstrap_servers': self.KAFKA_BOOTSTRAP_SERVERS.split(','),
            'auto_offset_reset': self.KAFKA_AUTO_OFFSET_RESET,
            'enable_auto_commit': True,
            'group_id': 'api-gateway',
            'value_serializer': lambda x: x.encode('utf-8') if isinstance(x, str) else x,
        }
    
    def create_upload_dir(self):
        """Create upload directory if it doesn't exist"""
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Ensure upload directory exists
settings.create_upload_dir()
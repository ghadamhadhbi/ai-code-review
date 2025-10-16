
# =====================================================
# NOTIFICATION SERVICE
# services/notification/main.py
# =====================================================

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog
import uvicorn

from core.config import settings
from services.kafka_consumer import NotificationConsumer
from services.email_service import EmailService

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global services
kafka_consumer = None
email_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global kafka_consumer, email_service
    
    # Startup
    logger.info("Starting Notification Service", version="1.0.0")
    
    try:
        # Initialize email service
        email_service = EmailService()
        await email_service.test_connection()
        logger.info("Email service initialized")
        
        # Initialize Kafka consumer
        kafka_consumer = NotificationConsumer(email_service)
        
        # Start consumer in background
        consumer_task = asyncio.create_task(kafka_consumer.start())
        logger.info("Notification service started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Startup failed", error=str(e))
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Notification Service")
        
        if kafka_consumer:
            await kafka_consumer.stop()
        
        if email_service:
            await email_service.close()
        
        logger.info("Notification service stopped")


# Create FastAPI app
app = FastAPI(
    title="AI Code Review - Notification Service",
    description="Email notification service for review alerts",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ai-code-review-notification",
        "version": "1.0.0",
        "status": "running",
        "smtp_server": settings.SMTP_SERVER,
        "smtp_port": settings.SMTP_PORT,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test email service
        if email_service:
            await email_service.test_connection()
        
        return {
            "status": "healthy",
            "service": "notification-service",
            "version": "1.0.0",
            "email": "connected",
            "consumer": "running" if kafka_consumer and kafka_consumer.is_running else "stopped",
            "timestamp": settings.get_current_time(),
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": settings.get_current_time(),
        }


@app.get("/metrics")
async def get_metrics():
    """Get service metrics"""
    metrics = {}
    
    if kafka_consumer:
        metrics["consumer"] = {
            "messages_processed": kafka_consumer.messages_processed,
            "messages_failed": kafka_consumer.messages_failed,
            "uptime_seconds": kafka_consumer.get_uptime_seconds(),
        }
    
    if email_service:
        metrics["email"] = {
            "emails_sent": email_service.emails_sent,
            "emails_failed": email_service.emails_failed,
        }
    
    return metrics


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info" if settings.LOG_LEVEL == "INFO" else "debug"
    )

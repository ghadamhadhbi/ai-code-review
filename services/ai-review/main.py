"""
AI Review Service - Main Application - FIXED
FastAPI application for AI-powered code review processing
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from core.config import settings
from core.database import init_db_pool, close_db_pool
from services.kafka_consumer import start_kafka_consumer, stop_kafka_consumer, get_kafka_consumer
from services.kafka_producer import get_kafka_producer, close_kafka_producer
from api.routes import router as api_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler - startup and shutdown
    """
    # Startup
    logger.info("🚀 Starting AI Review Service")
    
    try:
        # Initialize database
        logger.info("Initializing database connection pool")
        await init_db_pool()
        logger.info("✅ Database pool initialized")
        
        # Test database connection
        from core.database import get_db_session
        async with get_db_session() as db:
            await db.fetchval("SELECT 1")
        logger.info("✅ Database connection verified")
        
        # Start Kafka consumer in background
        asyncio.create_task(start_kafka_consumer())
        logger.info("✅ Kafka consumer started in background")
        
        logger.info("🎉 AI Review Service startup complete")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start AI Review Service", error=str(e))
        raise
    
    finally:
        # Shutdown
        logger.info("🛑 Shutting down AI Review Service")
        
        try:
            # Stop Kafka consumer
            await stop_kafka_consumer()
            logger.info("✅ Kafka consumer stopped")
            
            # Close Kafka producer
            await close_kafka_producer()
            logger.info("✅ Kafka producer closed")
            
            # Close database
            await close_db_pool()
            logger.info("✅ Database pool closed")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e))
        
        logger.info("👋 AI Review Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AI Code Review Service",
    description="AI-powered code review processing service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Code Review Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    from core.database import get_db_session
    
    health_status = {
        "service": "ai-review",
        "status": "healthy",
        "components": {}
    }
    
    # Check database
    try:
        async with get_db_session() as db:
            await db.fetchval("SELECT 1")
        health_status["components"]["database"] = {
            "status": "healthy",
            "connected": True
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Kafka consumer
    try:
        consumer = get_kafka_consumer()
        consumer_health = consumer.health_check()
        health_status["components"]["kafka_consumer"] = consumer_health
        
        if not consumer_health.get("running"):
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["components"]["kafka_consumer"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Kafka producer
    try:
        producer = get_kafka_producer()
        health_status["components"]["kafka_producer"] = {
            "status": "healthy",
            "initialized": producer.producer is not None
        }
    except Exception as e:
        health_status["components"]["kafka_producer"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
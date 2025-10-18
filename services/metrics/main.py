"""
Metrics Service - Main FastAPI Application - COMPLETE FIXED VERSION
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import asyncio
import sys

from core.config import settings

# Configure logging FIRST
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

# NOW import modules that use database
from core.database import init_db_pool, close_db_pool, test_connection, is_db_available
from services.data_aggregator import aggregator
from services.kafka_consumer import start_kafka_consumer, stop_kafka_consumer
from api import dashboard, analytics

# Global task references
_consumer_task = None
_aggregator_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    global _consumer_task, _aggregator_task
    
    # ==================== STARTUP ====================
    logger.info("=" * 50)
    logger.info("🚀 METRICS SERVICE STARTING UP")
    logger.info("=" * 50)
    logger.info("Environment", env=settings.ENVIRONMENT)
    logger.info("Database URL", db_url=settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else "not configured")
    
    # Step 1: Initialize database pool
    logger.info("STEP 1: Initializing database connection pool...")
    try:
        db_initialized = await init_db_pool()
        
        if db_initialized:
            logger.info("✅ Database pool initialized successfully")
            
            # Test connection
            logger.info("Testing database connection...")
            connection_ok = await test_connection()
            if connection_ok:
                logger.info("✅ Database connection test PASSED")
            else:
                logger.error("❌ Database connection test FAILED")
        else:
            logger.error("❌ Database pool initialization FAILED - running in degraded mode")
            
    except Exception as e:
        logger.error(
            "❌ CRITICAL: Database initialization error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
    
    # Step 2: Start data aggregator
    logger.info("STEP 2: Starting data aggregator...")
    try:
        if is_db_available():
            _aggregator_task = asyncio.create_task(aggregator.start_background_processing())
            await asyncio.sleep(1)  # Give it time to start
            logger.info("✅ Data aggregator task created and running")
        else:
            logger.warning("⚠️  Skipping data aggregator - database not available")
    except Exception as e:
        logger.error("❌ Failed to start data aggregator", error=str(e), exc_info=True)
    
    # Step 3: Start Kafka consumer
    logger.info("STEP 3: Starting Kafka consumer...")
    try:
        _consumer_task = asyncio.create_task(start_kafka_consumer(aggregator))
        await asyncio.sleep(1)  # Give it time to start
        logger.info("✅ Kafka consumer task created and running")
    except Exception as e:
        logger.error("❌ Failed to start Kafka consumer", error=str(e), exc_info=True)
    
    logger.info("=" * 50)
    logger.info("✅ METRICS SERVICE STARTUP COMPLETE")
    logger.info("=" * 50)
    
    yield
    
    # ==================== SHUTDOWN ====================
    logger.info("=" * 50)
    logger.info("🛑 METRICS SERVICE SHUTTING DOWN")
    logger.info("=" * 50)
    
    # Stop aggregator
    try:
        if _aggregator_task and not _aggregator_task.done():
            logger.info("Stopping data aggregator...")
            await aggregator.stop()
            try:
                await asyncio.wait_for(_aggregator_task, timeout=5.0)
                logger.info("✅ Data aggregator stopped")
            except asyncio.TimeoutError:
                logger.warning("⚠️  Data aggregator timeout - cancelling")
                _aggregator_task.cancel()
    except Exception as e:
        logger.error("Error stopping aggregator", error=str(e))
    
    # Stop Kafka consumer
    try:
        if _consumer_task and not _consumer_task.done():
            logger.info("Stopping Kafka consumer...")
            await stop_kafka_consumer()
            try:
                await asyncio.wait_for(_consumer_task, timeout=5.0)
                logger.info("✅ Kafka consumer stopped")
            except asyncio.TimeoutError:
                logger.warning("⚠️  Kafka consumer timeout - cancelling")
                _consumer_task.cancel()
    except Exception as e:
        logger.error("Error stopping Kafka consumer", error=str(e))
    
    # Close database pool
    try:
        await close_db_pool()
        logger.info("✅ Database pool closed")
    except Exception as e:
        logger.error("Error closing database pool", error=str(e))
    
    logger.info("=" * 50)
    logger.info("✅ METRICS SERVICE SHUTDOWN COMPLETE")
    logger.info("=" * 50)


# Create FastAPI app
app = FastAPI(
    title="AI Code Review - Metrics Service",
    description="Analytics and metrics aggregation service",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_status = {
            "status": "healthy",
            "service": "metrics-service",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "components": {}
        }
        
        # Check database
        db_available = is_db_available()
        health_status["database_available"] = db_available
        
        if db_available:
            try:
                db_ok = await test_connection()
                health_status["components"]["database"] = "healthy" if db_ok else "unhealthy"
            except Exception as e:
                health_status["components"]["database"] = "unhealthy"
                logger.error("Database health check failed", error=str(e))
        else:
            health_status["components"]["database"] = "not_initialized"
        
        # Check aggregator
        global _aggregator_task
        if _aggregator_task and not _aggregator_task.done():
            health_status["components"]["aggregator"] = "running"
            health_status["aggregator_stats"] = aggregator.get_stats()
        else:
            health_status["components"]["aggregator"] = "not_running"
        
        # Check consumer
        global _consumer_task
        if _consumer_task and not _consumer_task.done():
            health_status["components"]["kafka_consumer"] = "running"
        else:
            health_status["components"]["kafka_consumer"] = "not_running"
        
        # Determine overall status
        if not db_available or health_status["components"].get("database") == "unhealthy":
            health_status["status"] = "degraded"
            health_status["warning"] = "Database not available - running in degraded mode"
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "metrics-service",
                "error": str(e)
            }
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Code Review - Metrics Service",
        "version": "1.0.0",
        "status": "running",
        "database_available": is_db_available(),
        "endpoints": {
            "health": "/health",
            "dashboard_stats": "/api/dashboard/stats",
            "issue_analytics": "/api/analytics/issues",
            "performance_analytics": "/api/analytics/performance",
            "quality_analytics": "/api/analytics/quality",
        }
    }


# Include routers
app.include_router(
    dashboard.router,
    prefix="/api/dashboard",
    tags=["Dashboard"]
)

app.include_router(
    analytics.router,
    prefix="/api/analytics",
    tags=["Analytics"]
)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
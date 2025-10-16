"""
Metrics Service - Dashboard Analytics and System Monitoring
"""

# =====================================================
# services/metrics/main.py
# =====================================================

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
import uvicorn

from core.config import settings
from core.database import init_db_pool, close_db_pool, test_connection
from api.dashboard import router as dashboard_router
from api.analytics import router as analytics_router
from services.kafka_consumer import MetricsConsumer
from services.data_aggregator import DataAggregator

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
data_aggregator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global kafka_consumer, data_aggregator
    
    # Startup
    logger.info("Starting Metrics Service", version="1.0.0")
    
    try:
        # Initialize database
        await init_db_pool()
        await test_connection()
        logger.info("Database connection established")
        
        # Initialize data aggregator
        data_aggregator = DataAggregator()
        
        # Initialize Kafka consumer for metrics events
        kafka_consumer = MetricsConsumer(data_aggregator)
        
        # Start background tasks
        consumer_task = asyncio.create_task(kafka_consumer.start())
        aggregator_task = asyncio.create_task(data_aggregator.start_background_processing())
        
        logger.info("Metrics service started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Startup failed", error=str(e))
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Metrics Service")
        
        if kafka_consumer:
            await kafka_consumer.stop()
        
        if data_aggregator:
            await data_aggregator.stop()
        
        await close_db_pool()
        logger.info("Metrics service stopped")


# Create FastAPI app
app = FastAPI(
    title="AI Code Review - Metrics Service",
    description="Analytics and dashboard data service",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ai-code-review-metrics",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "dashboard": "/api/v1/dashboard",
            "analytics": "/api/v1/analytics", 
            "health": "/health",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await test_connection()
        
        return {
            "status": "healthy",
            "service": "metrics-service",
            "version": "1.0.0",
            "database": "connected",
            "consumer": "running" if kafka_consumer and kafka_consumer.is_running else "stopped",
            "aggregator": "running" if data_aggregator and data_aggregator.is_running else "stopped",
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
async def get_service_metrics():
    """Get service-specific metrics"""
    metrics = {}
    
    if kafka_consumer:
        metrics["consumer"] = {
            "messages_processed": kafka_consumer.messages_processed,
            "messages_failed": kafka_consumer.messages_failed,
            "uptime_seconds": kafka_consumer.get_uptime_seconds(),
        }
    
    if data_aggregator:
        metrics["aggregator"] = {
            "aggregations_run": data_aggregator.aggregations_run,
            "last_aggregation": data_aggregator.last_aggregation_time,
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

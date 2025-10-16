# =====================================================
# services/metrics/main.py
# =====================================================

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from core.config import settings
from core.database import init_db_pool, close_db_pool, test_connection
from api.dashboard import router as dashboard_router
from api.analytics import router as analytics_router
from services.kafka_consumer import MetricsConsumer
from services.data_aggregator import DataAggregator

logger = structlog.get_logger(__name__)

kafka_consumer = None
data_aggregator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global kafka_consumer, data_aggregator
    
    logger.info("🚀 Starting Metrics Service")
    
    try:
        await init_db_pool()
        await test_connection()
        logger.info("✅ Database connected")
        
        data_aggregator = DataAggregator()
        kafka_consumer = MetricsConsumer(data_aggregator)
        
        asyncio.create_task(kafka_consumer.start())
        asyncio.create_task(data_aggregator.start_background_processing())
        
        logger.info("✅ Metrics service ready")
        yield
        
    except Exception as e:
        logger.error("❌ Startup failed", error=str(e))
        raise
    finally:
        logger.info("🛑 Shutting down")
        if kafka_consumer:
            await kafka_consumer.stop()
        if data_aggregator:
            await data_aggregator.stop()
        await close_db_pool()


app = FastAPI(
    title="AI Code Review - Metrics Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await test_connection()
        return {
            "status": "healthy",
            "service": "metrics-service",
            "database": "connected",
            "consumer": "running" if kafka_consumer else "stopped",
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


"""
API Gateway - Main FastAPI application - COMPLETE FIXED VERSION
Handles file uploads, review results, WebSocket, and dashboard APIs
Includes Kafka consumer integration for async processing
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import structlog
import time
import asyncio

from core.config import settings
from core.exceptions import ValidationError, ProcessingError
from api import upload, reviews, websocket
from services.kafka_producer import initialize_kafka_producer, shutdown_kafka_producer
from services.kafka_consumer import start_kafka_consumer, stop_kafka_consumer

# Configure structured logging
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

# Global reference for background tasks
_consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - startup and shutdown"""
    global _consumer_task
    
    # ==================== STARTUP ====================
    logger.info("API Gateway starting up", environment=settings.ENVIRONMENT)
    
    # Test database connection
    try:
        from core.database import test_connection
        await test_connection()
        logger.info("Database connection successful")
    except Exception as e:
        logger.warning("Database connection failed (non-critical)", error=str(e))
    
    # Initialize Kafka producer
    try:
        await initialize_kafka_producer()
        logger.info("Kafka producer initialized")
    except Exception as e:
        logger.warning("Kafka producer initialization failed (non-critical)", error=str(e))
    
    # Start Kafka consumer as background task
    try:
        logger.info("Starting Kafka consumer in background")
        # Create task to run consumer
        _consumer_task = asyncio.create_task(start_kafka_consumer())
        # Give it a moment to start
        await asyncio.sleep(0.5)
        logger.info("Kafka consumer background task created and started")
    except Exception as e:
        logger.error("Failed to start Kafka consumer", error=str(e))
        logger.warning("Continuing without Kafka consumer - reviews will not process")
    
    logger.info("API Gateway startup complete")
    
    yield
    
    # ==================== SHUTDOWN ====================
    logger.info("API Gateway shutting down")
    
    # Stop Kafka consumer
    try:
        if _consumer_task and not _consumer_task.done():
            logger.info("Stopping Kafka consumer")
            await stop_kafka_consumer()
            # Wait for task to complete with timeout
            await asyncio.wait_for(_consumer_task, timeout=5.0)
            logger.info("Kafka consumer stopped")
    except asyncio.TimeoutError:
        logger.warning("Kafka consumer shutdown timeout - cancelling task")
        if _consumer_task and not _consumer_task.done():
            _consumer_task.cancel()
    except Exception as e:
        logger.error("Error stopping Kafka consumer", error=str(e))
    
    # Shutdown Kafka producer
    try:
        await shutdown_kafka_producer()
        logger.info("Kafka producer shutdown complete")
    except Exception as e:
        logger.error("Error stopping Kafka producer", error=str(e))
    
    logger.info("API Gateway shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AI Code Review - API Gateway",
    description="File upload and results API for AI-powered code reviews",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan,
)


# ✅ CORS middleware with WebSocket support
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:3001",
        "http://localhost:8003",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:8003",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


# Add trusted host middleware for production security
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )


# ✅ Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing"""
    start_time = time.time()
    
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        client_ip=request.client.host if request.client else None,
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=round(process_time, 4),
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as exc:
        process_time = time.time() - start_time
        logger.error(
            "Request failed",
            method=request.method,
            path=request.url.path,
            process_time=round(process_time, 4),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise


# ✅ Exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle validation errors"""
    logger.warning(
        "Validation error",
        path=request.url.path,
        error=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=400,
        content={
            "error": "validation_error",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(ProcessingError)
async def processing_exception_handler(request: Request, exc: ProcessingError):
    """Handle processing errors"""
    logger.error(
        "Processing error",
        path=request.url.path,
        error=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "processing_error",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(
        "Unexpected error",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.ENVIRONMENT == "development" else None,
        },
    )


# ✅ Health endpoint BEFORE routers
@app.get("/health")
async def health_check():
    """
    Health check endpoint - Returns service status
    Must be defined BEFORE including routers
    """
    try:
        health_status = {
            "status": "healthy",
            "service": "api-gateway",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
        }
        
        components = {}
        
        # Check database
        try:
            from core.database import test_connection
            await test_connection()
            components["database"] = "healthy"
        except Exception as e:
            components["database"] = "unhealthy"
            logger.warning("Database health check failed", error=str(e))
        
        # Check Kafka producer
        try:
            from services.kafka_producer import get_kafka_producer
            producer = get_kafka_producer()
            health = await producer.health_check()
            components["kafka_producer"] = health.get("status", "unknown")
        except Exception as e:
            components["kafka_producer"] = "unhealthy"
            logger.warning("Kafka producer health check failed", error=str(e))
        
        # Check Kafka consumer status
        global _consumer_task
        if _consumer_task:
            components["kafka_consumer"] = "healthy" if not _consumer_task.done() else "stopped"
        else:
            components["kafka_consumer"] = "not_started"
        
        # Check AI Review Service
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.AI_REVIEW_SERVICE_URL}/health")
                if response.status_code == 200:
                    components["ai_review_service"] = "healthy"
                else:
                    components["ai_review_service"] = "degraded"
        except Exception as e:
            components["ai_review_service"] = "unhealthy"
            logger.warning("AI Review Service health check failed", error=str(e))
        
        health_status["components"] = components
        
        # Determine overall status
        unhealthy_components = [k for k, v in components.items() if v == "unhealthy"]
        if unhealthy_components:
            health_status["status"] = "degraded"
            health_status["unhealthy_components"] = unhealthy_components
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "api-gateway",
                "error": str(e),
            }
        )


# Root endpoint
@app.get("/")
async def root():
    """API Gateway root endpoint"""
    return {
        "service": "AI Code Review - API Gateway",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "health": "/health",
            "upload": "/api/upload",
            "reviews": "/api/reviews",
            "reviews_stats": "/api/reviews/stats",
            "websocket": "/api/reviews/ws/reviews",
            "docs": "/docs" if settings.ENVIRONMENT == "development" else None,
        },
        "kafka": {
            "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "topics": {
                "uploads": settings.KAFKA_TOPIC_CODE_UPLOADS,
                "results": settings.KAFKA_TOPIC_REVIEW_RESULTS,
            }
        }
    }


# ✅ Include routers AFTER health endpoint (specific routes first)
app.include_router(
    upload.router,
    prefix="/api/upload",
    tags=["Upload"]
)

app.include_router(
    reviews.router,
    prefix="/api/reviews",
    tags=["Reviews"]
)

app.include_router(
    websocket.router,
    prefix="/api/reviews",
    tags=["WebSocket"]
)


# Additional utility endpoints
@app.get("/api/info")
async def get_api_info():
    """Get API information and configuration"""
    return {
        "api_version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "max_files_per_review": settings.MAX_FILES_PER_REVIEW,
        "allowed_extensions": settings.ALLOWED_FILE_EXTENSIONS,
        "upload_timeout_seconds": settings.UPLOAD_TIMEOUT_SECONDS,
    }


@app.get("/api/status")
async def get_system_status():
    """Get system status and metrics"""
    try:
        status_info = {
            "timestamp": time.time(),
            "uptime": "N/A",
            "services": {},
            "kafka_consumer_running": False
        }
        
        # Check consumer task
        global _consumer_task
        if _consumer_task and not _consumer_task.done():
            status_info["kafka_consumer_running"] = True
            status_info["kafka_consumer_status"] = "running"
        else:
            status_info["kafka_consumer_status"] = "stopped"
        
        # Check AI Review Service
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.AI_REVIEW_SERVICE_URL}/health")
                status_info["services"]["ai_review"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "url": settings.AI_REVIEW_SERVICE_URL,
                }
        except Exception as e:
            status_info["services"]["ai_review"] = {
                "status": "unhealthy",
                "error": str(e),
            }
        
        return status_info
        
    except Exception as e:
        logger.error("Failed to get system status", error=str(e))
        raise


# ✅ 404 Handler
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": f"The requested path '{request.url.path}' was not found",
            "available_endpoints": {
                "health": "/health",
                "root": "/",
                "api_info": "/api/info",
                "api_status": "/api/status",
                "upload": "/api/upload",
                "reviews": "/api/reviews",
                "websocket": "/api/reviews/ws/reviews",
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
        access_log=False,
        ws_ping_interval=20,
        ws_ping_timeout=20,
    )
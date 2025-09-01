"""
API Gateway - Main FastAPI application
Handles file uploads, review results, and dashboard APIs
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

from core.config import settings
from core.exceptions import ValidationError, ProcessingError
from api import upload, reviews, metrics, health

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

# Create FastAPI app
app = FastAPI(
    title="AI Code Review - API Gateway",
    description="File upload and results API for AI-powered code reviews",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev server
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )


# Request/Response middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        client_ip=request.client.host if request.client else None,
    )
    
    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=round(process_time, 4),
        )
        
        # Add timing header
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
        )
        raise


# Exception handlers
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
        },
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["Reviews"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])


# Root endpoint
@app.get("/")
async def root():
    """API Gateway root endpoint"""
    return {
        "service": "AI Code Review - API Gateway",
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "upload": "/api/upload",
            "reviews": "/api/reviews", 
            "metrics": "/api/metrics",
            "health": "/health",
            "docs": "/docs" if settings.ENVIRONMENT == "development" else None,
        },
    }


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("API Gateway starting up", environment=settings.ENVIRONMENT)
    
    # Test database connection
    try:
        from core.database import test_connection
        await test_connection()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        raise
    
    # Test Kafka connection
    try:
        from core.kafka_producer import test_connection
        await test_connection()
        logger.info("Kafka connection successful")
    except Exception as e:
        logger.error("Kafka connection failed", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("API Gateway shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
    )
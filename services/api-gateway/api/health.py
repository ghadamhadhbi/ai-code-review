"""
Health check endpoints
Service status and dependency checks
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from core.config import settings
from core.database import test_connection as test_db
from services.kafka_producer import test_connection as test_kafka

logger = structlog.get_logger(__name__)
router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model"""
    service: str
    status: str
    timestamp: datetime
    version: str
    environment: str
    dependencies: Dict[str, Any]


class ServiceDependency(BaseModel):
    """Individual service dependency status"""
    name: str
    status: str
    response_time_ms: Optional[float]
    error: Optional[str]


@router.get("/", response_model=HealthStatus)
async def health_check():
    """
    Complete health check including all dependencies
    
    Returns overall service health and dependency status
    """
    start_time = asyncio.get_event_loop().time()
    
    logger.info("Health check started")
    
    # Check all dependencies
    dependencies = {}
    overall_healthy = True
    
    # Database check
    db_start = asyncio.get_event_loop().time()
    try:
        await test_db()
        db_time = (asyncio.get_event_loop().time() - db_start) * 1000
        dependencies["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_time, 2),
            "error": None
        }
        logger.debug("Database health check passed", response_time_ms=round(db_time, 2))
        
    except Exception as e:
        db_time = (asyncio.get_event_loop().time() - db_start) * 1000
        dependencies["database"] = {
            "status": "unhealthy",
            "response_time_ms": round(db_time, 2),
            "error": str(e)
        }
        overall_healthy = False
        logger.error("Database health check failed", error=str(e))
    
    # Kafka check
    kafka_start = asyncio.get_event_loop().time()
    try:
        await test_kafka()
        kafka_time = (asyncio.get_event_loop().time() - kafka_start) * 1000
        dependencies["kafka"] = {
            "status": "healthy",
            "response_time_ms": round(kafka_time, 2),
            "error": None
        }
        logger.debug("Kafka health check passed", response_time_ms=round(kafka_time, 2))
        
    except Exception as e:
        kafka_time = (asyncio.get_event_loop().time() - kafka_start) * 1000
        dependencies["kafka"] = {
            "status": "unhealthy",
            "response_time_ms": round(kafka_time, 2),
            "error": str(e)
        }
        overall_healthy = False
        logger.error("Kafka health check failed", error=str(e))
    
    # File system check
    fs_start = asyncio.get_event_loop().time()
    try:
        import os
        # Check if upload directory is writable
        test_file = os.path.join(settings.UPLOAD_DIR, '.health_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        
        fs_time = (asyncio.get_event_loop().time() - fs_start) * 1000
        dependencies["filesystem"] = {
            "status": "healthy",
            "response_time_ms": round(fs_time, 2),
            "error": None,
            "upload_dir": settings.UPLOAD_DIR
        }
        logger.debug("Filesystem health check passed")
        
    except Exception as e:
        fs_time = (asyncio.get_event_loop().time() - fs_start) * 1000
        dependencies["filesystem"] = {
            "status": "unhealthy",
            "response_time_ms": round(fs_time, 2),
            "error": str(e),
            "upload_dir": settings.UPLOAD_DIR
        }
        overall_healthy = False
        logger.error("Filesystem health check failed", error=str(e))
    
    total_time = (asyncio.get_event_loop().time() - start_time) * 1000
    
    status = "healthy" if overall_healthy else "unhealthy"
    
    logger.info(
        "Health check completed",
        status=status,
        total_time_ms=round(total_time, 2),
        dependencies_checked=len(dependencies)
    )
    
    return HealthStatus(
        service="AI Code Review - API Gateway",
        status=status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        dependencies=dependencies
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint
    
    Returns 200 if service is ready to accept traffic
    """
    try:
        # Quick checks for critical dependencies
        await test_db()
        await test_kafka()
        
        return {"status": "ready", "timestamp": datetime.utcnow()}
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint
    
    Returns 200 if service is alive (basic functionality)
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow(),
        "service": "api-gateway"
    }


@router.get("/metrics")
async def health_metrics():
    """
    Basic service metrics for monitoring
    
    Returns key operational metrics
    """
    try:
        import psutil
        import os
        
        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process metrics
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        return {
            "timestamp": datetime.utcnow(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available // (1024*1024),
                "disk_percent": (disk.used / disk.total) * 100,
                "disk_free_gb": disk.free // (1024*1024*1024),
            },
            "process": {
                "memory_rss_mb": process_memory.rss // (1024*1024),
                "memory_vms_mb": process_memory.vms // (1024*1024),
                "num_threads": process.num_threads(),
                "cpu_percent": process.cpu_percent(),
            },
            "upload_dir": {
                "path": settings.UPLOAD_DIR,
                "exists": os.path.exists(settings.UPLOAD_DIR),
                "writable": os.access(settings.UPLOAD_DIR, os.W_OK),
            }
        }
        
    except ImportError:
        # psutil not available, return basic info
        return {
            "timestamp": datetime.utcnow(),
            "message": "Detailed metrics not available (psutil not installed)",
            "basic_info": {
                "environment": settings.ENVIRONMENT,
                "upload_dir": settings.UPLOAD_DIR,
            }
        }
    except Exception as e:
        logger.error("Failed to get health metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")
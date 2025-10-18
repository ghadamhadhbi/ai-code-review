"""
API Gateway - Analytics API endpoints (proxy to metrics service)
Forwards dashboard and analytics requests to the metrics service
FIXED VERSION - Removes duplicate /analytics in paths
"""

from fastapi import APIRouter, Query, HTTPException
import httpx
import structlog

from core.config import settings

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/stats")
async def get_dashboard_stats(days: int = Query(7, ge=1, le=90)):
    """
    Get dashboard statistics (proxied to metrics service)
    
    Args:
        days: Number of days to analyze (1-90)
    """
    try:
        logger.info("Forwarding stats request to metrics service", days=days)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.METRICS_SERVICE_URL}/api/dashboard/stats",
                params={"days": days}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Metrics service error",
                    status_code=response.status_code,
                    response=response.text
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to fetch stats from metrics service"
                )
                
    except httpx.TimeoutException:
        logger.error("Timeout connecting to metrics service")
        raise HTTPException(status_code=504, detail="Metrics service timeout")
    except httpx.ConnectError:
        logger.error("Cannot connect to metrics service")
        raise HTTPException(status_code=503, detail="Metrics service unavailable")
    except Exception as e:
        logger.error("Error fetching stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/issues")
async def get_issue_analytics(days: int = Query(30, ge=1, le=90)):
    """
    Get issue analytics (proxied to metrics service)
    
    Args:
        days: Number of days to analyze (1-90)
    """
    try:
        logger.info("Forwarding issue analytics request to metrics service", days=days)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.METRICS_SERVICE_URL}/api/analytics/issues",
                params={"days": days}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Metrics service error",
                    status_code=response.status_code,
                    response=response.text
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to fetch issue analytics from metrics service"
                )
                
    except httpx.TimeoutException:
        logger.error("Timeout connecting to metrics service")
        raise HTTPException(status_code=504, detail="Metrics service timeout")
    except httpx.ConnectError:
        logger.error("Cannot connect to metrics service")
        raise HTTPException(status_code=503, detail="Metrics service unavailable")
    except Exception as e:
        logger.error("Error fetching issue analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_analytics(hours: int = Query(24, ge=1, le=168)):
    """
    Get performance analytics (proxied to metrics service)
    
    Args:
        hours: Number of hours to analyze (1-168)
    """
    try:
        logger.info("Forwarding performance analytics request to metrics service", hours=hours)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.METRICS_SERVICE_URL}/api/analytics/performance",
                params={"hours": hours}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Metrics service error",
                    status_code=response.status_code,
                    response=response.text
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to fetch performance analytics from metrics service"
                )
                
    except httpx.TimeoutException:
        logger.error("Timeout connecting to metrics service")
        raise HTTPException(status_code=504, detail="Metrics service timeout")
    except httpx.ConnectError:
        logger.error("Cannot connect to metrics service")
        raise HTTPException(status_code=503, detail="Metrics service unavailable")
    except Exception as e:
        logger.error("Error fetching performance analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality")
async def get_quality_analytics(days: int = Query(30, ge=1, le=90)):
    """
    Get quality analytics (proxied to metrics service)
    
    Args:
        days: Number of days to analyze (1-90)
    """
    try:
        logger.info("Forwarding quality analytics request to metrics service", days=days)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.METRICS_SERVICE_URL}/api/analytics/quality",
                params={"days": days}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Metrics service error",
                    status_code=response.status_code,
                    response=response.text
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to fetch quality analytics from metrics service"
                )
                
    except httpx.TimeoutException:
        logger.error("Timeout connecting to metrics service")
        raise HTTPException(status_code=504, detail="Metrics service timeout")
    except httpx.ConnectError:
        logger.error("Cannot connect to metrics service")
        raise HTTPException(status_code=503, detail="Metrics service unavailable")
    except Exception as e:
        logger.error("Error fetching quality analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
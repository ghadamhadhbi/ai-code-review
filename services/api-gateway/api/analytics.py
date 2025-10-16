# =====================================================
# services/api-gateway/api/analytics.py (COMPLETE FILE)
# =====================================================

from fastapi import APIRouter, Query, HTTPException
import httpx
import structlog
import os

router = APIRouter()
logger = structlog.get_logger(__name__)

METRICS_SERVICE_URL = os.getenv("METRICS_SERVICE_URL", "http://metrics:8000")


async def call_metrics_service(endpoint: str, params: dict = None):
    """Helper function to call metrics service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{METRICS_SERVICE_URL}{endpoint}",
                params=params or {}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    "Metrics service non-200 response",
                    endpoint=endpoint,
                    status=response.status_code
                )
                return None
                
    except httpx.TimeoutException:
        logger.warning("Metrics service timeout", endpoint=endpoint)
        return None
    except Exception as e:
        logger.error("Error calling metrics service", endpoint=endpoint, error=str(e))
        return None


@router.get("/issues")
async def get_issue_analytics(days: int = Query(30, ge=1, le=90)):
    """Get issue analytics from metrics service"""
    result = await call_metrics_service("/api/analytics/issues", {"days": days})
    
    if result:
        return result
    
    # Return empty data on error
    return {
        "issue_types": [],
        "severity_trends": [],
        "common_issues": []
    }


@router.get("/performance")
async def get_performance_analytics(hours: int = Query(24, ge=1, le=168)):
    """Get performance analytics from metrics service"""
    result = await call_metrics_service("/api/analytics/performance", {"hours": hours})
    
    if result:
        return result
    
    return {
        "hourly_performance": [],
        "token_usage": []
    }


@router.get("/quality")
async def get_quality_analytics(days: int = Query(30, ge=1, le=90)):
    """Get quality analytics from metrics service"""
    result = await call_metrics_service("/api/analytics/quality", {"days": days})
    
    if result:
        return result
    
    return {
        "quality_distribution": [],
        "language_quality": []
    }

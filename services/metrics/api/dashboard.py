"""
Metrics Service - Dashboard API and Analytics Endpoints
"""

# =====================================================
# services/metrics/api/dashboard.py
# =====================================================

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime, timedelta

from core.database import (
    get_db_session, get_dashboard_overview, 
    get_daily_activity, get_language_distribution
)

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview_endpoint(
    days: int = Query(default=7, le=90, description="Number of days for overview")
):
    """Get dashboard overview metrics"""
    try:
        logger.info("Fetching dashboard overview", days=days)
        
        overview = await get_dashboard_overview(days)
        
        return {
            "period": {
                "days": days,
                "start_date": (datetime.utcnow() - timedelta(days=days)).isoformat(),
                "end_date": datetime.utcnow().isoformat(),
            },
            "metrics": overview
        }
        
    except Exception as e:
        logger.error("Failed to fetch dashboard overview", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard overview")


@router.get("/activity")
async def get_daily_activity_endpoint(
    days: int = Query(default=30, le=90, description="Number of days for activity data")
):
    """Get daily activity trends"""
    try:
        logger.info("Fetching daily activity", days=days)
        
        activity = await get_daily_activity(days)
        
        return {
            "period": {
                "days": days,
                "data_points": len(activity)
            },
            "activity": activity
        }
        
    except Exception as e:
        logger.error("Failed to fetch daily activity", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve activity data")


@router.get("/languages")
async def get_language_distribution_endpoint(
    days: int = Query(default=30, le=90, description="Number of days for language data")
):
    """Get programming language distribution"""
    try:
        logger.info("Fetching language distribution", days=days)
        
        languages = await get_language_distribution(days)
        
        return {
            "period": {
                "days": days,
                "languages_count": len(languages)
            },
            "languages": languages
        }
        
    except Exception as e:
        logger.error("Failed to fetch language distribution", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve language data")


@router.get("/health-status")
async def get_system_health():
    """Get current system health metrics"""
    try:
        async with get_db_session() as db:
            # Recent activity (last hour)
            recent_activity = await db.fetchrow("""
                SELECT 
                    COUNT(*) as reviews_last_hour,
                    COUNT(*) FILTER (WHERE status = 'failed') as failures_last_hour
                FROM review_results
                WHERE created_at >= NOW() - INTERVAL '1 hour'
            """)
            
            # Queue status
            queue_status = await db.fetchrow("""
                SELECT 
                    COUNT(*) as pending_reviews,
                    MIN(created_at) as oldest_pending
                FROM review_results
                WHERE status = 'pending'
            """)
            
            # Error rate (last 24 hours)
            error_metrics = await db.fetchrow("""
                SELECT 
                    COUNT(*) as total_attempts,
                    COUNT(*) FILTER (WHERE status = 'failed') as failures
                FROM review_results
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """)
            
            # Performance metrics
            performance = await db.fetchrow("""
                SELECT 
                    AVG(processing_time_ms) as avg_time,
                    MAX(processing_time_ms) as max_time,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_time
                FROM review_results
                WHERE created_at >= NOW() - INTERVAL '24 hours' 
                AND processing_time_ms > 0
            """)
            
            # Calculate health indicators
            error_rate = 0
            if error_metrics["total_attempts"] and error_metrics["total_attempts"] > 0:
                error_rate = (error_metrics["failures"] or 0) / error_metrics["total_attempts"] * 100
            
            pending_count = queue_status["pending_reviews"] or 0
            queue_health = "healthy"
            if pending_count > 50:
                queue_health = "degraded"
            elif pending_count > 100:
                queue_health = "unhealthy"
            
            avg_time = performance["avg_time"] or 0
            performance_health = "healthy"
            if avg_time > 30000:  # 30 seconds
                performance_health = "degraded"
            elif avg_time > 60000:  # 1 minute
                performance_health = "unhealthy"
            
            # Overall health
            overall_health = "healthy"
            if error_rate > 10 or queue_health == "unhealthy" or performance_health == "unhealthy":
                overall_health = "unhealthy"
            elif error_rate > 5 or queue_health == "degraded" or performance_health == "degraded":
                overall_health = "degraded"
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_health": overall_health,
                "activity": {
                    "reviews_last_hour": recent_activity["reviews_last_hour"] or 0,
                    "failures_last_hour": recent_activity["failures_last_hour"] or 0,
                },
                "queue": {
                    "pending_reviews": pending_count,
                    "oldest_pending": queue_status["oldest_pending"].isoformat() if queue_status["oldest_pending"] else None,
                    "health": queue_health,
                },
                "errors": {
                    "error_rate_24h": round(error_rate, 2),
                    "total_attempts_24h": error_metrics["total_attempts"] or 0,
                    "failures_24h": error_metrics["failures"] or 0,
                },
                "performance": {
                    "avg_processing_time_ms": round(float(avg_time), 1),
                    "max_processing_time_ms": performance["max_time"] or 0,
                    "p95_processing_time_ms": round(float(performance["p95_time"] or 0), 1),
                    "health": performance_health,
                },
            }
        
    except Exception as e:
        logger.error("Failed to fetch system health", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")


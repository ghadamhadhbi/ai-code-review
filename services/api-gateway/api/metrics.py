"""
Metrics and analytics API endpoints
Dashboard data and system metrics
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime, timedelta

from core.config import settings
from core.database import get_db_session

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_metrics(
    days: int = Query(default=7, le=90, description="Number of days for metrics"),
    db_session = Depends(get_db_session)
):
    """
    Get dashboard metrics for the specified time period
    
    - **days**: Number of days to include (max 90)
    
    Returns comprehensive dashboard metrics
    """
    try:
        logger.info("Fetching dashboard metrics", days=days)
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Overall system metrics
        overview_query = """
            SELECT 
                COUNT(DISTINCT r.id) as total_reviews,
                COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'completed') as completed_reviews,
                COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'failed') as failed_reviews,
                COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'pending') as pending_reviews,
                AVG(r.overall_score) FILTER (WHERE r.overall_score IS NOT NULL) as avg_score,
                COUNT(DISTINCT s.id) as total_suggestions,
                COUNT(DISTINCT s.id) FILTER (WHERE s.severity = 'critical') as critical_issues,
                COUNT(DISTINCT s.id) FILTER (WHERE s.severity = 'high') as high_issues,
                SUM(r.tokens_used) as total_tokens,
                AVG(r.processing_time_ms) as avg_processing_time
            FROM review_results r
            LEFT JOIN review_suggestions s ON s.review_result_id = r.id
            WHERE r.created_at >= $1
        """
        
        overview = await db_session.fetchrow(overview_query, since_date)
        
        # Daily activity trend
        daily_query = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as reviews,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                AVG(overall_score) FILTER (WHERE overall_score IS NOT NULL) as avg_score
            FROM review_results
            WHERE created_at >= $1
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """
        
        daily_rows = await db_session.fetch(daily_query, since_date)
        
        # Language distribution
        language_query = """
            SELECT 
                COALESCE(u.language, 'unknown') as language,
                COUNT(*) as count,
                AVG(r.overall_score) FILTER (WHERE r.overall_score IS NOT NULL) as avg_score
            FROM review_results r
            LEFT JOIN uploads u ON r.upload_id = u.id
            WHERE r.created_at >= $1
            GROUP BY COALESCE(u.language, 'unknown')
            ORDER BY count DESC
        """
        
        language_rows = await db_session.fetch(language_query, since_date)
        
        # Top issues by type
        issues_query = """
            SELECT 
                suggestion_type,
                severity,
                COUNT(*) as count,
                AVG(confidence_score) as avg_confidence
            FROM review_suggestions s
            JOIN review_results r ON s.review_result_id = r.id
            WHERE r.created_at >= $1
            GROUP BY suggestion_type, severity
            ORDER BY count DESC
            LIMIT 20
        """
        
        issues_rows = await db_session.fetch(issues_query, since_date)
        
        # Performance metrics
        performance_query = """
            SELECT 
                DATE(created_at) as date,
                AVG(processing_time_ms) as avg_time,
                MIN(processing_time_ms) as min_time,
                MAX(processing_time_ms) as max_time,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_time
            FROM review_results
            WHERE created_at >= $1 AND processing_time_ms > 0
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """
        
        performance_rows = await db_session.fetch(performance_query, since_date)
        
        return {
            "period": {
                "days": days,
                "start_date": since_date,
                "end_date": datetime.utcnow(),
            },
            "overview": {
                "total_reviews": overview["total_reviews"] or 0,
                "completed_reviews": overview["completed_reviews"] or 0,
                "failed_reviews": overview["failed_reviews"] or 0,
                "pending_reviews": overview["pending_reviews"] or 0,
                "success_rate": round(
                    (overview["completed_reviews"] or 0) / max(overview["total_reviews"] or 1, 1) * 100, 1
                ),
                "average_score": round(float(overview["avg_score"] or 0), 1),
                "total_suggestions": overview["total_suggestions"] or 0,
                "critical_issues": overview["critical_issues"] or 0,
                "high_issues": overview["high_issues"] or 0,
                "total_tokens_used": overview["total_tokens"] or 0,
                "avg_processing_time_ms": round(float(overview["avg_processing_time"] or 0), 1),
            },
            "daily_activity": [
                {
                    "date": row["date"].isoformat(),
                    "reviews": row["reviews"],
                    "completed": row["completed"],
                    "avg_score": round(float(row["avg_score"] or 0), 1),
                }
                for row in daily_rows
            ],
            "language_distribution": [
                {
                    "language": row["language"],
                    "count": row["count"],
                    "avg_score": round(float(row["avg_score"] or 0), 1),
                }
                for row in language_rows
            ],
            "top_issues": [
                {
                    "type": row["suggestion_type"],
                    "severity": row["severity"],
                    "count": row["count"],
                    "avg_confidence": round(float(row["avg_confidence"] or 0), 1),
                }
                for row in issues_rows
            ],
            "performance_trends": [
                {
                    "date": row["date"].isoformat(),
                    "avg_time_ms": round(float(row["avg_time"] or 0), 1),
                    "min_time_ms": row["min_time"] or 0,
                    "max_time_ms": row["max_time"] or 0,
                    "p95_time_ms": round(float(row["p95_time"] or 0), 1),
                }
                for row in performance_rows
            ],
        }
        
    except Exception as e:
        logger.error("Failed to fetch dashboard metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard metrics")


@router.get("/health")
async def get_system_health_metrics(
    db_session = Depends(get_db_session)
):
    """
    Get system health and operational metrics
    
    Returns current system status and health indicators
    """
    try:
        logger.info("Fetching system health metrics")
        
        # Recent activity (last hour)
        recent_activity_query = """
            SELECT 
                COUNT(*) as reviews_last_hour,
                COUNT(*) FILTER (WHERE status = 'failed') as failures_last_hour
            FROM review_results
            WHERE created_at >= NOW() - INTERVAL '1 hour'
        """
        
        activity = await db_session.fetchrow(recent_activity_query)
        
        # Queue status (pending reviews)
        queue_query = """
            SELECT 
                COUNT(*) as pending_reviews,
                MIN(created_at) as oldest_pending
            FROM review_results
            WHERE status = 'pending'
        """
        
        queue = await db_session.fetchrow(queue_query)
        
        # Error rate (last 24 hours)
        error_query = """
            SELECT 
                COUNT(*) as total_attempts,
                COUNT(*) FILTER (WHERE status = 'failed') as failures
            FROM review_results
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """
        
        errors = await db_session.fetchrow(error_query)
        
        # Processing time trends (last 24 hours)
        timing_query = """
            SELECT 
                AVG(processing_time_ms) as avg_time,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_time,
                MAX(processing_time_ms) as max_time
            FROM review_results
            WHERE created_at >= NOW() - INTERVAL '24 hours' 
            AND processing_time_ms > 0
        """
        
        timing = await db_session.fetchrow(timing_query)
        
        # Calculate health indicators
        error_rate = 0
        if errors["total_attempts"] and errors["total_attempts"] > 0:
            error_rate = (errors["failures"] or 0) / errors["total_attempts"] * 100
        
        queue_health = "healthy"
        pending_count = queue["pending_reviews"] or 0
        if pending_count > 50:
            queue_health = "degraded"
        elif pending_count > 100:
            queue_health = "unhealthy"
        
        performance_health = "healthy"
        avg_time = timing["avg_time"] or 0
        if avg_time > 30000:  # 30 seconds
            performance_health = "degraded"
        elif avg_time > 60000:  # 1 minute
            performance_health = "unhealthy"
        
        # Overall system health
        overall_health = "healthy"
        if error_rate > 10 or queue_health == "unhealthy" or performance_health == "unhealthy":
            overall_health = "unhealthy"
        elif error_rate > 5 or queue_health == "degraded" or performance_health == "degraded":
            overall_health = "degraded"
        
        return {
            "timestamp": datetime.utcnow(),
            "overall_health": overall_health,
            "activity": {
                "reviews_last_hour": activity["reviews_last_hour"] or 0,
                "failures_last_hour": activity["failures_last_hour"] or 0,
            },
            "queue": {
                "pending_reviews": pending_count,
                "oldest_pending": queue["oldest_pending"],
                "health": queue_health,
            },
            "error_metrics": {
                "error_rate_24h": round(error_rate, 2),
                "total_attempts_24h": errors["total_attempts"] or 0,
                "failures_24h": errors["failures"] or 0,
            },
            "performance": {
                "avg_processing_time_ms": round(float(avg_time), 1),
                "p95_processing_time_ms": round(float(timing["p95_time"] or 0), 1),
                "max_processing_time_ms": timing["max_time"] or 0,
                "health": performance_health,
            },
        }
        
    except Exception as e:
        logger.error("Failed to fetch system health metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve system health metrics")


@router.get("/usage/tokens")
async def get_token_usage(
    days: int = Query(default=30, le=90, description="Number of days for token usage"),
    db_session = Depends(get_db_session)
):
    """
    Get AI token usage statistics
    
    - **days**: Number of days to include (max 90)
    
    Returns token usage trends and costs
    """
    try:
        logger.info("Fetching token usage metrics", days=days)
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Daily token usage
        daily_usage_query = """
            SELECT 
                DATE(created_at) as date,
                SUM(tokens_used) as tokens_used,
                COUNT(*) as review_count,
                AVG(tokens_used) as avg_tokens_per_review
            FROM review_results
            WHERE created_at >= $1 AND tokens_used > 0
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """
        
        daily_rows = await db_session.fetch(daily_usage_query, since_date)
        
        # Model usage distribution
        model_usage_query = """
            SELECT 
                model_used,
                COUNT(*) as usage_count,
                SUM(tokens_used) as total_tokens,
                AVG(tokens_used) as avg_tokens
            FROM review_results
            WHERE created_at >= $1 AND tokens_used > 0
            GROUP BY model_used
            ORDER BY total_tokens DESC
        """
        
        model_rows = await db_session.fetch(model_usage_query, since_date)
        
        # Total usage summary
        total_tokens = sum(row["tokens_used"] for row in daily_rows)
        total_reviews = sum(row["review_count"] for row in daily_rows)
        
        # Estimated costs (approximate based on OpenAI pricing)
        estimated_cost = total_tokens * 0.00002  # $0.02 per 1K tokens (rough estimate)
        
        return {
            "period": {
                "days": days,
                "start_date": since_date,
                "end_date": datetime.utcnow(),
            },
            "summary": {
                "total_tokens_used": total_tokens,
                "total_reviews": total_reviews,
                "avg_tokens_per_review": round(total_tokens / max(total_reviews, 1), 1),
                "estimated_cost_usd": round(estimated_cost, 4),
            },
            "daily_usage": [
                {
                    "date": row["date"].isoformat(),
                    "tokens_used": row["tokens_used"],
                    "review_count": row["review_count"],
                    "avg_tokens_per_review": round(float(row["avg_tokens_per_review"] or 0), 1),
                }
                for row in daily_rows
            ],
            "model_distribution": [
                {
                    "model": row["model_used"],
                    "usage_count": row["usage_count"],
                    "total_tokens": row["total_tokens"],
                    "avg_tokens": round(float(row["avg_tokens"] or 0), 1),
                    "percentage": round(row["total_tokens"] / max(total_tokens, 1) * 100, 1),
                }
                for row in model_rows
            ],
        }
        
    except Exception as e:
        logger.error("Failed to fetch token usage metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve token usage metrics")


@router.get("/performance")
async def get_performance_metrics(
    hours: int = Query(default=24, le=168, description="Number of hours for performance data"),
    db_session = Depends(get_db_session)
):
    """
    Get detailed performance metrics
    
    - **hours**: Number of hours to include (max 168 = 1 week)
    
    Returns performance trends and bottleneck analysis
    """
    try:
        logger.info("Fetching performance metrics", hours=hours)
        
        since_date = datetime.utcnow() - timedelta(hours=hours)
        
        # Hourly performance trends
        hourly_query = """
            SELECT 
                DATE_TRUNC('hour', created_at) as hour,
                COUNT(*) as review_count,
                AVG(processing_time_ms) as avg_time,
                MIN(processing_time_ms) as min_time,
                MAX(processing_time_ms) as max_time,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY processing_time_ms) as median_time,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_time
            FROM review_results
            WHERE created_at >= $1 AND processing_time_ms > 0
            GROUP BY DATE_TRUNC('hour', created_at)
            ORDER BY hour DESC
        """
        
        hourly_rows = await db_session.fetch(hourly_query, since_date)
        
        # Slowest reviews
        slow_reviews_query = """
            SELECT 
                id, processing_time_ms, tokens_used, model_used, created_at,
                (SELECT COUNT(*) FROM review_suggestions WHERE review_result_id = r.id) as suggestion_count
            FROM review_results r
            WHERE created_at >= $1 AND processing_time_ms > 0
            ORDER BY processing_time_ms DESC
            LIMIT 10
        """
        
        slow_rows = await db_session.fetch(slow_reviews_query, since_date)
        
        # Throughput analysis
        throughput_query = """
            SELECT 
                DATE_TRUNC('hour', created_at) as hour,
                COUNT(*) as reviews_processed,
                COUNT(*) FILTER (WHERE status = 'completed') as successful_reviews,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_reviews
            FROM review_results
            WHERE created_at >= $1
            GROUP BY DATE_TRUNC('hour', created_at)
            ORDER BY hour DESC
        """
        
        throughput_rows = await db_session.fetch(throughput_query, since_date)
        
        return {
            "period": {
                "hours": hours,
                "start_date": since_date,
                "end_date": datetime.utcnow(),
            },
            "hourly_performance": [
                {
                    "hour": row["hour"].isoformat(),
                    "review_count": row["review_count"],
                    "avg_time_ms": round(float(row["avg_time"] or 0), 1),
                    "min_time_ms": row["min_time"] or 0,
                    "max_time_ms": row["max_time"] or 0,
                    "median_time_ms": round(float(row["median_time"] or 0), 1),
                    "p95_time_ms": round(float(row["p95_time"] or 0), 1),
                }
                for row in hourly_rows
            ],
            "slowest_reviews": [
                {
                    "review_id": row["id"],
                    "processing_time_ms": row["processing_time_ms"],
                    "tokens_used": row["tokens_used"],
                    "model_used": row["model_used"],
                    "suggestion_count": row["suggestion_count"],
                    "created_at": row["created_at"].isoformat(),
                }
                for row in slow_rows
            ],
            "throughput": [
                {
                    "hour": row["hour"].isoformat(),
                    "reviews_processed": row["reviews_processed"],
                    "successful_reviews": row["successful_reviews"],
                    "failed_reviews": row["failed_reviews"],
                    "success_rate": round(
                        row["successful_reviews"] / max(row["reviews_processed"], 1) * 100, 1
                    ),
                }
                for row in throughput_rows
            ],
        }
        
    except Exception as e:
        logger.error("Failed to fetch performance metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")


@router.get("/quality")
async def get_quality_metrics(
    days: int = Query(default=30, le=90, description="Number of days for quality analysis"),
    db_session = Depends(get_db_session)
):
    """
    Get code quality analysis metrics
    
    - **days**: Number of days to include (max 90)
    
    Returns quality trends and insights
    """
    try:
        logger.info("Fetching quality metrics", days=days)
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Quality score distribution
        score_distribution_query = """
            SELECT 
                CASE 
                    WHEN overall_score >= 90 THEN 'excellent'
                    WHEN overall_score >= 80 THEN 'good'
                    WHEN overall_score >= 70 THEN 'fair'
                    WHEN overall_score >= 60 THEN 'poor'
                    ELSE 'very_poor'
                END as quality_tier,
                COUNT(*) as count,
                AVG(overall_score) as avg_score
            FROM review_results
            WHERE created_at >= $1 AND overall_score IS NOT NULL
            GROUP BY quality_tier
            ORDER BY avg_score DESC
        """
        
        score_rows = await db_session.fetch(score_distribution_query, since_date)
        
        # Issue severity trends
        severity_trends_query = """
            SELECT 
                DATE(r.created_at) as date,
                s.severity,
                COUNT(*) as count
            FROM review_suggestions s
            JOIN review_results r ON s.review_result_id = r.id
            WHERE r.created_at >= $1
            GROUP BY DATE(r.created_at), s.severity
            ORDER BY date DESC, severity
        """
        
        severity_rows = await db_session.fetch(severity_trends_query, since_date)
        
        # Most common issues
        common_issues_query = """
            SELECT 
                suggestion_type,
                severity,
                title,
                COUNT(*) as frequency,
                AVG(confidence_score) as avg_confidence
            FROM review_suggestions s
            JOIN review_results r ON s.review_result_id = r.id
            WHERE r.created_at >= $1
            GROUP BY suggestion_type, severity, title
            HAVING COUNT(*) >= 3  -- Only show patterns that appear multiple times
            ORDER BY frequency DESC, avg_confidence DESC
            LIMIT 20
        """
        
        common_issues_rows = await db_session.fetch(common_issues_query, since_date)
        
        return {
            "period": {
                "days": days,
                "start_date": since_date,
                "end_date": datetime.utcnow(),
            },
            "quality_distribution": [
                {
                    "tier": row["quality_tier"],
                    "count": row["count"],
                    "avg_score": round(float(row["avg_score"] or 0), 1),
                }
                for row in score_rows
            ],
            "severity_trends": [
                {
                    "date": row["date"].isoformat(),
                    "severity": row["severity"],
                    "count": row["count"],
                }
                for row in severity_rows
            ],
            "common_issues": [
                {
                    "type": row["suggestion_type"],
                    "severity": row["severity"],
                    "title": row["title"],
                    "frequency": row["frequency"],
                    "avg_confidence": round(float(row["avg_confidence"] or 0), 1),
                }
                for row in common_issues_rows
            ],
        }
        
    except Exception as e:
        logger.error("Failed to fetch quality metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve quality metrics")
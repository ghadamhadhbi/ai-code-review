# =====================================================
# services/metrics/api/analytics.py
# =====================================================

from fastapi import APIRouter, HTTPException, Query
import structlog
from datetime import datetime, timedelta

from core.database import get_db_session

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/issues")
async def get_issue_analytics(
    days: int = Query(default=30, le=90, description="Number of days for issue analytics")
):
    """Get detailed issue analytics"""
    try:
        logger.info("Fetching issue analytics", days=days)
        
        async with get_db_session() as db:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Issue type distribution
            type_query = """
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
            """
            
            type_rows = await db.fetch(type_query, since_date)
            
            # Most common issues
            common_query = """
                SELECT 
                    title,
                    suggestion_type,
                    severity,
                    COUNT(*) as frequency,
                    AVG(confidence_score) as avg_confidence
                FROM review_suggestions s
                JOIN review_results r ON s.review_result_id = r.id
                WHERE r.created_at >= $1
                GROUP BY title, suggestion_type, severity
                HAVING COUNT(*) >= 3
                ORDER BY frequency DESC
                LIMIT 20
            """
            
            common_rows = await db.fetch(common_query, since_date)
            
            # Severity trends over time
            trend_query = """
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
            
            trend_rows = await db.fetch(trend_query, since_date)
            
            return {
                "period": {
                    "days": days,
                    "start_date": since_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                },
                "issue_types": [
                    {
                        "type": row["suggestion_type"],
                        "severity": row["severity"],
                        "count": row["count"],
                        "avg_confidence": round(float(row["avg_confidence"] or 0), 1),
                    }
                    for row in type_rows
                ],
                "common_issues": [
                    {
                        "title": row["title"],
                        "type": row["suggestion_type"],
                        "severity": row["severity"],
                        "frequency": row["frequency"],
                        "avg_confidence": round(float(row["avg_confidence"] or 0), 1),
                    }
                    for row in common_rows
                ],
                "severity_trends": [
                    {
                        "date": row["date"].isoformat(),
                        "severity": row["severity"],
                        "count": row["count"],
                    }
                    for row in trend_rows
                ]
            }
        
    except Exception as e:
        logger.error("Failed to fetch issue analytics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve issue analytics")


@router.get("/performance")
async def get_performance_analytics(
    hours: int = Query(default=24, le=168, description="Number of hours for performance data")
):
    """Get detailed performance analytics"""
    try:
        logger.info("Fetching performance analytics", hours=hours)
        
        async with get_db_session() as db:
            since_date = datetime.utcnow() - timedelta(hours=hours)
            
            # Hourly performance
            hourly_query = """
                SELECT 
                    DATE_TRUNC('hour', created_at) as hour,
                    COUNT(*) as review_count,
                    AVG(processing_time_ms) as avg_time,
                    MIN(processing_time_ms) as min_time,
                    MAX(processing_time_ms) as max_time,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_time
                FROM review_results
                WHERE created_at >= $1 AND processing_time_ms > 0
                GROUP BY DATE_TRUNC('hour', created_at)
                ORDER BY hour DESC
            """
            
            hourly_rows = await db.fetch(hourly_query, since_date)
            
            # Token usage analytics
            token_query = """
                SELECT 
                    DATE(created_at) as date,
                    SUM(tokens_used) as total_tokens,
                    AVG(tokens_used) as avg_tokens,
                    COUNT(*) as review_count
                FROM review_results
                WHERE created_at >= $1 AND tokens_used > 0
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """
            
            token_rows = await db.fetch(token_query, since_date)
            
            return {
                "period": {
                    "hours": hours,
                    "start_date": since_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                },
                "hourly_performance": [
                    {
                        "hour": row["hour"].isoformat(),
                        "review_count": row["review_count"],
                        "avg_time_ms": round(float(row["avg_time"] or 0), 1),
                        "min_time_ms": row["min_time"] or 0,
                        "max_time_ms": row["max_time"] or 0,
                        "p95_time_ms": round(float(row["p95_time"] or 0), 1),
                    }
                    for row in hourly_rows
                ],
                "token_usage": [
                    {
                        "date": row["date"].isoformat(),
                        "total_tokens": row["total_tokens"],
                        "avg_tokens": round(float(row["avg_tokens"] or 0), 1),
                        "review_count": row["review_count"],
                        "estimated_cost_usd": round((row["total_tokens"] or 0) * 0.00002, 4),
                    }
                    for row in token_rows
                ]
            }
        
    except Exception as e:
        logger.error("Failed to fetch performance analytics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve performance analytics")


@router.get("/quality")
async def get_quality_analytics(
    days: int = Query(default=30, le=90, description="Number of days for quality analysis")
):
    """Get code quality analytics"""
    try:
        logger.info("Fetching quality analytics", days=days)
        
        async with get_db_session() as db:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Quality score distribution
            score_query = """
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
            
            score_rows = await db.fetch(score_query, since_date)
            
            # Quality trends by language
            language_quality_query = """
                SELECT 
                    COALESCE(u.language, 'unknown') as language,
                    AVG(r.overall_score) as avg_score,
                    COUNT(*) as review_count,
                    COUNT(*) FILTER (WHERE r.overall_score >= 80) as good_reviews
                FROM review_results r
                LEFT JOIN uploads u ON r.upload_id = u.id
                WHERE r.created_at >= $1 AND r.overall_score IS NOT NULL
                GROUP BY COALESCE(u.language, 'unknown')
                HAVING COUNT(*) >= 3
                ORDER BY avg_score DESC
            """
            
            language_rows = await db.fetch(language_quality_query, since_date)
            
            return {
                "period": {
                    "days": days,
                    "start_date": since_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat(),
                },
                "quality_distribution": [
                    {
                        "tier": row["quality_tier"],
                        "count": row["count"],
                        "avg_score": round(float(row["avg_score"] or 0), 1),
                    }
                    for row in score_rows
                ],
                "language_quality": [
                    {
                        "language": row["language"],
                        "avg_score": round(float(row["avg_score"] or 0), 1),
                        "review_count": row["review_count"],
                        "good_rate": round(row["good_reviews"] / max(row["review_count"], 1) * 100, 1),
                    }
                    for row in language_rows
                ]
            }
        
    except Exception as e:
        logger.error("Failed to fetch quality analytics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve quality analytics")
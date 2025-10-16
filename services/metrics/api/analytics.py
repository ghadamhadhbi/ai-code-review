# =====================================================
# services/metrics/api/analytics.py
# =====================================================

from fastapi import APIRouter, Query
from datetime import datetime, timedelta
import structlog

from core.database import db_pool

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/issues")
async def get_issue_analytics(days: int = Query(30, ge=1, le=90)):
    """Get issue analytics"""
    try:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        async with db_pool.acquire() as conn:
            # Issue types distribution
            issue_types = await conn.fetch("""
                SELECT 
                    rs.suggestion_type as type,
                    rs.severity,
                    COUNT(*) as count
                FROM review_suggestions rs
                JOIN review_results rr ON rs.review_result_id = rr.id
                WHERE rr.created_at >= $1
                GROUP BY rs.suggestion_type, rs.severity
                ORDER BY count DESC
            """, since_date)
            
            # Severity trends by day
            severity_trends = await conn.fetch("""
                SELECT 
                    DATE(rr.created_at) as date,
                    rs.severity,
                    COUNT(*) as count
                FROM review_suggestions rs
                JOIN review_results rr ON rs.review_result_id = rr.id
                WHERE rr.created_at >= $1
                GROUP BY DATE(rr.created_at), rs.severity
                ORDER BY date DESC
            """, since_date)
            
            # Most common issues
            common_issues = await conn.fetch("""
                SELECT 
                    rs.title,
                    rs.suggestion_type as type,
                    rs.severity,
                    COUNT(*) as frequency
                FROM review_suggestions rs
                JOIN review_results rr ON rs.review_result_id = rr.id
                WHERE rr.created_at >= $1
                GROUP BY rs.title, rs.suggestion_type, rs.severity
                ORDER BY frequency DESC
                LIMIT 20
            """, since_date)
            
            return {
                "issue_types": [dict(r) for r in issue_types],
                "severity_trends": [
                    {**dict(r), "date": r['date'].isoformat()} 
                    for r in severity_trends
                ],
                "common_issues": [dict(r) for r in common_issues]
            }
            
    except Exception as e:
        logger.error("Error fetching issue analytics", error=str(e))
        return {
            "issue_types": [],
            "severity_trends": [],
            "common_issues": []
        }


@router.get("/performance")
async def get_performance_analytics(hours: int = Query(24, ge=1, le=168)):
    """Get performance analytics"""
    try:
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with db_pool.acquire() as conn:
            # Hourly performance
            hourly_perf = await conn.fetch("""
                SELECT 
                    DATE_TRUNC('hour', created_at) as hour,
                    COUNT(*) as review_count,
                    AVG(processing_time_ms)::integer as avg_time_ms,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms)::integer as p95_time_ms,
                    MAX(processing_time_ms) as max_time_ms
                FROM review_results
                WHERE created_at >= $1 AND processing_time_ms IS NOT NULL
                GROUP BY DATE_TRUNC('hour', created_at)
                ORDER BY hour DESC
            """, since_time)
            
            # Token usage
            token_usage = await conn.fetch("""
                SELECT 
                    model_used,
                    COUNT(*) as review_count,
                    SUM(tokens_used) as total_tokens,
                    AVG(tokens_used)::integer as avg_tokens
                FROM review_results
                WHERE created_at >= $1 AND tokens_used > 0
                GROUP BY model_used
            """, since_time)
            
            return {
                "hourly_performance": [
                    {**dict(r), "hour": r['hour'].isoformat()} 
                    for r in hourly_perf
                ],
                "token_usage": [dict(r) for r in token_usage]
            }
            
    except Exception as e:
        logger.error("Error fetching performance analytics", error=str(e))
        return {
            "hourly_performance": [],
            "token_usage": []
        }


@router.get("/quality")
async def get_quality_analytics(days: int = Query(30, ge=1, le=90)):
    """Get quality analytics"""
    try:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        async with db_pool.acquire() as conn:
            # Quality tiers distribution
            quality_dist = await conn.fetch("""
                SELECT 
                    CASE 
                        WHEN overall_score >= 90 THEN 'excellent'
                        WHEN overall_score >= 70 THEN 'good'
                        WHEN overall_score >= 50 THEN 'fair'
                        WHEN overall_score >= 30 THEN 'poor'
                        ELSE 'very_poor'
                    END as tier,
                    COUNT(*) as count,
                    AVG(overall_score)::numeric(10,2) as avg_score
                FROM review_results
                WHERE created_at >= $1 AND overall_score IS NOT NULL
                GROUP BY tier
            """, since_date)
            
            # Quality by language
            lang_quality = await conn.fetch("""
                SELECT 
                    u.language,
                    COUNT(rr.id) as review_count,
                    AVG(rr.overall_score)::numeric(10,2) as avg_score,
                    SUM(CASE WHEN rr.overall_score >= 70 THEN 1 ELSE 0 END)::float / 
                        NULLIF(COUNT(rr.id), 0) * 100 as good_rate
                FROM uploads u
                JOIN review_results rr ON u.id = rr.upload_id
                WHERE rr.created_at >= $1 AND rr.overall_score IS NOT NULL
                GROUP BY u.language
                ORDER BY review_count DESC
            """, since_date)
            
            return {
                "quality_distribution": [dict(r) for r in quality_dist],
                "language_quality": [
                    {
                        **dict(r),
                        "avg_score": float(r['avg_score']),
                        "good_rate": float(r['good_rate']) if r['good_rate'] else 0
                    }
                    for r in lang_quality
                ]
            }
            
    except Exception as e:
        logger.error("Error fetching quality analytics", error=str(e))
        return {
            "quality_distribution": [],
            "language_quality": []
        }


"""
Dashboard API endpoints for metrics service - FIXED VERSION
Handles graceful degradation when database is unavailable
"""

from fastapi import APIRouter, Query
from datetime import datetime, timedelta
import structlog

from core.database import get_db_pool, is_db_available

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/stats")
async def get_review_stats(days: int = Query(7, ge=1, le=90)):
    """
    Get review statistics for dashboard
    
    Args:
        days: Number of days to analyze (1-90)
    
    Returns:
        Review counts, scores, and processing metrics
    """
    try:
        logger.info("Fetching review stats", days=days)
        
        # Check if database is available
        if not is_db_available():
            logger.warning("Database not available - returning empty stats")
            return {
                "period_days": days,
                "total_reviews": 0,
                "pending_reviews": 0,
                "processing_reviews": 0,
                "completed_reviews": 0,
                "failed_reviews": 0,
                "average_score": None,
                "average_processing_time_ms": None,
                "total_suggestions": 0,
                "total_tokens_used": 0,
                "warning": "Database not available"
            }
        
        db_pool = await get_db_pool()
        if not db_pool:
            logger.warning("Database pool is None - returning empty stats")
            return {
                "period_days": days,
                "total_reviews": 0,
                "pending_reviews": 0,
                "processing_reviews": 0,
                "completed_reviews": 0,
                "failed_reviews": 0,
                "average_score": None,
                "average_processing_time_ms": None,
                "total_suggestions": 0,
                "total_tokens_used": 0,
                "warning": "Database not available"
            }
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        async with db_pool.acquire() as conn:
            # Total reviews
            total_reviews = await conn.fetchval(
                "SELECT COUNT(*) FROM review_results WHERE created_at >= $1",
                since_date
            )
            
            # Status counts
            status_counts = await conn.fetch("""
                SELECT status, COUNT(*) as count
                FROM review_results
                WHERE created_at >= $1
                GROUP BY status
            """, since_date)
            
            pending = sum(r['count'] for r in status_counts if r['status'] == 'pending')
            processing = sum(r['count'] for r in status_counts if r['status'] == 'processing')
            completed = sum(r['count'] for r in status_counts if r['status'] == 'completed')
            failed = sum(r['count'] for r in status_counts if r['status'] == 'failed')
            
            # Average score
            avg_score = await conn.fetchval("""
                SELECT AVG(overall_score)::numeric(10,2)
                FROM review_results
                WHERE created_at >= $1 AND overall_score IS NOT NULL
            """, since_date)
            
            # Average processing time
            avg_time = await conn.fetchval("""
                SELECT AVG(processing_time_ms)::integer
                FROM review_results
                WHERE created_at >= $1 AND processing_time_ms IS NOT NULL
            """, since_date)
            
            # Total suggestions
            total_suggestions = await conn.fetchval("""
                SELECT COUNT(*)
                FROM review_suggestions rs
                JOIN review_results rr ON rs.review_result_id = rr.id
                WHERE rr.created_at >= $1
            """, since_date)
            
            # Total tokens
            total_tokens = await conn.fetchval("""
                SELECT COALESCE(SUM(tokens_used), 0)
                FROM review_results
                WHERE created_at >= $1
            """, since_date)
            
            return {
                "period_days": days,
                "total_reviews": total_reviews or 0,
                "pending_reviews": pending or 0,
                "processing_reviews": processing or 0,
                "completed_reviews": completed or 0,
                "failed_reviews": failed or 0,
                "average_score": float(avg_score) if avg_score else None,
                "average_processing_time_ms": avg_time or None,
                "total_suggestions": total_suggestions or 0,
                "total_tokens_used": total_tokens or 0
            }
            
    except Exception as e:
        logger.error("Error fetching stats", error=str(e), exc_info=True)
        return {
            "period_days": days,
            "total_reviews": 0,
            "pending_reviews": 0,
            "processing_reviews": 0,
            "completed_reviews": 0,
            "failed_reviews": 0,
            "average_score": None,
            "average_processing_time_ms": None,
            "total_suggestions": 0,
            "total_tokens_used": 0,
            "error": str(e)
        }
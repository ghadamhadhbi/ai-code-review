# =====================================================
# services/metrics/core/database.py
# =====================================================

import asyncpg
import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, List, Dict, Any
from datetime import datetime, timedelta

from core.config import settings

logger = structlog.get_logger(__name__)

# Global connection pool
_connection_pool: Optional[asyncpg.Pool] = None


async def init_db_pool():
    """Initialize database connection pool"""
    global _connection_pool
    
    try:
        logger.info("Initializing database connection pool")
        
        _connection_pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        
        logger.info("Database connection pool created successfully")
        
    except Exception as e:
        logger.error("Failed to create database connection pool", error=str(e))
        raise Exception(f"Database initialization failed: {str(e)}")


async def close_db_pool():
    """Close database connection pool"""
    global _connection_pool
    
    if _connection_pool:
        logger.info("Closing database connection pool")
        await _connection_pool.close()
        _connection_pool = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get database session from connection pool"""
    if not _connection_pool:
        await init_db_pool()
    
    async with _connection_pool.acquire() as connection:
        try:
            yield connection
        except Exception as e:
            logger.error("Database session error", error=str(e))
            raise


async def test_connection():
    """Test database connection"""
    try:
        async with get_db_session() as db:
            result = await db.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error("Database connection test failed", error=str(e))
        raise


# Dashboard data queries
async def get_dashboard_overview(days: int = 7) -> Dict[str, Any]:
    """Get dashboard overview metrics"""
    async with get_db_session() as db:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Main overview query
        overview_query = """
            SELECT 
                COUNT(DISTINCT r.id) as total_reviews,
                COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'completed') as completed_reviews,
                COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'failed') as failed_reviews,
                COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'pending') as pending_reviews,
                COALESCE(AVG(r.overall_score) FILTER (WHERE r.overall_score IS NOT NULL), 0) as avg_score,
                COUNT(DISTINCT s.id) as total_suggestions,
                COUNT(DISTINCT s.id) FILTER (WHERE s.severity = 'critical') as critical_issues,
                COUNT(DISTINCT s.id) FILTER (WHERE s.severity = 'high') as high_issues,
                COALESCE(SUM(r.tokens_used), 0) as total_tokens,
                COALESCE(AVG(r.processing_time_ms), 0) as avg_processing_time
            FROM review_results r
            LEFT JOIN review_suggestions s ON s.review_result_id = r.id
            WHERE r.created_at >= $1
        """
        
        overview = await db.fetchrow(overview_query, since_date)
        
        return {
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
        }


async def get_daily_activity(days: int = 30) -> List[Dict[str, Any]]:
    """Get daily activity trends"""
    async with get_db_session() as db:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        query = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as reviews,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COALESCE(AVG(overall_score) FILTER (WHERE overall_score IS NOT NULL), 0) as avg_score
            FROM review_results
            WHERE created_at >= $1
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """
        
        rows = await db.fetch(query, since_date)
        
        return [
            {
                "date": row["date"].isoformat(),
                "reviews": row["reviews"],
                "completed": row["completed"],
                "avg_score": round(float(row["avg_score"] or 0), 1),
            }
            for row in rows
        ]


async def get_language_distribution(days: int = 30) -> List[Dict[str, Any]]:
    """Get programming language distribution"""
    async with get_db_session() as db:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        query = """
            SELECT 
                COALESCE(u.language, 'unknown') as language,
                COUNT(*) as count,
                COALESCE(AVG(r.overall_score) FILTER (WHERE r.overall_score IS NOT NULL), 0) as avg_score
            FROM review_results r
            LEFT JOIN uploads u ON r.upload_id = u.id
            WHERE r.created_at >= $1
            GROUP BY COALESCE(u.language, 'unknown')
            ORDER BY count DESC
        """
        
        rows = await db.fetch(query, since_date)
        
        return [
            {
                "language": row["language"],
                "count": row["count"],
                "avg_score": round(float(row["avg_score"] or 0), 1),
            }
            for row in rows
        ]

# =====================================================
# services/metrics/core/database.py
# =====================================================

import asyncpg
import structlog
from core.config import settings

logger = structlog.get_logger(__name__)

db_pool = None


async def init_db_pool():
    """Initialize database connection pool"""
    global db_pool
    db_pool = await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=2,
        max_size=10,
        timeout=30
    )
    logger.info("Database pool created")


async def close_db_pool():
    """Close database connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")


async def test_connection():
    """Test database connection"""
    async with db_pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        return result == 1


async def get_connection():
    """Get database connection from pool"""
    return await db_pool.acquire()


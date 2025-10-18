"""
Database connection management for Metrics Service - FIXED VERSION
Handles connection pool initialization and graceful degradation
"""

import asyncpg
import structlog
from typing import Optional

from core.config import settings

logger = structlog.get_logger(__name__)

# Global connection pool
db_pool: Optional[asyncpg.Pool] = None


async def init_db_pool():
    """Initialize database connection pool"""
    global db_pool
    
    try:
        logger.info(
            "Initializing database connection pool",
            url=settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else "hidden",
            min_size=settings.DB_POOL_MIN_SIZE,
            max_size=settings.DB_POOL_MAX_SIZE,
        )
        
        db_pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=settings.DB_POOL_MIN_SIZE,
            max_size=settings.DB_POOL_MAX_SIZE,
            command_timeout=60,
            max_inactive_connection_lifetime=300,
        )
        
        # Test the connection
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            logger.info("Database pool created and tested successfully", test_result=result)
        
        return True
        
    except Exception as e:
        logger.error(
            "Failed to create database pool - metrics service will run in degraded mode",
            error=str(e),
            error_type=type(e).__name__,
        )
        db_pool = None
        return False


async def close_db_pool():
    """Close database connection pool"""
    global db_pool
    
    if db_pool:
        try:
            await db_pool.close()
            logger.info("Database pool closed")
        except Exception as e:
            logger.error("Error closing database pool", error=str(e))
    else:
        logger.info("No database pool to close")


async def test_connection():
    """Test database connection"""
    global db_pool
    
    if not db_pool:
        logger.warning("Database pool not initialized - cannot test connection")
        return False
    
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error("Database connection test failed", error=str(e))
        return False


async def get_db_connection():
    """
    Get a database connection from the pool
    Raises RuntimeError if pool is not initialized
    """
    global db_pool
    
    if not db_pool:
        raise RuntimeError("Database pool not initialized")
    
    return await db_pool.acquire()


def is_db_available() -> bool:
    """Check if database pool is available"""
    global db_pool
    return db_pool is not None


async def get_db_pool() -> Optional[asyncpg.Pool]:
    """Get the database pool (can be None)"""
    global db_pool
    return db_pool


async def execute_with_fallback(query: str, *args, fallback_result=None):
    """
    Execute a query with fallback if database is unavailable
    
    Args:
        query: SQL query to execute
        *args: Query parameters
        fallback_result: Value to return if database is unavailable
    
    Returns:
        Query result or fallback_result if database unavailable
    """
    global db_pool
    
    if not db_pool:
        logger.warning("Database unavailable - returning fallback result")
        return fallback_result
    
    try:
        async with db_pool.acquire() as conn:
            return await conn.fetch(query, *args)
    except Exception as e:
        logger.error("Database query failed", error=str(e), query=query[:100])
        return fallback_result


async def fetch_one_with_fallback(query: str, *args, fallback_result=None):
    """
    Fetch one record with fallback if database is unavailable
    
    Args:
        query: SQL query to execute
        *args: Query parameters
        fallback_result: Value to return if database is unavailable
    
    Returns:
        Query result or fallback_result if database unavailable
    """
    global db_pool
    
    if not db_pool:
        logger.warning("Database unavailable - returning fallback result")
        return fallback_result
    
    try:
        async with db_pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    except Exception as e:
        logger.error("Database query failed", error=str(e), query=query[:100])
        return fallback_result
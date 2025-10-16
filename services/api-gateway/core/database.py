"""
API Gateway - Database Connection Module - FIXED
Handles PostgreSQL connection pooling and session management
"""

import asyncpg
import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

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
            server_settings={
                'jit': 'off'  # Disable JIT for compatibility
            }
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
    """
    Get database session from connection pool
    
    ✅ FIX: Better error handling with meaningful messages
    """
    if not _connection_pool:
        try:
            await init_db_pool()
        except Exception as e:
            logger.error("Failed to initialize database pool", error=str(e))
            raise Exception(f"Database pool initialization failed: {str(e)}")
    
    try:
        async with _connection_pool.acquire() as connection:
            yield connection
    except asyncpg.PostgresError as e:
        # ✅ FIX: Specific PostgreSQL error handling
        logger.error(
            "PostgreSQL error in database session",
            error=str(e),
            error_code=e.sqlstate if hasattr(e, 'sqlstate') else None,
            error_detail=getattr(e, 'detail', None)
        )
        raise Exception(f"Database operation failed: {str(e)}")
    except Exception as e:
        # ✅ FIX: Generic error with full details
        logger.error(
            "Database session error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise Exception(f"Database session error: {type(e).__name__}: {str(e)}")


async def test_connection():
    """Test database connection"""
    try:
        async with get_db_session() as db:
            result = await db.fetchval("SELECT 1")
            if result == 1:
                logger.info("Database connection test successful")
                return True
            else:
                raise Exception("Database connection test returned unexpected result")
                
    except Exception as e:
        logger.error("Database connection test failed", error=str(e))
        raise Exception(f"Database connection test failed: {str(e)}")


# Aliases for compatibility
async def initialize_database():
    """Initialize database - alias for init_db_pool"""
    await init_db_pool()


async def shutdown_database():
    """Shutdown database - alias for close_db_pool"""
    await close_db_pool()
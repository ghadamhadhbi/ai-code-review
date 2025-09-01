"""
Database connection and session management
"""

import asyncpg
import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional
import json
from datetime import datetime

from core.config import settings
from core.exceptions import DatabaseError

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
                'jit': 'off'  # Disable JIT for better compatibility
            }
        )
        
        logger.info("Database connection pool created successfully")
        
    except Exception as e:
        logger.error("Failed to create database connection pool", error=str(e))
        raise DatabaseError(f"Database initialization failed: {str(e)}")


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
            raise DatabaseError(f"Database operation failed: {str(e)}")


async def test_connection():
    """Test database connection"""
    try:
        async with get_db_session() as db:
            result = await db.fetchval("SELECT 1")
            if result == 1:
                logger.info("Database connection test successful")
                return True
            else:
                raise DatabaseError("Database connection test returned unexpected result")
                
    except Exception as e:
        logger.error("Database connection test failed", error=str(e))
        raise DatabaseError(f"Database connection test failed: {str(e)}")


# Database utility functions

async def create_upload_record(db: asyncpg.Connection, upload_data: dict) -> str:
    """Create a new upload record"""
    query = """
        INSERT INTO uploads (
            id, author_email, description, language, 
            file_count, total_size_bytes, status, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, 'uploaded', NOW()
        ) RETURNING id
    """
    
    upload_id = await db.fetchval(
        query,
        upload_data["upload_id"],
        upload_data.get("author_email"),
        upload_data.get("description"),
        upload_data.get("language"),
        upload_data["file_count"],
        upload_data["total_size_bytes"]
    )
    
    return upload_id


async def get_upload_by_id(db: asyncpg.Connection, upload_id: str) -> Optional[dict]:
    """Get upload record by ID"""
    query = """
        SELECT id, author_email, description, language, file_count, 
               total_size_bytes, status, created_at, updated_at, error_message
        FROM uploads WHERE id = $1
    """
    
    row = await db.fetchrow(query, upload_id)
    
    if row:
        return {
            "upload_id": row["id"],
            "author_email": row["author_email"],
            "description": row["description"],
            "language": row["language"],
            "file_count": row["file_count"],
            "total_size_bytes": row["total_size_bytes"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "error_message": row["error_message"],
        }
    
    return None


async def update_upload_status(db: asyncpg.Connection, upload_id: str, 
                              status: str, error_message: Optional[str] = None):
    """Update upload status"""
    query = """
        UPDATE uploads 
        SET status = $2, updated_at = NOW(), error_message = $3
        WHERE id = $1
    """
    
    await db.execute(query, upload_id, status, error_message)


async def get_recent_reviews(db: asyncpg.Connection, limit: int = 10) -> List[dict]:
    """Get recent review results"""
    query = """
        SELECT r.id, r.overall_score, r.summary, r.status, r.created_at,
               c.commit_hash, c.author_name, c.repository_id,
               repo.name as repo_name, repo.owner as repo_owner
        FROM review_results r
        LEFT JOIN commits c ON r.commit_id = c.id
        LEFT JOIN repositories repo ON c.repository_id = repo.id
        ORDER BY r.created_at DESC
        LIMIT $1
    """
    
    rows = await db.fetch(query, limit)
    
    return [
        {
            "review_id": row["id"],
            "overall_score": row["overall_score"],
            "summary": row["summary"],
            "status": row["status"],
            "created_at": row["created_at"],
            "commit_hash": row["commit_hash"],
            "author_name": row["author_name"],
            "repository": {
                "id": row["repository_id"],
                "name": row["repo_name"],
                "owner": row["repo_owner"],
            } if row["repo_name"] else None,
        }
        for row in rows
    ]


async def get_review_by_id(db: asyncpg.Connection, review_id: int) -> Optional[dict]:
    """Get detailed review results by ID"""
    # Get main review record
    review_query = """
        SELECT r.*, c.commit_hash, c.author_name, c.commit_message,
               repo.name as repo_name, repo.owner as repo_owner
        FROM review_results r
        LEFT JOIN commits c ON r.commit_id = c.id
        LEFT JOIN repositories repo ON c.repository_id = repo.id
        WHERE r.id = $1
    """
    
    review_row = await db.fetchrow(review_query, review_id)
    
    if not review_row:
        return None
    
    # Get suggestions for this review
    suggestions_query = """
        SELECT * FROM review_suggestions 
        WHERE review_result_id = $1
        ORDER BY severity DESC, line_number ASC
    """
    
    suggestion_rows = await db.fetch(suggestions_query, review_id)
    
    return {
        "review_id": review_row["id"],
        "overall_score": review_row["overall_score"],
        "summary": review_row["summary"],
        "model_used": review_row["model_used"],
        "tokens_used": review_row["tokens_used"],
        "processing_time_ms": review_row["processing_time_ms"],
        "status": review_row["status"],
        "created_at": review_row["created_at"],
        "completed_at": review_row["completed_at"],
        "error_message": review_row["error_message"],
        "commit": {
            "hash": review_row["commit_hash"],
            "author": review_row["author_name"],
            "message": review_row["commit_message"],
        } if review_row["commit_hash"] else None,
        "repository": {
            "name": review_row["repo_name"],
            "owner": review_row["repo_owner"],
        } if review_row["repo_name"] else None,
        "suggestions": [
            {
                "id": row["id"],
                "file_path": row["file_path"],
                "line_number": row["line_number"],
                "suggestion_type": row["suggestion_type"],
                "severity": row["severity"],
                "title": row["title"],
                "description": row["description"],
                "suggested_fix": row["suggested_fix"],
                "confidence_score": row["confidence_score"],
            }
            for row in suggestion_rows
        ],
    }
"""
Reviews API endpoints - FIXED - Reviews persist correctly
Retrieves and manages code reviews with proper database queries
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
import structlog
import traceback
from datetime import datetime, timedelta

from core.database import get_db_session

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/stats")
async def get_review_stats(
    days: int = Query(7, ge=1, le=90),
    db_session = Depends(get_db_session)
):
    """Get review statistics for the given period"""
    try:
        if hasattr(db_session, '__aenter__'):
            async with db_session as conn:
                return await _fetch_stats(conn, days)
        else:
            return await _fetch_stats(db_session, days)
        
    except Exception as e:
        logger.error("Failed to retrieve statistics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")


async def _fetch_stats(conn, days):
    """Fetch statistics - Calculate date in Python"""
    since_date = datetime.utcnow() - timedelta(days=days)
    
    query = """
        SELECT
            COUNT(*) as total_reviews,
            SUM(CASE WHEN r.status = 'pending' THEN 1 ELSE 0 END) as pending_reviews,
            SUM(CASE WHEN r.status = 'completed' THEN 1 ELSE 0 END) as completed_reviews,
            SUM(CASE WHEN r.status = 'failed' THEN 1 ELSE 0 END) as failed_reviews,
            COUNT(DISTINCT u.language) as unique_languages,
            SUM(u.total_size_bytes) as total_bytes_processed,
            AVG(r.overall_score) as avg_score
        FROM review_results r
        JOIN uploads u ON u.id = r.upload_id
        WHERE r.created_at >= $1
    """
    
    row = await conn.fetchrow(query, since_date)
    
    if not row:
        return {
            "period_days": days,
            "since_date": since_date.isoformat(),
            "total_reviews": 0,
            "pending_reviews": 0,
            "completed_reviews": 0,
            "failed_reviews": 0,
            "unique_languages": 0,
            "total_bytes_processed": 0,
            "success_rate": 0,
            "average_score": 0
        }
    
    completed = row["completed_reviews"] or 0
    total = row["total_reviews"] or 0
    
    return {
        "period_days": days,
        "since_date": since_date.isoformat(),
        "total_reviews": total,
        "pending_reviews": row["pending_reviews"] or 0,
        "completed_reviews": completed,
        "failed_reviews": row["failed_reviews"] or 0,
        "unique_languages": row["unique_languages"] or 0,
        "total_bytes_processed": row["total_bytes_processed"] or 0,
        "success_rate": round((completed / total * 100) if total > 0 else 0, 2),
        "average_score": round(float(row["avg_score"] or 0), 2)
    }


@router.get("/")
async def get_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("desc"),
    db_session = Depends(get_db_session)
):
    """Get all reviews with pagination - FIX: Reviews persist correctly"""
    try:
        if hasattr(db_session, '__aenter__'):
            async with db_session as conn:
                return await _fetch_reviews(conn, page, page_size, status, language, sort_by, sort_order)
        else:
            return await _fetch_reviews(db_session, page, page_size, status, language, sort_by, sort_order)
        
    except Exception as e:
        logger.error("Error in get_reviews", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve reviews: {str(e)}")


async def _fetch_reviews(conn, page, page_size, status, language, sort_by, sort_order):
    """Fetch reviews - FIX: Proper aggregation to show all reviews"""
    
    # Validate sort
    valid_sort_fields = ["created_at", "status", "overall_score"]
    if sort_by not in valid_sort_fields:
        sort_by = "created_at"
    
    sort_direction = "DESC" if sort_order and sort_order.lower() == "desc" else "ASC"
    
    # Build WHERE clause
    where_conditions = []
    params = []
    param_count = 1
    
    if status:
        where_conditions.append(f"r.status = ${param_count}")
        params.append(status)
        param_count += 1
    
    if language:
        where_conditions.append(f"u.language = ${param_count}")
        params.append(language)
        param_count += 1
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # ✅ FIX: Get total count - this ensures we see ALL reviews
    count_query = f"""
        SELECT COUNT(DISTINCT r.id) as total
        FROM review_results r
        JOIN uploads u ON u.id = r.upload_id
        WHERE {where_clause}
    """
    
    count_result = await conn.fetchrow(count_query, *params)
    total = count_result["total"] if count_result else 0
    
    logger.info("Total reviews in database", total=total, status=status, language=language)
    
    # Calculate pagination
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    
    # Add pagination params
    params.append(page_size)
    params.append(offset)
    
    # ✅ FIX: Get reviews with proper file aggregation
    query = f"""
        SELECT 
            r.id as review_id,
            r.upload_id,
            r.status,
            r.overall_score,
            r.summary,
            r.model_used,
            r.created_at,
            r.completed_at,
            r.error_message,
            u.author_email,
            u.description,
            u.language,
            u.file_count,
            u.total_size_bytes,
            u.progress,
            COUNT(DISTINCT s.id) as suggestion_count,
            STRING_AGG(DISTINCT uf.filename, ', ' ORDER BY uf.filename) as filenames
        FROM review_results r
        JOIN uploads u ON u.id = r.upload_id
        LEFT JOIN review_suggestions s ON s.review_result_id = r.id
        LEFT JOIN upload_files uf ON uf.upload_id = u.id
        WHERE {where_clause}
        GROUP BY r.id, u.id, u.author_email, u.description, u.language, u.file_count, u.total_size_bytes, u.progress
        ORDER BY r.{sort_by} {sort_direction}
        LIMIT ${param_count}
        OFFSET ${param_count + 1}
    """
    
    rows = await conn.fetch(query, *params)
    
    # Transform rows
    reviews = []
    for row in rows:
        filename = row["filenames"] or row["description"] or "Code Review"
        
        reviews.append({
            "id": row["review_id"],
            "upload_id": row["upload_id"],
            "filename": filename,
            "status": row["status"],
            "language": row["language"],
            "file_count": row["file_count"],
            "total_size_bytes": row["total_size_bytes"],
            "author_email": row["author_email"],
            "description": row["description"],
            "overall_score": row["overall_score"],
            "summary": row["summary"],
            "suggestion_count": row["suggestion_count"] or 0,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
            "error_message": row["error_message"],
            "progress": row["progress"] or 0,
        })
    
    logger.info("Reviews fetched", count=len(reviews), total=total, page=page)
    
    return {
        "reviews": reviews,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }


@router.get("/{review_id}")
async def get_review_by_id(
    review_id: int,
    db_session = Depends(get_db_session)
):
    """Get a specific review by ID"""
    try:
        if hasattr(db_session, '__aenter__'):
            async with db_session as conn:
                return await _fetch_review_by_id(conn, review_id)
        else:
            return await _fetch_review_by_id(db_session, review_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve review", review_id=review_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve review: {str(e)}")


async def _fetch_review_by_id(conn, review_id):
    """Fetch single review with suggestions"""
    
    # Get review with upload info
    query = """
        SELECT 
            r.id as review_id,
            r.upload_id,
            r.status,
            r.overall_score,
            r.summary,
            r.model_used,
            r.tokens_used,
            r.processing_time_ms,
            r.created_at,
            r.completed_at,
            r.error_message,
            u.author_email,
            u.description,
            u.language,
            u.file_count,
            u.total_size_bytes,
            u.progress,
            STRING_AGG(DISTINCT uf.filename, ', ' ORDER BY uf.filename) as filenames
        FROM review_results r
        JOIN uploads u ON u.id = r.upload_id
        LEFT JOIN upload_files uf ON uf.upload_id = u.id
        WHERE r.id = $1
        GROUP BY r.id, u.id, u.author_email, u.description, u.language, u.file_count, u.total_size_bytes, u.progress
    """
    
    row = await conn.fetchrow(query, review_id)
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Review {review_id} not found")
    
    # Get suggestions
    suggestions_query = """
        SELECT 
            id,
            file_path,
            line_number,
            suggestion_type,
            severity,
            title,
            description,
            suggested_fix,
            confidence_score
        FROM review_suggestions
        WHERE review_result_id = $1
        ORDER BY 
            CASE severity 
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
                ELSE 5
            END,
            line_number ASC
    """
    
    suggestion_rows = await conn.fetch(suggestions_query, review_id)
    
    suggestions = [
        {
            "id": s["id"],
            "file_path": s["file_path"],
            "line_number": s["line_number"],
            "suggestion_type": s["suggestion_type"],
            "severity": s["severity"],
            "title": s["title"],
            "description": s["description"],
            "suggested_fix": s["suggested_fix"],
            "confidence_score": s["confidence_score"]
        }
        for s in suggestion_rows
    ]
    
    filenames = row["filenames"] or row["description"] or "Code Review"
    
    review = {
        "id": row["review_id"],
        "upload_id": row["upload_id"],
        "filenames": filenames,
        "status": row["status"],
        "overall_score": row["overall_score"],
        "summary": row["summary"],
        "model_used": row["model_used"],
        "tokens_used": row["tokens_used"],
        "processing_time_ms": row["processing_time_ms"],
        "author_email": row["author_email"],
        "description": row["description"],
        "language": row["language"],
        "file_count": row["file_count"],
        "total_size_bytes": row["total_size_bytes"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
        "error_message": row["error_message"],
        "progress": row["progress"] or 0,
        "suggestions": suggestions,
        "suggestion_count": len(suggestions)
    }
    
    return {"review": review}
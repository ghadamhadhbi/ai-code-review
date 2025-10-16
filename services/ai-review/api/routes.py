"""
FastAPI routes for AI Review Service - FIXED VERSION
Handles review results, status, and statistics.
Confirmed against the Phase 1 PostgreSQL Schema.
"""

from fastapi import APIRouter, HTTPException, status, Query
from datetime import datetime, timedelta
from typing import Optional
import structlog

# NOTE: Assuming get_db_session is available from core.database
try:
    from core.database import get_db_session
except ImportError:
    # Fallback/Mock for get_db_session if running in a non-standard environment
    class MockDB:
        async def fetchval(self, query, *args): return 0
        async def fetch(self, query, *args): return []
        async def fetchrow(self, query, *args): return None
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc_val, exc_tb): pass
    def get_db_session():
        return MockDB()


logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ai-review",
        "version": "1.0.0"
    }


@router.get("/reviews")
async def get_reviews(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search query"),
    sort: Optional[str] = Query("created_desc", description="Sort order")
):
    """
    Get paginated list of reviews
    Returns: { reviews: [], page: 1, page_size: 20, total: 100, total_pages: 5 }
    """
    try:
        async with get_db_session() as db:
            # --- 1. Build WHERE clause and parameters ---
            where_clauses = []
            where_params = []
            param_index = 1
            
            if status and status != 'all':
                where_clauses.append(f"r.status = ${param_index}")
                where_params.append(status)
                param_index += 1
            
            if search:
                # Matches filename OR review summary
                where_clauses.append(f"(uf.filename ILIKE ${param_index} OR r.summary ILIKE ${param_index})")
                where_params.append(f"%{search}%")
                param_index += 1
            
            where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            # --- 2. Get total count ---
            count_query = f"""
                SELECT COUNT(DISTINCT r.id)
                FROM review_results r
                LEFT JOIN uploads u ON r.upload_id = u.id
                LEFT JOIN upload_files uf ON u.id = uf.upload_id
                {where_clause}
            """
            total = await db.fetchval(count_query, *where_params)
            
            # --- 3. Parse sort parameter ---
            sort_field = "r.created_at"
            sort_dir = "DESC"
            
            if sort == "created_desc":
                sort_field, sort_dir = "r.created_at", "DESC"
            elif sort == "created_asc":
                sort_field, sort_dir = "r.created_at", "ASC"
            elif sort == "status":
                sort_field, sort_dir = "r.status", "ASC" 
            elif sort == "score":
                sort_field, sort_dir = "r.overall_score", "DESC NULLS LAST"
            
            # --- 4. Get paginated data (Using explicit indices for LIMIT/OFFSET) ---
            offset = (page - 1) * page_size
            limit_index = param_index
            offset_index = param_index + 1
            
            data_query = f"""
                SELECT DISTINCT ON (r.id)
                    r.id,
                    r.upload_id,
                    r.overall_score,
                    r.summary,
                    r.model_used,
                    r.tokens_used,
                    r.processing_time_ms,
                    r.status,
                    r.error_message,
                    r.created_at,
                    r.completed_at,
                    u.language,
                    u.progress,
                    u.author_email,
                    uf.filename,
                    (SELECT COUNT(*) FROM review_suggestions WHERE review_result_id = r.id) as suggestion_count
                FROM review_results r
                LEFT JOIN uploads u ON r.upload_id = u.id
                LEFT JOIN upload_files uf ON u.id = uf.upload_id
                {where_clause}
                ORDER BY r.id, {sort_field} {sort_dir}
                LIMIT ${limit_index} OFFSET ${offset_index}
            """
            
            # Final parameter list: [where_params..., page_size, offset]
            final_params = where_params + [page_size, offset]
            
            rows = await db.fetch(data_query, *final_params)
            
            # --- 5. Format and return results ---
            reviews = []
            for row in rows:
                reviews.append({
                    "id": row["id"],
                    "upload_id": row["upload_id"],
                    "filename": row["filename"],
                    "language": row["language"],
                    "status": row["status"],
                    "overall_score": row["overall_score"],
                    "summary": row["summary"],
                    "model_used": row["model_used"],
                    "tokens_used": row["tokens_used"] or 0,
                    "processing_time_ms": row["processing_time_ms"] or 0,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                    "error_message": row["error_message"],
                    "suggestion_count": row["suggestion_count"] or 0,
                    "progress": row["progress"] or 0,
                    "author_email": row["author_email"]
                })
            
            # Calculate pagination
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            return {
                "reviews": reviews,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages
            }
            
    except Exception as e:
        logger.error("Failed to get reviews", error=str(e), status=status, search=search, sort=sort)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reviews: {str(e)}"
        )
    
@router.get("/reviews/stats")
async def get_review_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze")
):
    """
    Get review statistics (total, status counts, averages) for the last N days.
    """
    try:
        async with get_db_session() as db:
            # Calculate date range
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # $1 is used for the cutoff_date in all parts of the query
            stats_query = """
                SELECT 
                    COUNT(*) as total_reviews,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_reviews,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing_reviews,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_reviews,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_reviews,
                    AVG(overall_score) FILTER (WHERE overall_score IS NOT NULL) as average_score,
                    AVG(processing_time_ms) FILTER (WHERE processing_time_ms > 0) as average_processing_time_ms,
                    SUM(tokens_used) FILTER (WHERE tokens_used > 0) as total_tokens_used,
                    (SELECT COUNT(*) FROM review_suggestions rs 
                     JOIN review_results rr ON rs.review_result_id = rr.id 
                     WHERE rr.created_at >= $1) as total_suggestions
                FROM review_results
                WHERE created_at >= $1
            """
            
            row = await db.fetchrow(stats_query, cutoff_date)
            
            # If no data is returned, initialize to zeros
            if row is None:
                row = {k: 0 for k in ["total_reviews", "pending_reviews", "processing_reviews", 
                                      "completed_reviews", "failed_reviews", "total_suggestions", 
                                      "total_tokens_used", "average_score", "average_processing_time_ms"]}

            # Return stats object directly
            return {
                "period_days": days,
                "total_reviews": row["total_reviews"] or 0,
                "pending_reviews": row["pending_reviews"] or 0,
                "processing_reviews": row["processing_reviews"] or 0,
                "completed_reviews": row["completed_reviews"] or 0,
                "failed_reviews": row["failed_reviews"] or 0,
                "average_score": float(row["average_score"]) if row["average_score"] else None,
                "average_processing_time_ms": float(row["average_processing_time_ms"]) if row["average_processing_time_ms"] else None,
                "total_suggestions": row["total_suggestions"] or 0,
                "total_tokens_used": row["total_tokens_used"] or 0
            }
            
    except Exception as e:
        logger.error("Failed to get review stats", error=str(e), days=days)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review stats: {str(e)}"
        )


@router.get("/reviews/{review_id}")
async def get_review_by_id(review_id: int):
    """Get detailed review by ID with suggestions and file list"""
    try:
        async with get_db_session() as db:
            # --- 1. Get review with file info (use DISTINCT ON to ensure one row per review) ---
            review_query = """
                SELECT DISTINCT ON (r.id)
                    r.id,
                    r.upload_id,
                    r.overall_score,
                    r.summary,
                    r.model_used,
                    r.tokens_used,
                    r.processing_time_ms,
                    r.status,
                    r.error_message,
                    r.created_at,
                    r.completed_at,
                    u.language,
                    u.progress,
                    u.author_email,
                    u.description,
                    uf.filename -- Only one filename, but we fetch all files below
                FROM review_results r
                LEFT JOIN uploads u ON r.upload_id = u.id
                LEFT JOIN upload_files uf ON u.id = uf.upload_id
                WHERE r.id = $1
                ORDER BY r.id, uf.id -- Ordering by uf.id to ensure a deterministic primary filename
            """
            row = await db.fetchrow(review_query, review_id)
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Review not found"
                )
            
            # --- 2. Get suggestions ---
            suggestions_query = """
                SELECT 
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
                    END,
                    line_number ASC
            """
            suggestion_rows = await db.fetch(suggestions_query, review_id)
            
            suggestions = [
                {
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
            
            # --- 3. Get all files for the upload ---
            files_query = """
                SELECT filename, file_type, size_bytes, detected_language
                FROM upload_files
                WHERE upload_id = $1
            """
            files_rows = await db.fetch(files_query, row["upload_id"])
            
            files = [
                {
                    "filename": f["filename"],
                    "file_type": f["file_type"],
                    "size_bytes": f["size_bytes"],
                    "detected_language": f["detected_language"]
                }
                for f in files_rows
            ]
            
            # --- 4. Construct final response ---
            review = {
                "id": row["id"],
                "upload_id": row["upload_id"],
                "filename": row["filename"],
                "language": row["language"],
                "status": row["status"],
                "overall_score": row["overall_score"],
                "summary": row["summary"],
                "suggestions": suggestions,
                "model_used": row["model_used"],
                "tokens_used": row["tokens_used"] or 0,
                "processing_time_ms": row["processing_time_ms"] or 0,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "error_message": row["error_message"],
                "author_email": row["author_email"],
                "description": row["description"],
                "progress": row["progress"] or 0,
                "files": files
            }
            
            return {"review": review}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get review", review_id=review_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review: {str(e)}"
        )


@router.get("/reviews/upload/{upload_id}/status")
async def get_review_status(upload_id: str):
    """Get review status by upload_id"""
    try:
        async with get_db_session() as db:
            # --- 1. Check upload status ---
            upload_query = """
                SELECT 
                    id,
                    status,
                    progress,
                    created_at,
                    updated_at,
                    error_message
                FROM uploads 
                WHERE id = $1
            """
            upload = await db.fetchrow(upload_query, upload_id)
            
            if not upload:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Upload not found"
                )
            
            # --- 2. Check if review exists ---
            review_query = """
                SELECT id, status, created_at, completed_at
                FROM review_results 
                WHERE upload_id = $1 
                ORDER BY created_at DESC 
                LIMIT 1
            """
            review = await db.fetchrow(review_query, upload_id)
            
            return {
                "upload_id": upload_id,
                "status": upload["status"],
                "progress": upload["progress"] or 0,
                "review_id": review["id"] if review else None,
                "error_message": upload["error_message"],
                "created_at": upload["created_at"].isoformat() if upload["created_at"] else None,
                "updated_at": upload["updated_at"].isoformat() if upload["updated_at"] else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get review status", upload_id=upload_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review status: {str(e)}"
        )


@router.post("/reviews/upload/{upload_id}/cancel")
async def cancel_review(upload_id: str):
    """Cancel an ongoing review"""
    try:
        async with get_db_session() as db:
            update_query = """
                UPDATE uploads 
                SET status = 'cancelled', updated_at = NOW() 
                WHERE id = $1 AND status IN ('uploaded', 'processing')
                RETURNING status
            """
            result = await db.fetchval(update_query, upload_id)
            
            if not result:
                # Check if upload exists but is in a state that can't be cancelled
                check_query = "SELECT status FROM uploads WHERE id = $1"
                current_status = await db.fetchval(check_query, upload_id)

                if current_status is None:
                    detail = "Upload not found"
                    code = status.HTTP_404_NOT_FOUND
                elif current_status in ('completed', 'failed', 'cancelled'):
                    detail = f"Review is already in final state: '{current_status}'"
                    code = status.HTTP_400_BAD_REQUEST
                else:
                    detail = "Review cannot be cancelled (unknown reason)"
                    code = status.HTTP_400_BAD_REQUEST

                raise HTTPException(
                    status_code=code,
                    detail=detail
                )
            
            return {
                "message": "Review cancelled successfully",
                "upload_id": upload_id,
                "status": "cancelled"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel review", upload_id=upload_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel review: {str(e)}"
        )
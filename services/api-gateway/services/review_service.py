"""
API Gateway - Review Service
Handles review-related business logic and coordination
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import structlog
from pathlib import Path

from core.config import settings
from core.database import get_db_session
from services.kafka_producer import get_kafka_producer
from models.upload import ReviewStatus, UploadStatus

logger = structlog.get_logger(__name__)


class ReviewService:
    """Service for managing code review operations in API Gateway"""
    
    def __init__(self):
        self.kafka_producer = get_kafka_producer()
    
    async def initiate_review(self, upload_id: str, files_info: List[Dict], 
                            metadata: Dict) -> Dict:
        """
        Initiate a new code review by publishing to Kafka
        
        Args:
            upload_id: Unique upload identifier
            files_info: List of uploaded file information
            metadata: Additional metadata (language, author, etc.)
            
        Returns:
            Review initiation result with review ID and status
        """
        try:
            logger.info(
                "Initiating code review",
                upload_id=upload_id,
                file_count=len(files_info)
            )
            
            # Create review record in database
            async with get_db_session() as db:
                review_id = await self._create_review_record(
                    db, upload_id, files_info, metadata
                )
            
            # Prepare Kafka event
            event_data = {
                "upload_id": upload_id,
                "review_id": review_id,
                "files": files_info,
                "metadata": metadata,
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "code_upload"
            }
            
            # Publish to Kafka for AI processing
            await self.kafka_producer.publish_code_upload(event_data)
            
            logger.info(
                "Review initiated successfully",
                upload_id=upload_id,
                review_id=review_id
            )
            
            return {
                "review_id": review_id,
                "upload_id": upload_id,
                "status": "pending",
                "message": "Review initiated successfully",
                "estimated_completion_time": self._estimate_completion_time(files_info)
            }
            
        except Exception as e:
            logger.error(
                "Failed to initiate review",
                upload_id=upload_id,
                error=str(e)
            )
            raise
    
    async def get_review_status(self, review_id: int) -> Dict:
        """
        Get current status of a review
        
        Args:
            review_id: Review identifier
            
        Returns:
            Review status information
        """
        try:
            async with get_db_session() as db:
                query = """
                    SELECT r.id, r.upload_id, r.status, r.overall_score, 
                           r.summary, r.created_at, r.completed_at, 
                           r.error_message, r.processing_time_ms,
                           r.tokens_used, r.model_used,
                           COUNT(s.id) as suggestions_count
                    FROM review_results r
                    LEFT JOIN review_suggestions s ON s.review_result_id = r.id
                    WHERE r.id = $1
                    GROUP BY r.id
                """
                
                row = await db.fetchrow(query, review_id)
                
                if not row:
                    return {
                        "review_id": review_id,
                        "status": "not_found",
                        "error": "Review not found"
                    }
                
                # Calculate progress percentage
                progress = self._calculate_progress(row["status"], row["completed_at"])
                
                result = {
                    "review_id": row["id"],
                    "upload_id": row["upload_id"],
                    "status": row["status"],
                    "progress": progress,
                    "created_at": row["created_at"],
                    "completed_at": row["completed_at"],
                    "overall_score": row["overall_score"],
                    "summary": row["summary"],
                    "suggestions_count": row["suggestions_count"],
                    "processing_time_ms": row["processing_time_ms"],
                    "tokens_used": row["tokens_used"],
                    "model_used": row["model_used"],
                    "error_message": row["error_message"]
                }
                
                return result
                
        except Exception as e:
            logger.error("Failed to get review status", review_id=review_id, error=str(e))
            raise
    
    async def get_review_results(self, review_id: int, 
                                include_suggestions: bool = True) -> Dict:
        """
        Get complete review results with suggestions
        
        Args:
            review_id: Review identifier
            include_suggestions: Whether to include detailed suggestions
            
        Returns:
            Complete review results
        """
        try:
            async with get_db_session() as db:
                # Get review data
                review_query = """
                    SELECT r.*, u.author_email, u.file_count, u.total_size_bytes
                    FROM review_results r
                    LEFT JOIN uploads u ON u.id = r.upload_id
                    WHERE r.id = $1
                """
                
                review_row = await db.fetchrow(review_query, review_id)
                
                if not review_row:
                    raise ValueError(f"Review {review_id} not found")
                
                result = {
                    "review_id": review_row["id"],
                    "upload_id": review_row["upload_id"],
                    "status": review_row["status"],
                    "overall_score": review_row["overall_score"],
                    "summary": review_row["summary"],
                    "model_used": review_row["model_used"],
                    "tokens_used": review_row["tokens_used"],
                    "processing_time_ms": review_row["processing_time_ms"],
                    "created_at": review_row["created_at"],
                    "completed_at": review_row["completed_at"],
                    "error_message": review_row["error_message"],
                    "author_email": review_row["author_email"],
                    "file_count": review_row["file_count"],
                    "total_size_bytes": review_row["total_size_bytes"]
                }
                
                # Get suggestions if requested
                if include_suggestions:
                    suggestions_query = """
                        SELECT id, file_path, line_number, suggestion_type,
                               severity, title, description, suggested_fix,
                               confidence_score
                        FROM review_suggestions
                        WHERE review_result_id = $1
                        ORDER BY severity DESC, line_number ASC
                    """
                    
                    suggestion_rows = await db.fetch(suggestions_query, review_id)
                    
                    result["suggestions"] = [
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
                    
                    # Group suggestions by severity
                    result["suggestions_by_severity"] = self._group_by_severity(
                        result["suggestions"]
                    )
                
                return result
                
        except Exception as e:
            logger.error(
                "Failed to get review results",
                review_id=review_id,
                error=str(e)
            )
            raise
    
    async def get_reviews_by_upload(self, upload_id: str) -> List[Dict]:
        """
        Get all reviews associated with an upload
        
        Args:
            upload_id: Upload identifier
            
        Returns:
            List of reviews for the upload
        """
        try:
            async with get_db_session() as db:
                query = """
                    SELECT r.id, r.status, r.overall_score, r.summary,
                           r.created_at, r.completed_at, r.error_message,
                           COUNT(s.id) as suggestions_count
                    FROM review_results r
                    LEFT JOIN review_suggestions s ON s.review_result_id = r.id
                    WHERE r.upload_id = $1
                    GROUP BY r.id
                    ORDER BY r.created_at DESC
                """
                
                rows = await db.fetch(query, upload_id)
                
                return [
                    {
                        "review_id": row["id"],
                        "status": row["status"],
                        "overall_score": row["overall_score"],
                        "summary": row["summary"],
                        "created_at": row["created_at"],
                        "completed_at": row["completed_at"],
                        "error_message": row["error_message"],
                        "suggestions_count": row["suggestions_count"]
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(
                "Failed to get reviews by upload",
                upload_id=upload_id,
                error=str(e)
            )
            raise
    
    async def cancel_review(self, review_id: int) -> Dict:
        """
        Cancel a pending or in-progress review
        
        Args:
            review_id: Review identifier
            
        Returns:
            Cancellation result
        """
        try:
            async with get_db_session() as db:
                # Check current status
                current_status = await db.fetchval(
                    "SELECT status FROM review_results WHERE id = $1",
                    review_id
                )
                
                if not current_status:
                    raise ValueError(f"Review {review_id} not found")
                
                if current_status in ["completed", "failed", "cancelled"]:
                    return {
                        "review_id": review_id,
                        "status": "cannot_cancel",
                        "message": f"Review is already {current_status}"
                    }
                
                # Update status to cancelled
                await db.execute(
                    """
                    UPDATE review_results 
                    SET status = 'cancelled', completed_at = NOW()
                    WHERE id = $1
                    """,
                    review_id
                )
                
                # Update associated upload
                await db.execute(
                    """
                    UPDATE uploads 
                    SET status = 'cancelled', updated_at = NOW()
                    WHERE id = (SELECT upload_id FROM review_results WHERE id = $1)
                    """,
                    review_id
                )
                
                logger.info("Review cancelled", review_id=review_id)
                
                return {
                    "review_id": review_id,
                    "status": "cancelled",
                    "message": "Review cancelled successfully",
                    "cancelled_at": datetime.utcnow()
                }
                
        except Exception as e:
            logger.error("Failed to cancel review", review_id=review_id, error=str(e))
            raise
    
    async def retry_failed_review(self, review_id: int) -> Dict:
        """
        Retry a failed review
        
        Args:
            review_id: Review identifier
            
        Returns:
            Retry result with new review information
        """
        try:
            async with get_db_session() as db:
                # Get original review data
                query = """
                    SELECT r.upload_id, u.author_email, u.file_count
                    FROM review_results r
                    JOIN uploads u ON u.id = r.upload_id
                    WHERE r.id = $1 AND r.status = 'failed'
                """
                
                row = await db.fetchrow(query, review_id)
                
                if not row:
                    raise ValueError(
                        f"Review {review_id} not found or not in failed state"
                    )
                
                upload_id = row["upload_id"]
                
                # Get file information
                files_query = """
                    SELECT filename, filepath, size_bytes, language
                    FROM uploaded_files
                    WHERE upload_id = $1
                """
                
                file_rows = await db.fetch(files_query, upload_id)
                
                files_info = [
                    {
                        "filename": f["filename"],
                        "filepath": f["filepath"],
                        "size": f["size_bytes"],
                        "language": f["language"]
                    }
                    for f in file_rows
                ]
                
                metadata = {
                    "author_email": row["author_email"],
                    "retry_of": review_id,
                    "retry_timestamp": datetime.utcnow().isoformat()
                }
                
                # Create new review
                new_review = await self.initiate_review(
                    upload_id, files_info, metadata
                )
                
                logger.info(
                    "Review retry initiated",
                    original_review_id=review_id,
                    new_review_id=new_review["review_id"]
                )
                
                return {
                    "original_review_id": review_id,
                    "new_review_id": new_review["review_id"],
                    "status": "retry_initiated",
                    "message": "Review retry initiated successfully"
                }
                
        except Exception as e:
            logger.error("Failed to retry review", review_id=review_id, error=str(e))
            raise
    
    async def get_review_statistics(self, days: int = 7) -> Dict:
        """
        Get review statistics for the specified period
        
        Args:
            days: Number of days to include in statistics
            
        Returns:
            Statistical summary of reviews
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            async with get_db_session() as db:
                stats_query = """
                    SELECT 
                        COUNT(*) as total_reviews,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed,
                        COUNT(*) FILTER (WHERE status = 'failed') as failed,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending,
                        COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled,
                        AVG(overall_score) FILTER (WHERE overall_score IS NOT NULL) as avg_score,
                        AVG(processing_time_ms) FILTER (WHERE processing_time_ms > 0) as avg_time,
                        SUM(tokens_used) as total_tokens
                    FROM review_results
                    WHERE created_at >= $1
                """
                
                stats_row = await db.fetchrow(stats_query, since_date)
                
                return {
                    "period_days": days,
                    "since_date": since_date,
                    "total_reviews": stats_row["total_reviews"] or 0,
                    "completed": stats_row["completed"] or 0,
                    "failed": stats_row["failed"] or 0,
                    "pending": stats_row["pending"] or 0,
                    "cancelled": stats_row["cancelled"] or 0,
                    "success_rate": round(
                        (stats_row["completed"] or 0) / (stats_row["total_reviews"] or 1) * 100, 
                        2
                    ),
                    "average_score": round(float(stats_row["avg_score"] or 0), 2),
                    "average_processing_time_ms": round(
                        float(stats_row["avg_time"] or 0), 
                        2
                    ),
                    "total_tokens_used": stats_row["total_tokens"] or 0
                }
                
        except Exception as e:
            logger.error("Failed to get review statistics", error=str(e))
            raise
    
    # Private helper methods
    
    async def _create_review_record(self, db, upload_id: str, 
                                   files_info: List[Dict], metadata: Dict) -> int:
        """Create initial review record in database"""
        query = """
            INSERT INTO review_results (
                upload_id, status, model_used, created_at
            ) VALUES ($1, 'pending', $2, NOW())
            RETURNING id
        """
        
        review_id = await db.fetchval(
            query,
            upload_id,
            settings.OPENAI_MODEL
        )
        
        return review_id
    
    def _estimate_completion_time(self, files_info: List[Dict]) -> str:
        """Estimate review completion time based on file count and size"""
        total_size = sum(f.get("size", 0) for f in files_info)
        file_count = len(files_info)
        
        # Rough estimation: 10 seconds base + 5 seconds per file + 1 second per 10KB
        estimated_seconds = 10 + (file_count * 5) + (total_size // 10240)
        
        # Cap at reasonable maximum
        estimated_seconds = min(estimated_seconds, 300)  # Max 5 minutes
        
        return f"{estimated_seconds} seconds"
    
    def _calculate_progress(self, status: str, completed_at: Optional[datetime]) -> int:
        """Calculate review progress percentage"""
        if status == "completed":
            return 100
        elif status == "pending":
            return 10
        elif status == "processing":
            return 50
        elif status in ["failed", "cancelled"]:
            return 0
        else:
            return 0
    
    def _group_by_severity(self, suggestions: List[Dict]) -> Dict:
        """Group suggestions by severity level"""
        grouped = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for suggestion in suggestions:
            severity = suggestion.get("severity", "low")
            if severity in grouped:
                grouped[severity].append(suggestion)
        
        return {
            severity: {
                "count": len(items),
                "suggestions": items
            }
            for severity, items in grouped.items()
        }


# Singleton instance
_review_service = None

def get_review_service() -> ReviewService:
    """Get or create ReviewService singleton"""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service
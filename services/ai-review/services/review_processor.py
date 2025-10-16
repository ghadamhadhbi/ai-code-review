"""
AI Review Service - Review Processor - FIXED VERSION
Processes code uploads and publishes results to Kafka
"""

import asyncio
import aiofiles
import os
from datetime import datetime
from typing import Dict, List, Optional
import structlog

from core.config import settings
from core.ai_client import get_ai_client
from core.database import get_db_session
from services.kafka_producer import get_kafka_producer

logger = structlog.get_logger(__name__)


class ReviewProcessor:
    """Main processor for code reviews"""
    
    def __init__(self):
        self.ai_client = get_ai_client()
        self.kafka_producer = get_kafka_producer()
    
    async def process_upload(self, upload_data: Dict) -> bool:
        """
        Process an upload and perform AI code review
        
        Args:
            upload_data: Upload event data from Kafka
            
        Returns:
            True if processing successful, False otherwise
        """
        upload_id = upload_data.get("upload_id")
        
        try:
            logger.info("🔄 Processing code upload", upload_id=upload_id, file_count=len(upload_data.get("files", [])))
            
            # Update status to processing
            async with get_db_session() as db:
                await self._update_upload_status(db, upload_id, "processing", progress=10)
            
            # Create review record
            async with get_db_session() as db:
                review_id = await self._create_review_record(db, upload_data)
            
            logger.info("✅ Review record created", review_id=review_id, upload_id=upload_id)
            
            # ✅ FIX: Publish status update
            await self.kafka_producer.publish_status_update(
                upload_id=upload_id,
                status="processing",
                progress=20,
                message="Loading files..."
            )
            
            # Load file contents
            files_data = await self._load_file_contents(upload_data.get("files", []))
            
            if not files_data:
                raise Exception("No valid files found for review")
            
            # ✅ FIX: Publish progress update
            await self.kafka_producer.publish_status_update(
                upload_id=upload_id,
                status="processing",
                progress=50,
                message="Analyzing code with AI..."
            )
            
            # Perform AI analysis
            logger.info("🤖 Starting AI analysis", upload_id=upload_id)
            start_time = datetime.utcnow()
            
            ai_result = await self.ai_client.analyze_code(files_data, {
                "language": upload_data.get("language"),
                "description": upload_data.get("description"),
                "author_email": upload_data.get("author_email")
            })
            
            processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            ai_result["processing_time_ms"] = processing_time_ms
            
            logger.info(
                "🎯 AI analysis completed",
                upload_id=upload_id,
                processing_time_ms=processing_time_ms,
                overall_score=ai_result.get("overall_score"),
                suggestions_count=len(ai_result.get("suggestions", []))
            )
            
            # Save review results
            async with get_db_session() as db:
                await self._save_review_results(db, review_id, ai_result)
                await self._update_upload_status(db, upload_id, "completed", progress=100)
            
            # ✅ FIX: Publish completion event with all data
            await self.kafka_producer.publish_review_result({
                "upload_id": upload_id,
                "review_id": review_id,
                "overall_score": ai_result.get("overall_score"),
                "summary": ai_result.get("summary"),
                "suggestions": ai_result.get("suggestions", []),
                "tokens_used": ai_result.get("tokens_used", 0),
                "processing_time_ms": processing_time_ms,
                "model_used": ai_result.get("model_used")
            })
            
            logger.info(
                "📤 Published review completion",
                upload_id=upload_id,
                review_id=review_id,
                overall_score=ai_result.get("overall_score")
            )
            
            # Clean up temporary files
            await self._cleanup_temp_files(upload_data.get("files", []))
            
            logger.info(
                "✅ Code upload processed successfully",
                upload_id=upload_id,
                review_id=review_id,
                overall_score=ai_result.get("overall_score"),
                suggestions_count=len(ai_result.get("suggestions", []))
            )
            
            return True
            
        except Exception as e:
            logger.error("❌ Review processing failed", upload_id=upload_id, error=str(e))
            
            # Update status to failed
            try:
                async with get_db_session() as db:
                    await self._update_upload_status(db, upload_id, "failed", error_message=str(e))
                
                # ✅ FIX: Publish failure event
                await self.kafka_producer.publish_review_failed(upload_id, str(e))
                
            except Exception as db_error:
                logger.error("Failed to update upload status", error=str(db_error))
            
            return False
    
    async def _load_file_contents(self, files_info: List[Dict]) -> List[Dict]:
        """Load file contents from disk"""
        files_data = []
        
        for file_info in files_info:
            try:
                filepath = file_info.get("filepath")
                filename = file_info.get("filename")
                
                if not filepath or not filename:
                    logger.warning("Missing file path or name", file_info=file_info)
                    continue
                
                # Check if file exists
                if not os.path.exists(filepath):
                    logger.warning("File not found", filepath=filepath)
                    continue
                
                # Read file content
                try:
                    async with aiofiles.open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = await f.read()
                except Exception as read_error:
                    logger.error("Failed to read file", filepath=filepath, error=str(read_error))
                    continue
                
                # Skip empty files
                if not content.strip():
                    logger.warning("Skipping empty file", filename=filename)
                    continue
                
                # Truncate very large files
                max_size = 100000  # 100KB
                if len(content) > max_size:
                    logger.warning("Truncating large file", filename=filename, size=len(content))
                    content = content[:max_size]
                    content += f"\n\n... (truncated, original size: {len(content)} chars)"
                
                files_data.append({
                    "filename": filename,
                    "content": content,
                    "size": len(content),
                    "language": file_info.get("detected_language") or file_info.get("language"),
                    "file_type": file_info.get("file_type")
                })
                
            except Exception as e:
                logger.error("Failed to load file content", filename=file_info.get("filename"), error=str(e))
                continue
        
        logger.info("Loaded file contents", count=len(files_data))
        return files_data
    
    async def _create_review_record(self, db, upload_data: Dict) -> int:
        """Create initial review record"""
        model_name = getattr(settings, 'GROQ_MODEL', 'llama-3.1-8b-instant')
        
        query = """
            INSERT INTO review_results (
                upload_id, status, model_used, created_at
            ) VALUES ($1, 'pending', $2, NOW())
            RETURNING id
        """
        
        review_id = await db.fetchval(
            query,
            upload_data.get("upload_id"),
            model_name
        )
        
        return review_id
    
    async def _save_review_results(self, db, review_id: int, ai_result: Dict):
        """Save AI analysis results to database"""
        # Update review record
        update_query = """
            UPDATE review_results 
            SET overall_score = $2,
                summary = $3,
                tokens_used = $4,
                processing_time_ms = $5,
                status = 'completed',
                completed_at = NOW()
            WHERE id = $1
        """
        
        await db.execute(
            update_query,
            review_id,
            ai_result.get("overall_score"),
            ai_result.get("summary"),
            ai_result.get("tokens_used", 0),
            ai_result.get("processing_time_ms", 0)
        )
        
        # Insert suggestions
        suggestions = ai_result.get("suggestions", [])
        if suggestions:
            suggestion_query = """
                INSERT INTO review_suggestions (
                    review_result_id, file_path, line_number, suggestion_type,
                    severity, title, description, suggested_fix, confidence_score
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """
            
            for suggestion in suggestions:
                try:
                    await db.execute(
                        suggestion_query,
                        review_id,
                        suggestion.get("file_path", "unknown"),
                        suggestion.get("line_number"),
                        suggestion.get("suggestion_type", "other"),
                        suggestion.get("severity", "low"),
                        suggestion.get("title", "Issue detected"),
                        suggestion.get("description", "No description provided"),
                        suggestion.get("suggested_fix"),
                        suggestion.get("confidence_score", 75)
                    )
                except Exception as e:
                    logger.error("Failed to insert suggestion", error=str(e))
                    continue
        
        logger.info("Saved review results", review_id=review_id, suggestions_count=len(suggestions))
    
    async def _update_upload_status(self, db, upload_id: str, status: str, 
                                   error_message: Optional[str] = None,
                                   progress: Optional[int] = None):
        """Update upload status"""
        query = """
            UPDATE uploads 
            SET status = $2, 
                updated_at = NOW(), 
                error_message = $3,
                progress = COALESCE($4, progress)
            WHERE id = $1
        """
        
        await db.execute(query, upload_id, status, error_message, progress)
    
    async def _cleanup_temp_files(self, files_info: List[Dict]):
        """Clean up temporary files after processing"""
        for file_info in files_info:
            try:
                filepath = file_info.get("filepath")
                if filepath and os.path.exists(filepath):
                    os.remove(filepath)
                    logger.debug("Cleaned up temp file", filepath=filepath)
            except Exception as e:
                logger.warning("Failed to clean up temp file", filepath=filepath, error=str(e))


# Singleton instance
_review_processor_instance = None


def get_review_processor() -> ReviewProcessor:
    """Get singleton ReviewProcessor instance"""
    global _review_processor_instance
    if _review_processor_instance is None:
        _review_processor_instance = ReviewProcessor()
    return _review_processor_instance
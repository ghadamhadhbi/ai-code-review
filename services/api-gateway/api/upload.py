"""
Upload API endpoints
Handles file uploads and triggers AI code review
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import structlog
import asyncio
import uuid
import os
import json
from datetime import datetime

from core.config import settings
from core.kafka_producer import KafkaProducer
from core.database import get_db_session
from models.upload import UploadRequest, UploadResponse, FileInfo
from services.file_service import FileService
from utils.validators import validate_files
from core.exceptions import ValidationError, ProcessingError

logger = structlog.get_logger(__name__)
router = APIRouter()

# Initialize services
file_service = FileService()
kafka_producer = KafkaProducer()


@router.post("/", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(..., description="Code files to analyze"),
    author_email: Optional[str] = Form(None, description="Author email for notifications"),
    description: Optional[str] = Form(None, description="Review description"),
    language: Optional[str] = Form(None, description="Primary programming language"),
    db_session = Depends(get_db_session)
) -> UploadResponse:
    """
    Upload code files for AI review analysis
    
    - **files**: List of code files (max 10 files, 5MB each)
    - **author_email**: Email for notifications (optional)
    - **description**: Description of the code review (optional)
    - **language**: Primary programming language (optional)
    
    Returns upload session ID and status
    """
    upload_id = str(uuid.uuid4())
    
    logger.info(
        "File upload started",
        upload_id=upload_id,
        file_count=len(files),
        author_email=author_email,
    )
    
    try:
        # Validate upload request
        validate_files(files, settings)
        
        # Process uploaded files
        processed_files = []
        total_size = 0
        
        for file in files:
            # Validate individual file
            if not file.filename:
                raise ValidationError("File must have a filename")
            
            file_info = await file_service.process_upload_file(file, upload_id)
            processed_files.append(file_info)
            total_size += file_info.size_bytes
            
            logger.debug(
                "File processed",
                upload_id=upload_id,
                filename=file_info.filename,
                size=file_info.size_bytes,
            )
        
        # Store upload record in database
        upload_record = await _create_upload_record(
            db_session=db_session,
            upload_id=upload_id,
            files=processed_files,
            author_email=author_email,
            description=description,
            language=language,
            total_size=total_size
        )
        
        # Prepare Kafka event
        upload_event = {
            "upload_id": upload_id,
            "timestamp": datetime.utcnow().isoformat(),
            "author_email": author_email,
            "description": description,
            "language": language,
            "files": [
                {
                    "filename": f.filename,
                    "filepath": f.filepath,
                    "size_bytes": f.size_bytes,
                    "extension": f.extension,
                    "content_type": f.content_type,
                    "language": f.detected_language,
                }
                for f in processed_files
            ],
            "total_size_bytes": total_size,
            "file_count": len(processed_files),
        }
        
        # Publish to Kafka
        await kafka_producer.publish_upload_event(upload_event)
        
        logger.info(
            "Upload completed successfully",
            upload_id=upload_id,
            file_count=len(processed_files),
            total_size=total_size,
        )
        
        # Return success response
        return UploadResponse(
            upload_id=upload_id,
            status="uploaded",
            message="Files uploaded successfully and queued for review",
            file_count=len(processed_files),
            total_size_bytes=total_size,
            files=[
                FileInfo(
                    filename=f.filename,
                    size_bytes=f.size_bytes,
                    extension=f.extension,
                    content_type=f.content_type,
                    detected_language=f.detected_language,
                )
                for f in processed_files
            ],
            estimated_processing_time=_estimate_processing_time(processed_files),
        )
        
    except ValidationError as e:
        logger.warning(
            "Upload validation failed",
            upload_id=upload_id,
            error=e.message,
        )
        # Cleanup any partial files
        await file_service.cleanup_upload(upload_id)
        raise HTTPException(status_code=400, detail=e.message)
        
    except ProcessingError as e:
        logger.error(
            "Upload processing failed",
            upload_id=upload_id,
            error=e.message,
        )
        # Cleanup any partial files
        await file_service.cleanup_upload(upload_id)
        raise HTTPException(status_code=500, detail=e.message)
        
    except Exception as e:
        logger.error(
            "Unexpected upload error",
            upload_id=upload_id,
            error=str(e),
        )
        # Cleanup any partial files
        await file_service.cleanup_upload(upload_id)
        raise HTTPException(status_code=500, detail="Upload processing failed")


@router.get("/status/{upload_id}")
async def get_upload_status(
    upload_id: str,
    db_session = Depends(get_db_session)
):
    """
    Get the status of an upload and its review progress
    
    - **upload_id**: The upload session ID
    
    Returns current status and progress information
    """
    try:
        # Query database for upload status
        upload_record = await _get_upload_record(db_session, upload_id)
        
        if not upload_record:
            raise HTTPException(
                status_code=404,
                detail=f"Upload {upload_id} not found"
            )
        
        return {
            "upload_id": upload_id,
            "status": upload_record["status"],
            "created_at": upload_record["created_at"],
            "updated_at": upload_record["updated_at"],
            "file_count": upload_record["file_count"],
            "total_size_bytes": upload_record["total_size_bytes"],
            "progress": upload_record.get("progress", 0),
            "error_message": upload_record.get("error_message"),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get upload status", upload_id=upload_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve upload status")


@router.delete("/{upload_id}")
async def cancel_upload(
    upload_id: str,
    db_session = Depends(get_db_session)
):
    """
    Cancel an upload and cleanup associated files
    
    - **upload_id**: The upload session ID to cancel
    
    Returns confirmation of cancellation
    """
    try:
        # Check if upload exists and is cancellable
        upload_record = await _get_upload_record(db_session, upload_id)
        
        if not upload_record:
            raise HTTPException(
                status_code=404,
                detail=f"Upload {upload_id} not found"
            )
        
        if upload_record["status"] in ["completed", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel upload with status: {upload_record['status']}"
            )
        
        # Update status to cancelled
        await _update_upload_status(db_session, upload_id, "cancelled")
        
        # Cleanup files
        await file_service.cleanup_upload(upload_id)
        
        logger.info("Upload cancelled", upload_id=upload_id)
        
        return {
            "upload_id": upload_id,
            "status": "cancelled",
            "message": "Upload cancelled and files cleaned up"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel upload", upload_id=upload_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to cancel upload")


# Helper functions

async def _create_upload_record(db_session, upload_id: str, files: List, 
                               author_email: Optional[str], description: Optional[str],
                               language: Optional[str], total_size: int) -> dict:
    """Create upload record in database"""
    query = """
        INSERT INTO uploads (
            id, author_email, description, language, 
            file_count, total_size_bytes, status, created_at
        ) VALUES (
            :id, :author_email, :description, :language,
            :file_count, :total_size_bytes, 'uploaded', NOW()
        )
    """
    
    await db_session.execute(query, {
        "id": upload_id,
        "author_email": author_email,
        "description": description,
        "language": language,
        "file_count": len(files),
        "total_size_bytes": total_size,
    })
    await db_session.commit()
    
    return {
        "upload_id": upload_id,
        "status": "uploaded",
        "file_count": len(files),
        "total_size_bytes": total_size,
    }


async def _get_upload_record(db_session, upload_id: str) -> Optional[dict]:
    """Get upload record from database"""
    query = """
        SELECT id, status, created_at, updated_at, file_count, 
               total_size_bytes, error_message
        FROM uploads WHERE id = :upload_id
    """
    
    result = await db_session.execute(query, {"upload_id": upload_id})
    row = result.fetchone()
    
    if row:
        return dict(row)
    return None


async def _update_upload_status(db_session, upload_id: str, status: str, 
                               error_message: Optional[str] = None):
    """Update upload status in database"""
    query = """
        UPDATE uploads 
        SET status = :status, updated_at = NOW(), error_message = :error_message
        WHERE id = :upload_id
    """
    
    await db_session.execute(query, {
        "upload_id": upload_id,
        "status": status,
        "error_message": error_message,
    })
    await db_session.commit()


def _estimate_processing_time(files: List) -> int:
    """Estimate processing time based on file count and size"""
    base_time = 10  # Base processing time in seconds
    file_time = len(files) * 5  # 5 seconds per file
    
    total_size_mb = sum(f.size_bytes for f in files) / (1024 * 1024)
    size_time = int(total_size_mb * 2)  # 2 seconds per MB
    
    return base_time + file_time + size_time
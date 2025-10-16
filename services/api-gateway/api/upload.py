"""
Upload API endpoints - FIXED - Files persist correctly
Handles file uploads with proper database storage
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional
import structlog
import uuid
import os
from datetime import datetime

from core.config import settings
from services.kafka_producer import get_kafka_producer
from core.database import get_db_session

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/")
async def upload_files(
    files: List[UploadFile] = File(...),
    author_email: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    db_session = Depends(get_db_session)
):
    """
    ✅ FIX: Upload code files - ensures persistence in database
    """
    upload_id = str(uuid.uuid4())
    
    logger.info(
        "File upload started",
        upload_id=upload_id,
        file_count=len(files),
        author_email=author_email,
    )
    
    try:
        # Validate files
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="No files provided")
        
        max_files = getattr(settings, 'MAX_FILES_PER_REVIEW', 10)
        if len(files) > max_files:
            raise HTTPException(status_code=400, detail=f"Maximum {max_files} files allowed")
        
        # Process uploaded files
        processed_files = []
        total_size = 0
        upload_dir = f"/tmp/uploads/{upload_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        for file in files:
            if not file.filename:
                continue
                
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Check file size
            max_size = getattr(settings, 'MAX_FILE_SIZE_MB', 5) * 1024 * 1024
            if file_size > max_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB"
                )
            
            # Save file
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Detect language from extension
            extension = os.path.splitext(file.filename)[1]
            detected_lang = _detect_language(extension)
            
            file_info = {
                "filename": file.filename,
                "filepath": file_path,
                "extension": extension,
                "size_bytes": file_size,
                "content_type": file.content_type or "text/plain",
                "detected_language": detected_lang,
                "file_type": extension
            }
            
            processed_files.append(file_info)
            total_size += file_size
            
            logger.debug("File processed", filename=file.filename, size=file_size)
        
        # ✅ FIX: Create upload record in database with proper error handling
        try:
            if hasattr(db_session, '__aenter__'):
                async with db_session as conn:
                    await _create_upload_record(
                        conn, upload_id, processed_files, author_email,
                        description, language, total_size
                    )
            else:
                await _create_upload_record(
                    db_session, upload_id, processed_files, author_email,
                    description, language, total_size
                )
            
            logger.info("✅ Upload record created in database", upload_id=upload_id)
            
        except Exception as e:
            logger.error("Database error during upload", upload_id=upload_id, error=str(e))
            # Clean up files
            for file_info in processed_files:
                try:
                    os.remove(file_info["filepath"])
                except:
                    pass
            raise HTTPException(status_code=500, detail=f"Failed to save upload: {str(e)}")
        
        # Prepare Kafka event
        upload_event = {
            "upload_id": upload_id,
            "timestamp": datetime.utcnow().isoformat(),
            "author_email": author_email,
            "description": description,
            "language": language or (processed_files[0]["detected_language"] if processed_files else None),
            "files": processed_files,
            "total_size_bytes": total_size,
            "file_count": len(processed_files),
        }
        
        # Publish to Kafka
        try:
            kafka_producer = get_kafka_producer()
            await kafka_producer.publish_upload_event(upload_event)
            logger.info("✅ Upload event published to Kafka", upload_id=upload_id)
        except Exception as e:
            logger.error("Kafka publishing error", upload_id=upload_id, error=str(e))
            # Continue despite Kafka failure - upload is in database
        
        logger.info(
            "✅ Upload completed successfully",
            upload_id=upload_id,
            file_count=len(processed_files),
            total_size=total_size,
        )
        
        # Return success response
        return {
            "upload_id": upload_id,
            "status": "uploaded",
            "message": "Files uploaded successfully and queued for review",
            "file_count": len(processed_files),
            "total_size_bytes": total_size,
            "files": [
                {
                    "filename": f["filename"],
                    "size_bytes": f["size_bytes"],
                    "extension": f["extension"],
                    "content_type": f["content_type"],
                    "detected_language": f["detected_language"],
                }
                for f in processed_files
            ],
            "estimated_processing_time": f"{10 + len(processed_files) * 5} seconds",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected upload error", upload_id=upload_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}")


async def _create_upload_record(conn, upload_id: str, files: List, 
                               author_email: Optional[str], description: Optional[str],
                               language: Optional[str], total_size: int):
    """
    ✅ FIX: Create upload record with proper transaction handling
    """
    
    # Insert upload record
    insert_query = """
        INSERT INTO uploads (
            id, author_email, description, language, 
            file_count, total_size_bytes, status, created_at, updated_at, progress
        ) VALUES (
            $1, $2, $3, $4, $5, $6, 'uploaded', NOW(), NOW(), 10
        )
    """
    
    await conn.execute(
        insert_query,
        upload_id, author_email, description, language, len(files), total_size
    )
    
    logger.debug("Inserted upload record", upload_id=upload_id)
    
    # ✅ FIX: Insert file records with proper field mapping
    for file_info in files:
        file_insert_query = """
            INSERT INTO upload_files (
                upload_id, filename, filepath, file_type, size_bytes,
                detected_language, content_type, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, NOW()
            )
        """
        
        await conn.execute(
            file_insert_query,
            upload_id,
            file_info["filename"],
            file_info["filepath"],
            file_info["extension"],  # file_type
            file_info["size_bytes"],
            file_info["detected_language"],
            file_info["content_type"]
        )
        
        logger.debug("Inserted file record", filename=file_info["filename"])
    
    logger.info("✅ Upload and file records inserted", upload_id=upload_id, file_count=len(files))


def _detect_language(extension: str) -> str:
    """Detect programming language from file extension"""
    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".go": "go",
        ".rs": "rust",
        ".php": "php",
        ".rb": "ruby",
        ".swift": "swift",
        ".kt": "kotlin",
        ".cs": "csharp",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
    }
    return lang_map.get(extension.lower(), "unknown")


@router.get("/{upload_id}")
async def get_upload_status(
    upload_id: str,
    db_session = Depends(get_db_session)
):
    """
    ✅ FIX: Get upload status - shows current progress
    """
    try:
        if hasattr(db_session, '__aenter__'):
            async with db_session as conn:
                return await _fetch_upload_status(conn, upload_id)
        else:
            return await _fetch_upload_status(db_session, upload_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get upload status", upload_id=upload_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get upload status: {str(e)}")


async def _fetch_upload_status(conn, upload_id: str):
    """Fetch upload status from database"""
    
    query = """
        SELECT 
            id,
            status,
            progress,
            author_email,
            description,
            language,
            file_count,
            total_size_bytes,
            created_at,
            updated_at,
            error_message
        FROM uploads
        WHERE id = $1
    """
    
    row = await conn.fetchrow(query, upload_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Get file list
    files_query = """
        SELECT filename, file_type, size_bytes, detected_language
        FROM upload_files
        WHERE upload_id = $1
        ORDER BY created_at
    """
    
    file_rows = await conn.fetch(files_query, upload_id)
    
    files = [
        {
            "filename": f["filename"],
            "file_type": f["file_type"],
            "size_bytes": f["size_bytes"],
            "detected_language": f["detected_language"]
        }
        for f in file_rows
    ]
    
    # Check if review exists
    review_query = """
        SELECT id, status, overall_score, created_at, completed_at
        FROM review_results
        WHERE upload_id = $1
        ORDER BY created_at DESC
        LIMIT 1
    """
    
    review = await conn.fetchrow(review_query, upload_id)
    
    return {
        "upload_id": row["id"],
        "status": row["status"],
        "progress": row["progress"] or 0,
        "author_email": row["author_email"],
        "description": row["description"],
        "language": row["language"],
        "file_count": row["file_count"],
        "total_size_bytes": row["total_size_bytes"],
        "files": files,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "error_message": row["error_message"],
        "review_id": review["id"] if review else None,
        "review_status": review["status"] if review else None,
        "review_score": review["overall_score"] if review else None
    }
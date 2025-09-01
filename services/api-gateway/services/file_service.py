"""
File processing service
Handles file validation, storage, and cleanup
"""

import os
import shutil
import aiofiles
import magic
import structlog
from typing import List, Optional
from fastapi import UploadFile
from pathlib import Path

from core.config import settings
from core.exceptions import FileError, ValidationError
from models.upload import ProcessedFileInfo
from utils.file_utils import detect_language, get_file_stats


logger = structlog.get_logger(__name__)


class FileService:
    """Service for handling file operations"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_upload_file(self, file: UploadFile, upload_id: str) -> ProcessedFileInfo:
        """Process a single uploaded file"""
        try:
            # Create upload-specific directory
            upload_path = self.upload_dir / upload_id
            upload_path.mkdir(exist_ok=True)
            
            # Generate safe filename
            safe_filename = self._generate_safe_filename(file.filename)
            file_path = upload_path / safe_filename
            
            # Read and validate file content
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Validate file size
            if len(content) > settings.max_file_size_bytes:
                raise ValidationError(
                    f"File {file.filename} exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB"
                )
            
            # Detect content type
            detected_mime = magic.from_buffer(content, mime=True)
            
            # Get file extension
            extension = Path(file.filename).suffix.lower()
            
            # Validate file extension
            if extension not in settings.allowed_extensions_list:
                raise ValidationError(
                    f"File extension {extension} not allowed. "
                    f"Allowed extensions: {', '.join(settings.allowed_extensions_list)}"
                )
            
            # Save file to disk
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # Get file statistics
            stats = await get_file_stats(file_path)
            
            # Detect programming language
            detected_language = detect_language(file.filename, content.decode('utf-8', errors='ignore'))
            
            logger.info(
                "File processed successfully",
                filename=file.filename,
                size_bytes=len(content),
                detected_language=detected_language,
                upload_id=upload_id,
            )
            
            return ProcessedFileInfo(
                filename=file.filename,
                filepath=str(file_path),
                size_bytes=len(content),
                extension=extension,
                content_type=detected_mime,
                detected_language=detected_language,
                line_count=stats.get("line_count"),
                char_count=stats.get("char_count"),
            )
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                "File processing failed",
                filename=file.filename,
                upload_id=upload_id,
                error=str(e),
            )
            raise FileError(f"Failed to process file {file.filename}: {str(e)}")
    
    async def cleanup_upload(self, upload_id: str):
        """Clean up files for a specific upload"""
        try:
            upload_path = self.upload_dir / upload_id
            
            if upload_path.exists():
                shutil.rmtree(upload_path)
                logger.info("Upload files cleaned up", upload_id=upload_id)
            else:
                logger.warning("Upload directory not found for cleanup", upload_id=upload_id)
                
        except Exception as e:
            logger.error("Failed to cleanup upload files", upload_id=upload_id, error=str(e))
            # Don't raise exception for cleanup failures
    
    async def get_file_content(self, filepath: str) -> str:
        """Read file content"""
        try:
            async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                return await f.read()
        except Exception as e:
            logger.error("Failed to read file content", filepath=filepath, error=str(e))
            raise FileError(f"Failed to read file: {str(e)}")
    
    def _generate_safe_filename(self, original_filename: str) -> str:
        """Generate a safe filename for storage"""
        # Remove any path components
        filename = os.path.basename(original_filename)
        
        # Replace unsafe characters
        safe_chars = []
        for char in filename:
            if char.isalnum() or char in '.-_':
                safe_chars.append(char)
            else:
                safe_chars.append('_')
        
        safe_filename = ''.join(safe_chars)
        
        # Ensure filename is not empty
        if not safe_filename or safe_filename.startswith('.'):
            safe_filename = f"file_{safe_filename}"
        
        return safe_filename
    
    async def cleanup_old_uploads(self, max_age_hours: int = 24):
        """Clean up old upload directories"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)
            
            for upload_dir in self.upload_dir.iterdir():
                if upload_dir.is_dir():
                    dir_mtime = upload_dir.stat().st_mtime
                    if dir_mtime < cutoff_time:
                        shutil.rmtree(upload_dir)
                        logger.info("Cleaned up old upload directory", path=str(upload_dir))
                        
        except Exception as e:
            logger.error("Failed to cleanup old uploads", error=str(e))
"""
Input validation utilities
"""

import re
from typing import List
from fastapi import UploadFile
import structlog

from core.config import Settings
from core.exceptions import ValidationError
from utils.file_utils import validate_filename, is_text_file

logger = structlog.get_logger(__name__)


def validate_files(files: List[UploadFile], settings: Settings):
    """
    Validate uploaded files against system constraints
    
    Args:
        files: List of uploaded files
        settings: Application settings
        
    Raises:
        ValidationError: If validation fails
    """
    # Check file count
    if len(files) == 0:
        raise ValidationError("No files provided")
    
    if len(files) > settings.MAX_FILES_PER_REVIEW:
        raise ValidationError(
            f"Too many files. Maximum {settings.MAX_FILES_PER_REVIEW} files allowed per review"
        )
    
    total_size = 0
    seen_filenames = set()
    
    for file in files:
        # Check filename
        if not file.filename:
            raise ValidationError("File must have a filename")
        
        if not validate_filename(file.filename):
            raise ValidationError(f"Invalid filename: {file.filename}")
        
        # Check for duplicate filenames
        if file.filename in seen_filenames:
            raise ValidationError(f"Duplicate filename: {file.filename}")
        seen_filenames.add(file.filename)
        
        # Check file extension
        extension = file.filename.split('.')[-1].lower()
        if f".{extension}" not in settings.allowed_extensions_list:
            raise ValidationError(
                f"File extension .{extension} not allowed for {file.filename}. "
                f"Allowed extensions: {', '.join(settings.allowed_extensions_list)}"
            )
        
        # Check file size (this is approximate from headers)
        if hasattr(file, 'size') and file.size:
            if file.size > settings.max_file_size_bytes:
                raise ValidationError(
                    f"File {file.filename} exceeds maximum size of {settings.MAX_FILE_SIZE_MB}MB"
                )
            total_size += file.size
    
    # Check total upload size
    max_total_size = settings.max_file_size_bytes * settings.MAX_FILES_PER_REVIEW
    if total_size > max_total_size:
        raise ValidationError(
            f"Total upload size exceeds maximum allowed "
            f"({total_size / (1024*1024):.1f}MB > {max_total_size / (1024*1024):.1f}MB)"
        )
    
    logger.info(
        "File validation passed",
        file_count=len(files),
        total_size_mb=round(total_size / (1024*1024), 2)
    )


def validate_email(email: str) -> bool:
    """
    Validate email address format
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid
    """
    if not email:
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return bool(re.match(pattern, email))


def validate_upload_id(upload_id: str) -> bool:
    """
    Validate upload ID format (UUID)
    
    Args:
        upload_id: Upload ID to validate
        
    Returns:
        True if upload ID is valid UUID format
    """
    if not upload_id:
        return False
    
    # UUID v4 pattern
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    
    return bool(re.match(uuid_pattern, upload_id, re.IGNORECASE))


def validate_language(language: str) -> bool:
    """
    Validate programming language name
    
    Args:
        language: Programming language name
        
    Returns:
        True if language is recognized
    """
    if not language:
        return True  # Optional field
    
    recognized_languages = {
        'python', 'javascript', 'typescript', 'java', 'cpp', 'c', 'go', 
        'rust', 'php', 'ruby', 'swift', 'kotlin', 'csharp', 'scala', 
        'r', 'sql', 'bash', 'powershell', 'yaml', 'json', 'xml', 
        'html', 'css', 'scss'
    }
    
    return language.lower() in recognized_languages


def sanitize_description(description: str, max_length: int = 1000) -> str:
    """
    Sanitize and validate description text
    
    Args:
        description: Description text
        max_length: Maximum allowed length
        
    Returns:
        Sanitized description
        
    Raises:
        ValidationError: If description is invalid
    """
    if not description:
        return ""
    
    # Remove any potentially harmful characters
    sanitized = re.sub(r'[<>"\'\x00-\x1f\x7f-\x9f]', '', description)
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Check length
    if len(sanitized) > max_length:
        raise ValidationError(f"Description too long (max {max_length} characters)")
    
    return sanitized


async def validate_file_content(file: UploadFile) -> bytes:
    """
    Validate and read file content
    
    Args:
        file: Uploaded file
        
    Returns:
        File content as bytes
        
    Raises:
        ValidationError: If file content is invalid
    """
    try:
        content = await file.read()
        await file.seek(0)  # Reset file pointer
        
        # Check if file is empty
        if len(content) == 0:
            raise ValidationError(f"File {file.filename} is empty")
        
        # Check if content appears to be text
        if not is_text_file(content):
            raise ValidationError(f"File {file.filename} does not appear to be a text file")
        
        # Try to decode as UTF-8 to ensure it's readable
        try:
            content.decode('utf-8')
        except UnicodeDecodeError:
            # Try other common encodings
            try:
                content.decode('latin-1')
            except UnicodeDecodeError:
                raise ValidationError(f"File {file.filename} contains invalid text encoding")
        
        return content
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error("File content validation failed", filename=file.filename, error=str(e))
        raise ValidationError(f"Failed to validate file content: {str(e)}")
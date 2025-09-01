"""
Upload request and response models
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class UploadStatus(str, Enum):
    """Upload status enumeration"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SuggestionType(str, Enum):
    """AI suggestion types"""
    BUG = "bug"
    PERFORMANCE = "performance"
    STYLE = "style"
    SECURITY = "security"
    BEST_PRACTICE = "best_practice"


class Severity(str, Enum):
    """Suggestion severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FileInfo(BaseModel):
    """Information about an uploaded file"""
    filename: str = Field(..., description="Original filename")
    size_bytes: int = Field(..., description="File size in bytes")
    extension: str = Field(..., description="File extension")
    content_type: str = Field(..., description="MIME content type")
    detected_language: Optional[str] = Field(None, description="Detected programming language")
    
    @validator('size_bytes')
    def validate_size(cls, v):
        if v <= 0:
            raise ValueError('File size must be positive')
        return v


class ProcessedFileInfo(FileInfo):
    """Extended file info with processing details"""
    filepath: str = Field(..., description="Temporary file path")
    line_count: Optional[int] = Field(None, description="Number of lines in file")
    char_count: Optional[int] = Field(None, description="Number of characters in file")


class UploadRequest(BaseModel):
    """Upload request metadata"""
    author_email: Optional[str] = Field(None, description="Author email for notifications")
    description: Optional[str] = Field(None, description="Description of the code review")
    language: Optional[str] = Field(None, description="Primary programming language")
    
    @validator('author_email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v


class UploadResponse(BaseModel):
    """Upload response with processing info"""
    upload_id: str = Field(..., description="Unique upload session ID")
    status: UploadStatus = Field(..., description="Current upload status")
    message: str = Field(..., description="Human-readable status message")
    file_count: int = Field(..., description="Number of files uploaded")
    total_size_bytes: int = Field(..., description="Total size of all files")
    files: List[FileInfo] = Field(..., description="Information about uploaded files")
    estimated_processing_time: int = Field(..., description="Estimated processing time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")


class UploadStatusResponse(BaseModel):
    """Upload status check response"""
    upload_id: str = Field(..., description="Upload session ID")
    status: UploadStatus = Field(..., description="Current status")
    progress: int = Field(..., description="Progress percentage (0-100)")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    file_count: int = Field(..., description="Number of files")
    total_size_bytes: int = Field(..., description="Total file size")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ReviewSuggestion(BaseModel):
    """Individual AI suggestion"""
    id: int = Field(..., description="Suggestion ID")
    file_path: str = Field(..., description="File path")
    line_number: Optional[int] = Field(None, description="Line number")
    suggestion_type: SuggestionType = Field(..., description="Type of suggestion")
    severity: Severity = Field(..., description="Severity level")
    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Detailed description")
    suggested_fix: Optional[str] = Field(None, description="Suggested fix")
    confidence_score: Optional[int] = Field(None, description="AI confidence (0-100)")


class ReviewResult(BaseModel):
    """Complete review result"""
    review_id: int = Field(..., description="Review ID")
    upload_id: Optional[str] = Field(None, description="Associated upload ID")
    overall_score: Optional[int] = Field(None, description="Overall code quality score (0-100)")
    summary: Optional[str] = Field(None, description="Review summary")
    model_used: str = Field(..., description="AI model used for review")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    processing_time_ms: int = Field(default=0, description="Processing time in milliseconds")
    status: str = Field(..., description="Review status")
    created_at: datetime = Field(..., description="Review start time")
    completed_at: Optional[datetime] = Field(None, description="Review completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    suggestions: List[ReviewSuggestion] = Field(default_factory=list, description="AI suggestions")
    
    commit_info: Optional[dict] = Field(None, description="Associated commit information")
    repository_info: Optional[dict] = Field(None, description="Repository information")
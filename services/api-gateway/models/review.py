"""
Review and Upload models for Pydantic validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ReviewResponse(BaseModel):
    """Single review response model"""
    id: str
    upload_id: str
    filename: str
    status: str
    language: Optional[str] = None
    file_count: int = 0
    total_size_bytes: int = 0
    author_email: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error_message: Optional[str] = None
    progress: int = 0

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """List of reviews with pagination"""
    reviews: List[ReviewResponse]
    page: int
    page_size: int
    total: int
    total_pages: int

    class Config:
        from_attributes = True


class UploadStatusResponse(BaseModel):
    """Upload status response"""
    upload_id: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    file_count: int
    total_size_bytes: int
    progress: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewStatsResponse(BaseModel):
    """Review statistics response"""
    period_days: int
    total_reviews: int
    pending_reviews: int
    processing_reviews: int
    completed_reviews: int
    failed_reviews: int
    unique_languages: Optional[int] = None
    total_bytes_processed: Optional[int] = None
    success_rate: Optional[float] = None

    class Config:
        from_attributes = True
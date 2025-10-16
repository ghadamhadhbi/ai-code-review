
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ReviewStatus(str, Enum):
    """Review processing status"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"


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


class ReviewSuggestion(BaseModel):
    """Individual AI suggestion"""
    file_path: str = Field(..., description="File path")
    line_number: Optional[int] = Field(None, description="Line number")
    suggestion_type: SuggestionType = Field(..., description="Type of suggestion")
    severity: Severity = Field(..., description="Severity level")
    title: str = Field(..., description="Suggestion title")
    description: str = Field(..., description="Detailed description")
    suggested_fix: Optional[str] = Field(None, description="Suggested fix")
    confidence_score: Optional[int] = Field(None, description="AI confidence (0-100)")


class ReviewRequest(BaseModel):
    """Review processing request"""
    upload_id: str = Field(..., description="Upload session ID")
    files: List[dict] = Field(..., description="Files to review")
    context: dict = Field(default_factory=dict, description="Review context")


class ReviewResult(BaseModel):
    """Complete review result"""
    review_id: Optional[int] = Field(None, description="Review ID")
    upload_id: str = Field(..., description="Upload session ID")
    status: ReviewStatus = Field(..., description="Review status")
    overall_score: Optional[int] = Field(None, description="Overall code quality score (0-100)")
    summary: Optional[str] = Field(None, description="Review summary")
    suggestions: List[ReviewSuggestion] = Field(default_factory=list, description="AI suggestions")
    model_used: str = Field(..., description="AI model used")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    processing_time_ms: int = Field(default=0, description="Processing time in milliseconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")


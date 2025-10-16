"""
API request/response schemas
"""

from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    service: str = "ai-review"


class ReviewStatusResponse(BaseModel):
    upload_id: str
    status: str
    review_id: Optional[int] = None
    progress: Optional[float] = None
    estimated_completion: Optional[datetime] = None
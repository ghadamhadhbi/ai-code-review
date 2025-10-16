
# =====================================================
# services/shared/database/models.py
# =====================================================

"""
Common database models and utilities
"""

from typing import Dict, Any, Optional
from datetime import datetime


class DatabaseModel:
    """Base database model with common operations"""
    
    @staticmethod
    def serialize_datetime(dt: datetime) -> str:
        """Serialize datetime to ISO string"""
        if dt:
            return dt.isoformat()
        return None
    
    @staticmethod
    def deserialize_datetime(dt_str: str) -> datetime:
        """Deserialize ISO string to datetime"""
        if dt_str:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return None


class UploadModel(DatabaseModel):
    """Upload record model"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.author_email = data.get("author_email")
        self.description = data.get("description")
        self.language = data.get("language")
        self.file_count = data.get("file_count", 0)
        self.total_size_bytes = data.get("total_size_bytes", 0)
        self.status = data.get("status", "uploaded")
        self.created_at = data.get("created_at")
        self.updated_at = data.get("updated_at")
        self.error_message = data.get("error_message")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "author_email": self.author_email,
            "description": self.description,
            "language": self.language,
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
            "status": self.status,
            "created_at": self.serialize_datetime(self.created_at),
            "updated_at": self.serialize_datetime(self.updated_at),
            "error_message": self.error_message,
        }


class ReviewModel(DatabaseModel):
    """Review result model"""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id")
        self.upload_id = data.get("upload_id")
        self.overall_score = data.get("overall_score")
        self.summary = data.get("summary")
        self.model_used = data.get("model_used")
        self.tokens_used = data.get("tokens_used", 0)
        self.processing_time_ms = data.get("processing_time_ms", 0)
        self.status = data.get("status", "pending")
        self.created_at = data.get("created_at")
        self.completed_at = data.get("completed_at")
        self.error_message = data.get("error_message")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "upload_id": self.upload_id,
            "overall_score": self.overall_score,
            "summary": self.summary,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "processing_time_ms": self.processing_time_ms,
            "status": self.status,
            "created_at": self.serialize_datetime(self.created_at),
            "completed_at": self.serialize_datetime(self.completed_at),
            "error_message": self.error_message,
        }


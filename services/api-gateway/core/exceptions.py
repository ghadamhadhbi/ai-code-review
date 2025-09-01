"""
Custom exceptions for API Gateway
"""

from typing import Optional, Dict, Any


class APIException(Exception):
    """Base API exception"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIException):
    """Raised when input validation fails"""
    pass


class ProcessingError(APIException):
    """Raised when file processing fails"""
    pass


class KafkaError(APIException):
    """Raised when Kafka operations fail"""
    pass


class DatabaseError(APIException):
    """Raised when database operations fail"""
    pass


class FileError(APIException):
    """Raised when file operations fail"""
    pass


class ServiceUnavailableError(APIException):
    """Raised when external services are unavailable"""
    pass
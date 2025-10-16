
# =====================================================
# services/shared/utils/logging.py
# =====================================================

"""
Structured logging configuration for all services
"""

import structlog
import logging
import sys


def configure_logging(service_name: str, log_level: str = "INFO"):
    """Configure structured logging for a service"""
    
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Add service name to all log entries
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            # JSON output for production, pretty print for development
            structlog.dev.ConsoleRenderer() if log_level == "DEBUG" 
            else structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create logger with service context
    logger = structlog.get_logger(service_name)
    logger.info("Logging configured", service=service_name, level=log_level)
    
    return logger


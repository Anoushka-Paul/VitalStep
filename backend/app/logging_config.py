"""
Logging configuration for production
"""
import logging
import sys
from typing import Dict, Any
from datetime import datetime
import json


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", log_format: str = None):
    """
    Setup logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format string (optional)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    
    # Use JSON formatter for production, standard for development
    if log_format:
        console_handler.setFormatter(logging.Formatter(log_format))
    else:
        console_handler.setFormatter(JSONFormatter())
    
    root_logger.addHandler(console_handler)
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("supabase").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured with level: {log_level}")


class LoggerMixin:
    """Mixin to add logging capabilities to classes"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return logging.getLogger(self.__class__.__name__)


def log_request(request_data: Dict[str, Any], logger: logging.Logger):
    """Log incoming request data"""
    logger.info(f"Request received", extra={"request": request_data})


def log_response(response_data: Dict[str, Any], logger: logging.Logger, duration: float = None):
    """Log response data"""
    log_extra = {"response": response_data}
    if duration:
        log_extra["duration_ms"] = round(duration * 1000, 2)
    logger.info(f"Response sent", extra=log_extra)


def log_error(error: Exception, logger: logging.Logger, context: Dict[str, Any] = None):
    """Log error with context"""
    log_extra = {"error": str(error), "error_type": type(error).__name__}
    if context:
        log_extra.update(context)
    logger.error(f"Error occurred: {str(error)}", extra=log_extra, exc_info=True)
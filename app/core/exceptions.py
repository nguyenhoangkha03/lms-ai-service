from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AIServiceException(Exception):
    """Base exception for AI services"""
    
    def __init__(self, message: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ModelNotFoundError(AIServiceException):
    """Raised when a required model is not found"""
    
    def __init__(self, model_name: str):
        super().__init__(
            message=f"Model '{model_name}' not found",
            status_code=404,
            details={"model_name": model_name}
        )

class DatabaseConnectionError(AIServiceException):
    """Raised when database connection fails"""
    
    def __init__(self, details: str = None):
        super().__init__(
            message="Database connection failed",
            status_code=503,
            details={"error": details} if details else {}
        )

class RedisConnectionError(AIServiceException):
    """Raised when Redis connection fails"""
    
    def __init__(self, details: str = None):
        super().__init__(
            message="Redis connection failed",
            status_code=503,
            details={"error": details} if details else {}
        )

class MLProcessingError(AIServiceException):
    """Raised when ML processing fails"""
    
    def __init__(self, details: str = None):
        super().__init__(
            message="ML processing failed",
            status_code=500,
            details={"error": details} if details else {}
        )

def setup_exception_handlers(app: FastAPI):
    """Setup custom exception handlers"""
    
    @app.exception_handler(AIServiceException)
    async def ai_service_exception_handler(request: Request, exc: AIServiceException):
        """Handle custom AI service exceptions"""
        logger.error(
            f"AI Service Error: {exc.message}",
            extra={
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "type": exc.__class__.__name__,
                    "details": exc.details
                },
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors"""
        logger.warning(
            f"Validation Error: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors()
            }
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "message": "Request validation failed",
                    "type": "ValidationError",
                    "details": exc.errors()
                },
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        logger.warning(
            f"HTTP Error {exc.status_code}: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.detail,
                    "type": "HTTPException"
                },
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions"""
        logger.error(
            f"Unexpected Error: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "exception_type": exc.__class__.__name__
            }
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "type": "InternalServerError"
                },
                "request_id": getattr(request.state, "request_id", None)
            }
        )
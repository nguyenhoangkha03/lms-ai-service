from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging

from app.config.settings import get_settings
from app.config.database import engine, create_tables
from app.config.redis import init_redis_pool
from app.core.exceptions import setup_exception_handlers
from app.core.middleware import setup_middleware
from app.api.v1.router import api_router
from app.core.utils import setup_logging

settings = get_settings()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    try:
        # Startup
        logger.info("🚀 Starting AI Services...")
        
        # Initialize database
        await create_tables()
        logger.info("✅ Database tables created/verified")
        
        # Initialize Redis
        await init_redis_pool()
        logger.info("✅ Redis connection established")
        
        # Additional startup tasks
        logger.info("✅ AI Services started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise
    finally:
        # Shutdown
        logger.info("🛑 Shutting down AI Services...")
        # Cleanup tasks here
        logger.info("✅ AI Services shut down complete")

# Create FastAPI application
app = FastAPI(
    title="LMS AI Services",
    description="AI-powered backend services for Learning Management System",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Setup logging
setup_logging()

# Setup middleware
setup_middleware(app)

# Setup exception handlers
setup_exception_handlers(app)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-services",
        "version": "1.0.0",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )

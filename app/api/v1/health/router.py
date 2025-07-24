from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import time
import psutil
import logging
from typing import Dict, Any

from app.config.database import get_database
from app.config.redis import get_redis
from app.config.settings import get_settings

router = APIRouter(prefix="/health", tags=["Health Check"])
settings = get_settings()
logger = logging.getLogger(__name__)

@router.get("/")
async def basic_health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-services",
        "version": "1.0.0",
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT
    }

@router.get("/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_database)
):
    """Detailed health check with dependency status"""
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "service": "ai-services",
        "version": "1.0.0",
        "timestamp": start_time,
        "environment": settings.ENVIRONMENT,
        "checks": {}
    }
    
    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        logger.error(f"Database health check failed: {str(e)}")
    
    # Check Redis connection
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        logger.error(f"Redis health check failed: {str(e)}")
    
    # Check system resources
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_status["checks"]["system"] = {
            "status": "healthy",
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "available_memory_gb": round(memory.available / (1024**3), 2)
        }
        
        # Warning thresholds
        if cpu_percent > 80 or memory.percent > 85 or disk.percent > 90:
            health_status["checks"]["system"]["status"] = "warning"
            health_status["checks"]["system"]["message"] = "High resource usage detected"
            
    except Exception as e:
        health_status["checks"]["system"] = {
            "status": "error",
            "message": f"Failed to get system metrics: {str(e)}"
        }
    
    # Check external dependencies
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.NESTJS_API_URL}/health",
                timeout=5.0
            )
            if response.status_code == 200:
                health_status["checks"]["nestjs_backend"] = {
                    "status": "healthy",
                    "message": "NestJS backend reachable"
                }
            else:
                health_status["checks"]["nestjs_backend"] = {
                    "status": "unhealthy",
                    "message": f"NestJS backend returned {response.status_code}"
                }
    except Exception as e:
        health_status["checks"]["nestjs_backend"] = {
            "status": "unhealthy",
            "message": f"NestJS backend unreachable: {str(e)}"
        }
    
    # Calculate response time
    health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    # Return appropriate status code
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

@router.get("/readiness")
async def readiness_check(
    db: AsyncSession = Depends(get_database)
):
    """Kubernetes readiness probe endpoint"""
    try:
        # Check critical dependencies
        await db.execute(text("SELECT 1"))
        
        redis_client = await get_redis()
        await redis_client.ping()
        
        return {"status": "ready"}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "error": str(e)}
        )

@router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive", "timestamp": time.time()}

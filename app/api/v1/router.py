from fastapi import APIRouter

from app.api.v1.health.router import router as health_router

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(health_router)

# Will be added in subsequent parts:
# api_router.include_router(analytics_router)
# api_router.include_router(recommendations_router)
# api_router.include_router(assessment_router)
# api_router.include_router(chatbot_router)
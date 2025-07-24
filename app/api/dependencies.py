from fastapi import Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
import logging

from app.config.database import get_database
from app.config.redis import get_redis
from app.core.auth import get_current_user, get_optional_user

logger = logging.getLogger(__name__)

class CommonQueryParams:
    """Common query parameters for list endpoints"""
    
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
        sort_by: Optional[str] = Query(None, description="Field to sort by"),
        sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order")
    ):
        self.skip = skip
        self.limit = limit
        self.sort_by = sort_by
        self.sort_order = sort_order

class StudentAccessControl:
    """Access control for student-related endpoints"""
    
    def __init__(
        self,
        student_id: str = Path(..., description="Student ID"),
        current_user: Dict[str, Any] = Depends(get_current_user),
        db: AsyncSession = Depends(get_database)
    ):
        self.student_id = student_id
        self.current_user = current_user
        self.db = db
        
        # Check if user can access this student's data
        self._check_access()
    
    def _check_access(self):
        """Check if current user can access student data"""
        user_id = self.current_user.get("id")
        user_type = self.current_user.get("userType")
        
        # Students can only access their own data
        if user_type == "student" and user_id != self.student_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Can only access your own data"
            )
        
        # Teachers and admins can access any student data
        if user_type not in ["student", "teacher", "admin"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Insufficient permissions"
            )

class CourseAccessControl:
    """Access control for course-related endpoints"""
    
    def __init__(
        self,
        course_id: str = Path(..., description="Course ID"),
        current_user: Dict[str, Any] = Depends(get_current_user),
        db: AsyncSession = Depends(get_database)
    ):
        self.course_id = course_id
        self.current_user = current_user
        self.db = db

async def get_user_context(
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
) -> Dict[str, Any]:
    """Get user context for personalization"""
    if not current_user:
        return {"user_id": None, "user_type": "anonymous", "personalize": False}
    
    return {
        "user_id": current_user.get("id"),
        "user_type": current_user.get("userType"),
        "roles": current_user.get("roles", []),
        "personalize": True
    }

async def get_cache_manager():
    """Dependency to get cache manager"""
    from app.config.redis import cache
    return cache

async def validate_pagination(
    skip: int = Query(0, ge=0, le=10000, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of items to return")
) -> Dict[str, int]:
    """Validate and return pagination parameters"""
    return {"skip": skip, "limit": limit}

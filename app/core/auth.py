from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional, Dict, Any
import httpx
import logging

from app.config.settings import get_settings
from app.config.redis import get_redis

settings = get_settings()
logger = logging.getLogger(__name__)

# JWT Security scheme
security = HTTPBearer()

class AuthManager:
    """Authentication manager for JWT token validation"""
    
    def __init__(self):
        self.nestjs_api_url = settings.NESTJS_API_URL
        self.api_key = settings.NESTJS_API_KEY
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token with NestJS backend"""
        try:
            # First check Redis cache
            redis_client = await get_redis()
            cached_user = await redis_client.get(f"user_token:{token}")
            
            if cached_user:
                import json
                return json.loads(cached_user)
            
            # Verify with NestJS backend
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.nestjs_api_url}/api/v1/auth/verify-token",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-API-Key": self.api_key
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    
                    # Cache the user data for 15 minutes
                    await redis_client.setex(
                        f"user_token:{token}",
                        900,  # 15 minutes
                        json.dumps(user_data)
                    )
                    
                    return user_data
                
                return None
                
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return None
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
        """Get current authenticated user"""
        token = credentials.credentials
        
        user_data = await self.verify_token(token)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user_data
    
    async def require_role(self, allowed_roles: list, user: Dict[str, Any] = None):
        """Check if user has required role"""
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_roles = user.get("roles", [])
        user_type = user.get("userType", "")
        
        # Check if user has any of the allowed roles
        if not any(role in user_roles or role == user_type for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return True

# Global auth manager instance
auth_manager = AuthManager()

# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    return await auth_manager.get_current_user(credentials)

async def get_current_student(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency to get current student user"""
    await auth_manager.require_role(["student"], current_user)
    return current_user

async def get_current_teacher(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency to get current teacher user"""
    await auth_manager.require_role(["teacher"], current_user)
    return current_user

async def get_current_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency to get current admin user"""
    await auth_manager.require_role(["admin"], current_user)
    return current_user

# Optional authentication (for public endpoints that can work with/without auth)
async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False)) -> Optional[Dict[str, Any]]:
    """Dependency to get current user optionally"""
    if not credentials:
        return None
    
    try:
        return await auth_manager.get_current_user(credentials)
    except HTTPException:
        return None
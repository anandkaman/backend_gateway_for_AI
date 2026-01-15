"""
JWT Authentication Handler
Manages token generation, validation, and user authentication
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from passlib.context import CryptContext
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import get_config


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


class JWTHandler:
    """Handles JWT token operations"""
    
    def __init__(self):
        self.config = get_config().auth
        self.algorithm = self.config.jwt_algorithm
        self.secret = self.config.jwt_secret
        self.access_token_expire = self.config.access_token_expire_minutes
        self.refresh_token_expire = self.config.refresh_token_expire_days
    
    def create_access_token(
        self,
        data: Dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        return jwt.encode(to_encode, self.secret, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        return jwt.encode(to_encode, self.secret, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)


# Global JWT handler
jwt_handler = JWTHandler()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict:
    """
    Dependency to get current authenticated user
    
    Usage in FastAPI endpoints:
        @app.get("/protected")
        async def protected_route(user: Dict = Depends(get_current_user)):
            ...
    """
    token = credentials.credentials
    payload = jwt_handler.decode_token(token)
    
    # Validate token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    return payload


def create_tokens(user_id: str, client_id: str) -> Dict[str, str]:
    """Create access and refresh tokens for a user"""
    data = {
        "sub": user_id,
        "client_id": client_id
    }
    
    return {
        "access_token": jwt_handler.create_access_token(data),
        "refresh_token": jwt_handler.create_refresh_token(data),
        "token_type": "bearer"
    }

"""
Dual Authentication Dependencies
Supports both JWT (internal) and API keys (external clients)
"""

from fastapi import Header, HTTPException, Depends, status
from typing import Optional
from app.auth.jwt_handler import get_current_user
from app.auth.api_keys import APIKeyManager


async def get_api_key_user(
    x_api_key: Optional[str] = Header(None),
    api_key_manager: APIKeyManager = None
) -> Optional[dict]:
    """
    Validate API key from X-API-Key header
    
    Returns:
        Client info if valid, None if no API key provided
    """
    if not x_api_key:
        return None
    
    if not api_key_manager:
        from app.main import api_key_manager as global_manager
        api_key_manager = global_manager
    
    client_info = await api_key_manager.validate_api_key(x_api_key)
    
    if not client_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )
    
    return {
        "email": client_info["email"],
        "name": client_info["name"],
        "auth_type": "api_key",
        "rate_limit": client_info.get("rate_limit", 60)
    }


async def get_current_user_or_api_key(
    jwt_user: Optional[dict] = Depends(get_current_user),
    api_key_user: Optional[dict] = Depends(get_api_key_user)
) -> dict:
    """
    Dual authentication: Accept either JWT or API key
    
    Priority:
    1. JWT token (for internal company software)
    2. API key (for external clients)
    
    Returns:
        User/client info
    """
    # Try JWT first (internal)
    if jwt_user:
        return {
            **jwt_user,
            "auth_type": "jwt"
        }
    
    # Try API key (external)
    if api_key_user:
        return api_key_user
    
    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either JWT token (Authorization: Bearer) or API key (X-API-Key)",
        headers={"WWW-Authenticate": "Bearer"}
    )

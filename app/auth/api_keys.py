"""
API Key Management System
Handles API key generation, validation, and management for external clients
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorClient


class APIKeyManager:
    """
    Manages API keys for external clients
    
    Features:
    - Generate secure API keys
    - Store hashed keys in MongoDB
    - Validate API keys
    - Track usage per key
    - Revoke/delete keys
    - Email-based client tracking
    """
    
    def __init__(self, mongodb_client: AsyncIOMotorClient, db_name: str = "ai_gateway"):
        self.client = mongodb_client
        self.db = self.client[db_name]
        self.collection = self.db["api_keys"]
    
    async def initialize(self):
        """Create indexes for API keys collection"""
        await self.collection.create_index("key_hash", unique=True)
        await self.collection.create_index("email")
        await self.collection.create_index("active")
        await self.collection.create_index("created_at")
    
    def _generate_key(self) -> str:
        """Generate a secure random API key"""
        # Format: agw_<32 random characters>
        random_part = secrets.token_urlsafe(32)
        return f"agw_{random_part}"
    
    def _hash_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def create_api_key(
        self,
        email: str,
        name: str = "",
        description: str = "",
        expires_days: Optional[int] = None
    ) -> Dict:
        """
        Create a new API key for a client
        
        Args:
            email: Client email address
            name: Client name or company
            description: Optional description
            expires_days: Days until expiration (None = never expires)
        
        Returns:
            Dict with api_key (plaintext, show once!) and metadata
        """
        # Generate key
        api_key = self._generate_key()
        key_hash = self._hash_key(api_key)
        
        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # Create document
        key_doc = {
            "key_hash": key_hash,
            "email": email.lower().strip(),
            "name": name,
            "description": description,
            "active": True,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "last_used_at": None,
            "usage_count": 0,
            "rate_limit": 60,  # requests per minute
            "metadata": {}
        }
        
        # Store in database
        await self.collection.insert_one(key_doc)
        
        # Return key (ONLY TIME IT'S SHOWN IN PLAINTEXT!)
        return {
            "api_key": api_key,  # Show this to client ONCE
            "email": email,
            "name": name,
            "created_at": key_doc["created_at"],
            "expires_at": expires_at,
            "active": True
        }
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """
        Validate an API key and return client info
        
        Args:
            api_key: The API key to validate
        
        Returns:
            Client info dict if valid, None if invalid
        """
        if not api_key or not api_key.startswith("agw_"):
            return None
        
        key_hash = self._hash_key(api_key)
        
        # Find key in database
        key_doc = await self.collection.find_one({"key_hash": key_hash})
        
        if not key_doc:
            return None
        
        # Check if active
        if not key_doc.get("active", False):
            return None
        
        # Check expiration
        if key_doc.get("expires_at"):
            if datetime.utcnow() > key_doc["expires_at"]:
                # Expired - deactivate it
                await self.collection.update_one(
                    {"_id": key_doc["_id"]},
                    {"$set": {"active": False}}
                )
                return None
        
        # Update usage stats
        await self.collection.update_one(
            {"_id": key_doc["_id"]},
            {
                "$set": {"last_used_at": datetime.utcnow()},
                "$inc": {"usage_count": 1}
            }
        )
        
        return {
            "email": key_doc["email"],
            "name": key_doc["name"],
            "rate_limit": key_doc.get("rate_limit", 60),
            "usage_count": key_doc["usage_count"] + 1
        }
    
    async def revoke_api_key(self, email: str) -> int:
        """
        Revoke all API keys for an email
        
        Returns:
            Number of keys revoked
        """
        result = await self.collection.update_many(
            {"email": email.lower().strip(), "active": True},
            {"$set": {"active": False, "revoked_at": datetime.utcnow()}}
        )
        return result.modified_count
    
    async def delete_api_key(self, email: str) -> int:
        """
        Permanently delete all API keys for an email
        
        Returns:
            Number of keys deleted
        """
        result = await self.collection.delete_many(
            {"email": email.lower().strip()}
        )
        return result.deleted_count
    
    async def list_api_keys(
        self,
        active_only: bool = True,
        limit: int = 100
    ) -> List[Dict]:
        """
        List all API keys
        
        Args:
            active_only: Only show active keys
            limit: Maximum number of keys to return
        
        Returns:
            List of API key metadata (without actual keys)
        """
        query = {"active": True} if active_only else {}
        
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
        
        keys = []
        async for doc in cursor:
            keys.append({
                "email": doc["email"],
                "name": doc["name"],
                "description": doc.get("description", ""),
                "active": doc["active"],
                "created_at": doc["created_at"],
                "expires_at": doc.get("expires_at"),
                "last_used_at": doc.get("last_used_at"),
                "usage_count": doc.get("usage_count", 0),
                "rate_limit": doc.get("rate_limit", 60)
            })
        
        return keys
    
    async def get_key_stats(self, email: str) -> Optional[Dict]:
        """Get statistics for a specific client's API keys"""
        keys = await self.collection.find(
            {"email": email.lower().strip()}
        ).to_list(length=100)
        
        if not keys:
            return None
        
        total_usage = sum(k.get("usage_count", 0) for k in keys)
        active_keys = sum(1 for k in keys if k.get("active", False))
        
        return {
            "email": email,
            "total_keys": len(keys),
            "active_keys": active_keys,
            "total_usage": total_usage,
            "last_used": max((k.get("last_used_at") for k in keys if k.get("last_used_at")), default=None)
        }

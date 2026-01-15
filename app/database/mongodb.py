"""
MongoDB Database Connection and Operations
Handles all database interactions with 15-day auto-cleanup
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging

from app.config import get_config


logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager"""
    
    def __init__(self):
        self.config = get_config().mongodb
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self._cleanup_task = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.config.uri)
            self.db = self.client[self.config.database]
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Create indexes
            await self._create_indexes()
            
            logger.info(f"Connected to MongoDB: {self.config.database}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create necessary indexes"""
        # Request history indexes
        await self.db[self.config.collections.requests].create_index("created_at")
        await self.db[self.config.collections.requests].create_index("client_id")
        await self.db[self.config.collections.requests].create_index("model_name")
        
        # Queue state indexes
        await self.db[self.config.collections.queue_state].create_index("request_id", unique=True)
        await self.db[self.config.collections.queue_state].create_index("model_name")
        await self.db[self.config.collections.queue_state].create_index("status")
        
        # Crash logs indexes
        await self.db[self.config.collections.crashes].create_index("timestamp")
        
        # Metrics indexes
        await self.db[self.config.collections.metrics].create_index("timestamp")
        
        logger.info("Database indexes created")
    
    async def cleanup_old_data(self):
        """Delete data older than retention period (15 days)"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.history_retention_days)
        
        try:
            # Clean request history
            result = await self.db[self.config.collections.requests].delete_many({
                "created_at": {"$lt": cutoff_date}
            })
            logger.info(f"Deleted {result.deleted_count} old request records")
            
            # Clean crash logs
            result = await self.db[self.config.collections.crashes].delete_many({
                "timestamp": {"$lt": cutoff_date}
            })
            logger.info(f"Deleted {result.deleted_count} old crash logs")
            
            # Clean metrics
            result = await self.db[self.config.collections.metrics].delete_many({
                "timestamp": {"$lt": cutoff_date}
            })
            logger.info(f"Deleted {result.deleted_count} old metrics")
            
            # Clean completed queue items
            result = await self.db[self.config.collections.queue_state].delete_many({
                "status": {"$in": ["completed", "failed", "timeout"]},
                "completed_at": {"$lt": cutoff_date}
            })
            logger.info(f"Deleted {result.deleted_count} old queue records")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    # Request History Operations
    async def save_request(self, request_data: Dict):
        """Save request to history"""
        await self.db[self.config.collections.requests].insert_one(request_data)
    
    async def get_request_history(
        self,
        client_id: Optional[str] = None,
        model_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get request history with filters"""
        query = {}
        if client_id:
            query["client_id"] = client_id
        if model_name:
            query["model_name"] = model_name
        
        cursor = self.db[self.config.collections.requests].find(query).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    # Crash Logging Operations
    async def log_crash(self, crash_data: Dict):
        """Log a crash event"""
        crash_data["timestamp"] = datetime.utcnow()
        await self.db[self.config.collections.crashes].insert_one(crash_data)
        logger.error(f"Crash logged: {crash_data.get('error', 'Unknown')}")
    
    async def get_crash_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent crash logs"""
        cursor = self.db[self.config.collections.crashes].find().sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    # Missing Model Tracking
    async def log_missing_model(self, model_name: str, client_id: str):
        """Log request for unavailable model"""
        await self.db[self.config.collections.missing_models].insert_one({
            "model_name": model_name,
            "client_id": client_id,
            "timestamp": datetime.utcnow()
        })
        logger.warning(f"Missing model request logged: {model_name} from {client_id}")
    
    async def get_missing_model_requests(self, limit: int = 100) -> List[Dict]:
        """Get requests for missing models"""
        cursor = self.db[self.config.collections.missing_models].find().sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    # Metrics Operations
    async def save_metrics(self, metrics_data: Dict):
        """Save metrics snapshot"""
        metrics_data["timestamp"] = datetime.utcnow()
        await self.db[self.config.collections.metrics].insert_one(metrics_data)
    
    async def get_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """Get metrics within time range"""
        query = {}
        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time
            if end_time:
                query["timestamp"]["$lte"] = end_time
        
        cursor = self.db[self.config.collections.metrics].find(query).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)


# Global MongoDB instance
mongodb = MongoDB()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance"""
    return mongodb.db

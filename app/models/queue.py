"""
Crash-Proof Request Queue System
Handles request queuing with persistence, recovery, and crash protection
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import deque
import logging

from motor.motor_asyncio import AsyncIOMotorClient


logger = logging.getLogger(__name__)


class RequestStatus(str, Enum):
    """Request status states"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Request priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class QueuedRequest:
    """Represents a queued request with crash recovery data"""
    request_id: str
    model_name: str
    task_type: str
    client_id: str
    payload: Dict[str, Any]
    priority: Priority = Priority.NORMAL
    status: RequestStatus = RequestStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    error: Optional[str] = None
    result: Optional[Any] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'QueuedRequest':
        """Create from dictionary (MongoDB recovery)"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['started_at'] = datetime.fromisoformat(data['started_at']) if data['started_at'] else None
        data['completed_at'] = datetime.fromisoformat(data['completed_at']) if data['completed_at'] else None
        data['priority'] = Priority(data['priority'])
        data['status'] = RequestStatus(data['status'])
        return cls(**data)
    
    def is_timeout(self) -> bool:
        """Check if request has timed out"""
        if self.started_at is None:
            return False
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds


class CrashProofQueue:
    """
    Crash-proof queue with MongoDB persistence
    
    Features:
    - Persistent storage for crash recovery
    - Priority handling
    - Timeout management
    - Automatic retry on failure
    - Health monitoring
    """
    
    def __init__(
        self,
        model_name: str,
        max_concurrent: int,
        max_waiting: int,
        mongodb_client: AsyncIOMotorClient,
        db_name: str = "ai_gateway",
        collection_name: str = "queue_state"
    ):
        self.model_name = model_name
        self.max_concurrent = max_concurrent
        self.max_waiting = max_waiting
        
        # In-memory queues
        self.processing: Dict[str, QueuedRequest] = {}
        self.waiting: deque = deque()  # Priority queue
        
        # MongoDB for persistence
        self.db = mongodb_client[db_name]
        self.collection = self.db[collection_name]
        
        # Metrics
        self.total_processed = 0
        self.total_failed = 0
        self.total_timeout = 0
        
        # Recovery task
        self.recovery_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        logger.info(f"Initialized CrashProofQueue for {model_name}: "
                   f"max_concurrent={max_concurrent}, max_waiting={max_waiting}")
    
    async def start(self):
        """Start the queue and recovery system"""
        self.is_running = True
        
        # Recover any pending requests from database
        await self.recover_from_crash()
        
        # Start background recovery checker
        self.recovery_task = asyncio.create_task(self._recovery_loop())
        
        logger.info(f"Queue started for {self.model_name}")
    
    async def stop(self):
        """Stop the queue gracefully"""
        self.is_running = False
        
        if self.recovery_task:
            self.recovery_task.cancel()
            try:
                await self.recovery_task
            except asyncio.CancelledError:
                pass
        
        # Persist all pending requests
        await self._persist_all()
        
        logger.info(f"Queue stopped for {self.model_name}")
    
    async def enqueue(
        self,
        payload: Dict[str, Any],
        task_type: str,
        client_id: str,
        priority: Priority = Priority.NORMAL,
        timeout: int = 300
    ) -> str:
        """
        Add request to queue
        
        Returns:
            request_id: Unique identifier for tracking
        
        Raises:
            QueueFullError: If queue is at capacity
        """
        # Check if queue is full
        if len(self.waiting) >= self.max_waiting:
            raise QueueFullError(f"Queue full for {self.model_name}")
        
        # Create request
        request = QueuedRequest(
            request_id=str(uuid.uuid4()),
            model_name=self.model_name,
            task_type=task_type,
            client_id=client_id,
            payload=payload,
            priority=priority,
            timeout_seconds=timeout
        )
        
        # Add to waiting queue (sorted by priority)
        self._insert_by_priority(request)
        
        # Persist to database
        await self._persist_request(request)
        
        logger.info(f"Enqueued request {request.request_id} for {self.model_name}")
        
        return request.request_id
    
    async def dequeue(self) -> Optional[QueuedRequest]:
        """
        Get next request from queue for processing
        
        Returns:
            QueuedRequest if available, None if queue empty or at capacity
        """
        # Check if we can process more
        if len(self.processing) >= self.max_concurrent:
            return None
        
        # Get next request from waiting queue
        if not self.waiting:
            return None
        
        request = self.waiting.popleft()
        request.status = RequestStatus.PROCESSING
        request.started_at = datetime.utcnow()
        
        # Move to processing
        self.processing[request.request_id] = request
        
        # Update in database
        await self._persist_request(request)
        
        logger.info(f"Dequeued request {request.request_id} for processing")
        
        return request
    
    async def complete(self, request_id: str, result: Any = None):
        """Mark request as completed"""
        if request_id not in self.processing:
            logger.warning(f"Request {request_id} not in processing queue")
            return
        
        request = self.processing.pop(request_id)
        request.status = RequestStatus.COMPLETED
        request.completed_at = datetime.utcnow()
        request.result = result
        
        self.total_processed += 1
        
        # Update in database
        await self._persist_request(request)
        
        logger.info(f"Completed request {request_id}")
    
    async def fail(self, request_id: str, error: str):
        """Mark request as failed and retry if possible"""
        if request_id not in self.processing:
            logger.warning(f"Request {request_id} not in processing queue")
            return
        
        request = self.processing.pop(request_id)
        request.error = error
        request.retry_count += 1
        
        # Retry if under max retries
        if request.retry_count < request.max_retries:
            logger.warning(f"Request {request_id} failed, retrying ({request.retry_count}/{request.max_retries})")
            request.status = RequestStatus.QUEUED
            request.started_at = None
            self._insert_by_priority(request)
        else:
            logger.error(f"Request {request_id} failed permanently after {request.retry_count} retries")
            request.status = RequestStatus.FAILED
            request.completed_at = datetime.utcnow()
            self.total_failed += 1
        
        # Update in database
        await self._persist_request(request)
    
    async def get_status(self, request_id: str) -> Optional[Dict]:
        """Get status of a request"""
        # Check processing queue
        if request_id in self.processing:
            return self.processing[request_id].to_dict()
        
        # Check waiting queue
        for req in self.waiting:
            if req.request_id == request_id:
                return req.to_dict()
        
        # Check database
        doc = await self.collection.find_one({"request_id": request_id})
        if doc:
            return doc
        
        return None
    
    def get_metrics(self) -> Dict:
        """Get queue metrics"""
        return {
            "model": self.model_name,
            "processing": len(self.processing),
            "waiting": len(self.waiting),
            "max_concurrent": self.max_concurrent,
            "max_waiting": self.max_waiting,
            "total_processed": self.total_processed,
            "total_failed": self.total_failed,
            "total_timeout": self.total_timeout,
            "utilization": len(self.processing) / self.max_concurrent if self.max_concurrent > 0 else 0
        }
    
    async def recover_from_crash(self):
        """Recover pending requests from database after crash"""
        logger.info(f"Recovering queue state for {self.model_name}...")
        
        # Find all pending requests for this model
        cursor = self.collection.find({
            "model_name": self.model_name,
            "status": {"$in": [RequestStatus.QUEUED, RequestStatus.PROCESSING]}
        })
        
        recovered = 0
        async for doc in cursor:
            try:
                request = QueuedRequest.from_dict(doc)
                
                # Reset processing requests to queued
                if request.status == RequestStatus.PROCESSING:
                    request.status = RequestStatus.QUEUED
                    request.started_at = None
                    request.retry_count += 1
                
                # Re-add to waiting queue
                if request.retry_count < request.max_retries:
                    self._insert_by_priority(request)
                    recovered += 1
                else:
                    # Mark as failed if too many retries
                    request.status = RequestStatus.FAILED
                    await self._persist_request(request)
            
            except Exception as e:
                logger.error(f"Failed to recover request: {e}")
        
        logger.info(f"Recovered {recovered} requests for {self.model_name}")
    
    async def _recovery_loop(self):
        """Background task to check for timeouts and crashes"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check for timeouts
                timeout_ids = []
                for request_id, request in self.processing.items():
                    if request.is_timeout():
                        timeout_ids.append(request_id)
                
                # Handle timeouts
                for request_id in timeout_ids:
                    logger.warning(f"Request {request_id} timed out")
                    request = self.processing.pop(request_id)
                    request.status = RequestStatus.TIMEOUT
                    request.completed_at = datetime.utcnow()
                    self.total_timeout += 1
                    await self._persist_request(request)
                
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")
    
    def _insert_by_priority(self, request: QueuedRequest):
        """Insert request into waiting queue sorted by priority"""
        priority_order = {Priority.HIGH: 0, Priority.NORMAL: 1, Priority.LOW: 2}
        
        # Find insertion point
        inserted = False
        for i, existing in enumerate(self.waiting):
            if priority_order[request.priority] < priority_order[existing.priority]:
                self.waiting.insert(i, request)
                inserted = True
                break
        
        if not inserted:
            self.waiting.append(request)
    
    async def _persist_request(self, request: QueuedRequest):
        """Persist request to database"""
        try:
            await self.collection.update_one(
                {"request_id": request.request_id},
                {"$set": request.to_dict()},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to persist request {request.request_id}: {e}")
    
    async def _persist_all(self):
        """Persist all pending requests"""
        for request in list(self.processing.values()) + list(self.waiting):
            await self._persist_request(request)


class QueueFullError(Exception):
    """Raised when queue is at capacity"""
    pass

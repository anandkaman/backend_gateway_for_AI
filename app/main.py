"""
Main FastAPI Application
Production-grade AI Gateway with intelligent routing and queuing
"""

from fastapi import FastAPI, Depends, HTTPException, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from app.config import get_config
from app.database.mongodb import mongodb
from app.models.manager import ModelManager, OCRResolution
from app.models.queue import CrashProofQueue, Priority, QueueFullError
from app.auth.jwt_handler import get_current_user, create_tokens
from app.auth.api_keys import APIKeyManager
from app.monitoring.auto_switcher import AutoSwitcher


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global instances
model_manager: Optional[ModelManager] = None
queues: Dict[str, CrashProofQueue] = {}
auto_switcher: Optional[AutoSwitcher] = None
api_key_manager: Optional[APIKeyManager] = None
cleanup_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global model_manager, queues, auto_switcher, cleanup_task
    
    logger.info("Starting AI Gateway...")
    
    # Connect to MongoDB
    await mongodb.connect()
    
    # Initialize model manager
    model_manager = ModelManager()
    
    # Initialize queues for each model
    config = get_config()
    for model_name, model_config in config.models.items():
        if model_config.enabled:
            queue = CrashProofQueue(
                model_name=model_name,
                max_concurrent=model_config.max_concurrent,
                max_waiting=config.queue.max_waiting,
                mongodb_client=mongodb.client,
                db_name=config.mongodb.database,
                collection_name=config.mongodb.collections.queue_state
            )
            await queue.start()
            queues[model_name] = queue
            logger.info(f"Queue initialized for {model_name}")
    
    # Initialize auto-switcher
    auto_switcher = AutoSwitcher(model_manager, queues)
    await auto_switcher.start()
    
    # Initialize API key manager
    api_key_manager = APIKeyManager(
        mongodb_client=mongodb.client,
        db_name=config.mongodb.database
    )
    await api_key_manager.initialize()
    logger.info("API key manager initialized")
    
    # Start cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    logger.info("AI Gateway started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Gateway...")
    
    # Stop auto-switcher
    if auto_switcher:
        await auto_switcher.stop()
    
    # Stop cleanup task
    if cleanup_task:
        cleanup_task.cancel()
    
    # Stop all queues
    for queue in queues.values():
        await queue.stop()
    
    # Disconnect from MongoDB
    await mongodb.disconnect()
    
    logger.info("AI Gateway shut down")


# Create FastAPI app
app = FastAPI(
    title="AI Gateway",
    description="Production-grade AI model gateway with intelligent routing",
    version="1.0.0",
    lifespan=lifespan
)

# Set maximum request body size (10MB for images/PDFs)
app.add_middleware(
    lambda app: app,
    max_upload_size=10 * 1024 * 1024  # 10MB
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def periodic_cleanup():
    """Periodic cleanup of old data"""
    while True:
        try:
            await asyncio.sleep(86400)  # Run daily
            await mongodb.cleanup_old_data()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# Authentication endpoints
@app.post("/auth/token")
async def login(username: str, password: str):
    """
    Get JWT tokens
    
    In production, validate against user database
    For now, simple demo authentication
    """
    # TODO: Validate against user database
    if username and password:
        tokens = create_tokens(user_id=username, client_id="default")
        return tokens
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


# Chat/Completion endpoint (Gemma)
@app.post("/api/chat")
async def chat_completion(
    request: Request,
    user: Dict = Depends(get_current_user),
    x_client_id: Optional[str] = Header(None, alias="X-Client-ID"),
    x_model: Optional[str] = Header("gemma-3-4b-it", alias="X-Model"),
    x_task_type: Optional[str] = Header("chat", alias="X-Task-Type"),
    x_priority: Optional[str] = Header("normal", alias="X-Priority")
):
    """
    Chat completion endpoint
    Routes to Gemma-3-4B model
    """
    payload = await request.json()
    
    # Determine model
    model_name = "gemma"
    
    # Check if model exists
    if model_name not in queues:
        await mongodb.log_missing_model(model_name, x_client_id or user["client_id"])
        raise HTTPException(status_code=404, detail=f"Model {model_name} not available")
    
    # Enqueue request
    try:
        priority = Priority(x_priority.lower())
        request_id = await queues[model_name].enqueue(
            payload=payload,
            task_type=x_task_type,
            client_id=x_client_id or user["client_id"],
            priority=priority
        )
        
        # Process request (simplified - would integrate with actual model)
        # For now, return request ID
        return {
            "request_id": request_id,
            "status": "queued",
            "message": "Request queued for processing"
        }
    
    except QueueFullError:
        raise HTTPException(status_code=503, detail="Queue is full, please try again later")


# OCR endpoint (DeepSeek)
@app.post("/api/ocr")
async def ocr_processing(
    request: Request,
    user: Dict = Depends(get_current_user),
    x_client_id: Optional[str] = Header(None, alias="X-Client-ID"),
    x_model: Optional[str] = Header("deepseek-ocr", alias="X-Model"),
    x_task_type: Optional[str] = Header("ocr", alias="X-Task-Type"),
    x_priority: Optional[str] = Header("normal", alias="X-Priority"),
    x_resolution: Optional[str] = Header("large", alias="X-Resolution")
):
    """
    OCR processing endpoint
    Routes to DeepSeek-OCR model
    Supports dynamic resolution switching
    """
    payload = await request.json()
    
    model_name = "deepseek"
    
    # Check if model exists
    if model_name not in queues:
        await mongodb.log_missing_model(model_name, x_client_id or user["client_id"])
        raise HTTPException(status_code=404, detail=f"Model {model_name} not available")
    
    # Handle resolution switching if needed
    if x_resolution:
        try:
            resolution = OCRResolution(x_resolution.lower())
            # Check if we need to switch resolution
            model_status = await model_manager.get_model_status(model_name)
            if model_status and model_status["resolution"] != resolution:
                # Check if queue is empty before switching
                queue_metrics = queues[model_name].get_metrics()
                if queue_metrics["processing"] == 0:
                    logger.info(f"Switching OCR resolution to {resolution}")
                    await model_manager.switch_ocr_resolution(resolution, graceful=True)
        except ValueError:
            logger.warning(f"Invalid resolution: {x_resolution}")
    
    # Enqueue request
    try:
        priority = Priority(x_priority.lower())
        request_id = await queues[model_name].enqueue(
            payload=payload,
            task_type=x_task_type,
            client_id=x_client_id or user["client_id"],
            priority=priority
        )
        
        return {
            "request_id": request_id,
            "status": "queued",
            "resolution": x_resolution,
            "message": "Request queued for OCR processing"
        }
    
    except QueueFullError:
        raise HTTPException(status_code=503, detail="Queue is full, please try again later")


# Admin endpoints
@app.get("/admin/models")
async def get_models_status(user: Dict = Depends(get_current_user)):
    """Get status of all models"""
    return await model_manager.get_all_status()


@app.post("/admin/models/{model_name}/start")
async def start_model(
    model_name: str,
    resolution: Optional[str] = None,
    user: Dict = Depends(get_current_user)
):
    """Start a model"""
    res = OCRResolution(resolution) if resolution else None
    success = await model_manager.start_model(model_name, res)
    
    if success:
        return {"status": "started", "model": model_name}
    else:
        raise HTTPException(status_code=500, detail="Failed to start model")


@app.post("/admin/models/{model_name}/stop")
async def stop_model(
    model_name: str,
    graceful: bool = True,
    user: Dict = Depends(get_current_user)
):
    """Stop a model"""
    success = await model_manager.stop_model(model_name, graceful=graceful)
    
    if success:
        return {"status": "stopped", "model": model_name}
    else:
        raise HTTPException(status_code=500, detail="Failed to stop model")


@app.post("/admin/ocr/resolution")
async def switch_ocr_resolution(
    resolution: str,
    graceful: bool = True,
    user: Dict = Depends(get_current_user)
):
    """Switch DeepSeek-OCR resolution mode"""
    try:
        res = OCRResolution(resolution.lower())
        success = await model_manager.switch_ocr_resolution(res, graceful=graceful)
        
        if success:
            return {
                "status": "switched",
                "resolution": resolution,
                "message": f"OCR resolution switched to {resolution}"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to switch resolution")
    
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid resolution: {resolution}")


@app.get("/admin/queue/{model_name}")
async def get_queue_metrics(
    model_name: str,
    user: Dict = Depends(get_current_user)
):
    """Get queue metrics for a model"""
    if model_name not in queues:
        raise HTTPException(status_code=404, detail=f"Queue for {model_name} not found")
    
    return queues[model_name].get_metrics()


@app.get("/admin/crashes")
async def get_crash_logs(
    limit: int = 100,
    user: Dict = Depends(get_current_user)
):
    """Get crash logs"""
    return await mongodb.get_crash_logs(limit=limit)


@app.get("/admin/missing-models")
async def get_missing_model_requests(
    limit: int = 100,
    user: Dict = Depends(get_current_user)
):
    """Get requests for missing models"""
    return await mongodb.get_missing_model_requests(limit=limit)


if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run(
        "app.main:app",
        host=config.server.host,
        port=config.server.port,
        workers=config.server.workers,
        reload=config.server.reload
    )

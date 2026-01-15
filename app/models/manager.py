"""
Model Lifecycle Manager
Manages starting, stopping, and switching between AI models
Includes dynamic resolution switching for DeepSeek-OCR
"""

import asyncio
import subprocess
import time
import logging
from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime
import httpx

from app.config import get_config, ModelConfig


logger = logging.getLogger(__name__)


class ModelStatus(str, Enum):
    """Model status states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class OCRResolution(str, Enum):
    """DeepSeek-OCR resolution modes"""
    TINY = "tiny"      # 512×512
    SMALL = "small"    # 640×640
    BASE = "base"      # 1024×1024
    LARGE = "large"    # 1280×1280
    GUNDAM = "gundam"  # Dynamic n×640×640 + 1×1024×1024


class ModelManager:
    """
    Manages AI model lifecycle with intelligent switching
    
    Features:
    - Start/stop models dynamically
    - Graceful shutdown (wait for active requests)
    - Dynamic resolution switching for OCR
    - Health monitoring
    - Crash recovery
    """
    
    def __init__(self):
        self.config = get_config()
        self.models: Dict[str, ModelInfo] = {}
        self.current_model: Optional[str] = None
        self.switching_lock = asyncio.Lock()
        
        # Initialize model info
        for model_name, model_config in self.config.models.items():
            self.models[model_name] = ModelInfo(
                name=model_name,
                config=model_config,
                status=ModelStatus.STOPPED
            )
        
        logger.info(f"ModelManager initialized with {len(self.models)} models")
    
    async def start_model(
        self,
        model_name: str,
        resolution: Optional[OCRResolution] = None
    ) -> bool:
        """
        Start a model
        
        Args:
            model_name: Name of model to start
            resolution: OCR resolution mode (for DeepSeek-OCR only)
        
        Returns:
            True if started successfully
        """
        if model_name not in self.models:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        model_info = self.models[model_name]
        
        if model_info.status == ModelStatus.RUNNING:
            logger.info(f"Model {model_name} already running")
            return True
        
        logger.info(f"Starting model {model_name}...")
        model_info.status = ModelStatus.STARTING
        
        try:
            # Build vLLM command
            cmd = self._build_vllm_command(model_name, resolution)
            
            # Start process
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=lambda: None
            )
            
            model_info.process = process
            model_info.started_at = datetime.utcnow()
            
            # Wait for model to be ready
            if await self._wait_for_health(model_info.config.port, timeout=120):
                model_info.status = ModelStatus.RUNNING
                self.current_model = model_name
                logger.info(f"Model {model_name} started successfully")
                return True
            else:
                logger.error(f"Model {model_name} failed to start (health check timeout)")
                model_info.status = ModelStatus.ERROR
                return False
        
        except Exception as e:
            logger.error(f"Failed to start model {model_name}: {e}")
            model_info.status = ModelStatus.ERROR
            return False
    
    async def stop_model(
        self,
        model_name: str,
        graceful: bool = True,
        timeout: int = 60
    ) -> bool:
        """
        Stop a model
        
        Args:
            model_name: Name of model to stop
            graceful: Wait for active requests to complete
            timeout: Max seconds to wait for graceful shutdown
        
        Returns:
            True if stopped successfully
        """
        if model_name not in self.models:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        model_info = self.models[model_name]
        
        if model_info.status == ModelStatus.STOPPED:
            logger.info(f"Model {model_name} already stopped")
            return True
        
        logger.info(f"Stopping model {model_name} (graceful={graceful})...")
        model_info.status = ModelStatus.STOPPING
        
        try:
            if graceful:
                # Wait for active requests to complete
                start_time = time.time()
                while time.time() - start_time < timeout:
                    # Check if model has active requests
                    # This would integrate with the queue system
                    active_requests = await self._get_active_requests(model_name)
                    if active_requests == 0:
                        break
                    await asyncio.sleep(1)
                
                if time.time() - start_time >= timeout:
                    logger.warning(f"Graceful shutdown timeout for {model_name}, forcing stop")
            
            # Kill the process
            if model_info.process:
                model_info.process.terminate()
                try:
                    model_info.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    model_info.process.kill()
                    model_info.process.wait()
            
            # Also kill via pkill as backup
            subprocess.run(
                f"pkill -f '{model_info.config.name}'",
                shell=True,
                capture_output=True
            )
            
            model_info.status = ModelStatus.STOPPED
            model_info.process = None
            model_info.stopped_at = datetime.utcnow()
            
            if self.current_model == model_name:
                self.current_model = None
            
            logger.info(f"Model {model_name} stopped successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to stop model {model_name}: {e}")
            model_info.status = ModelStatus.ERROR
            return False
    
    async def switch_model(
        self,
        target_model: str,
        resolution: Optional[OCRResolution] = None
    ) -> bool:
        """
        Switch from current model to target model
        
        Args:
            target_model: Model to switch to
            resolution: OCR resolution (for DeepSeek-OCR)
        
        Returns:
            True if switched successfully
        """
        async with self.switching_lock:
            logger.info(f"Switching to model {target_model}")
            
            # Stop current model if different
            if self.current_model and self.current_model != target_model:
                await self.stop_model(self.current_model, graceful=True)
            
            # Start target model
            return await self.start_model(target_model, resolution)
    
    async def switch_ocr_resolution(
        self,
        resolution: OCRResolution,
        graceful: bool = True
    ) -> bool:
        """
        Switch DeepSeek-OCR resolution mode
        
        This will:
        1. Check if OCR has active requests
        2. If graceful=True, wait for them to complete
        3. Stop the OCR model
        4. Restart with new resolution
        
        Args:
            resolution: Target resolution mode
            graceful: Wait for active requests
        
        Returns:
            True if switched successfully
        """
        model_name = "deepseek"
        
        if model_name not in self.models:
            logger.error("DeepSeek-OCR not configured")
            return False
        
        model_info = self.models[model_name]
        
        # Check if already at target resolution
        if model_info.current_resolution == resolution:
            logger.info(f"Already at resolution {resolution}")
            return True
        
        logger.info(f"Switching DeepSeek-OCR from {model_info.current_resolution} to {resolution}")
        
        async with self.switching_lock:
            # Stop current OCR instance
            if model_info.status == ModelStatus.RUNNING:
                await self.stop_model(model_name, graceful=graceful)
            
            # Start with new resolution
            success = await self.start_model(model_name, resolution)
            
            if success:
                model_info.current_resolution = resolution
                logger.info(f"Successfully switched to {resolution} mode")
            
            return success
    
    async def get_model_status(self, model_name: str) -> Optional[Dict]:
        """Get detailed status of a model"""
        if model_name not in self.models:
            return None
        
        model_info = self.models[model_name]
        
        return {
            "name": model_name,
            "status": model_info.status,
            "port": model_info.config.port,
            "started_at": model_info.started_at.isoformat() if model_info.started_at else None,
            "uptime_seconds": (datetime.utcnow() - model_info.started_at).total_seconds() if model_info.started_at else 0,
            "resolution": model_info.current_resolution if model_name == "deepseek" else None,
            "is_healthy": await self._check_health(model_info.config.port)
        }
    
    async def get_all_status(self) -> Dict:
        """Get status of all models"""
        status = {}
        for model_name in self.models:
            status[model_name] = await self.get_model_status(model_name)
        return status
    
    def _build_vllm_command(
        self,
        model_name: str,
        resolution: Optional[OCRResolution] = None
    ) -> str:
        """Build vLLM serve command"""
        model_info = self.models[model_name]
        config = model_info.config
        
        # Determine environment and activation
        if model_name == "gemma":
            env_path = "/root/server_ai/vllm-workspace/vllm_env"
        elif model_name == "deepseek":
            env_path = "/root/server_ai/deepseek_ocr_env"
        else:
            env_path = "/root/server_ai/vllm-workspace/vllm_env"
        
        # Base command
        cmd = f"cd /root/server_ai && source {env_path}/bin/activate && "
        cmd += f"vllm serve {config.name} "
        cmd += f"--host 0.0.0.0 "
        cmd += f"--port {config.port} "
        cmd += f"--gpu-memory-utilization {config.gpu_memory} "
        cmd += f"--max-model-len {config.max_model_len} "
        cmd += f"--max-num-seqs {config.max_concurrent} "
        
        # Add resolution-specific settings for DeepSeek-OCR
        if model_name == "deepseek" and resolution:
            model_info.current_resolution = resolution
            # Note: Resolution is handled at inference time via image preprocessing
            # We just track it here for API routing
        
        # Redirect output to log file
        log_file = f"/root/server_ai/backend_ai/logs/{model_name}_server.log"
        cmd += f"> {log_file} 2>&1 &"
        
        return cmd
    
    async def _wait_for_health(self, port: int, timeout: int = 120) -> bool:
        """Wait for model to be healthy"""
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get(
                        f"http://localhost:{port}/health",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        return True
                except:
                    pass
                
                await asyncio.sleep(2)
        
        return False
    
    async def _check_health(self, port: int) -> bool:
        """Check if model is healthy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{port}/health",
                    timeout=5.0
                )
                return response.status_code == 200
        except:
            return False
    
    async def _get_active_requests(self, model_name: str) -> int:
        """Get number of active requests for a model"""
        # This would integrate with the queue system
        # For now, return 0 as placeholder
        return 0


class ModelInfo:
    """Stores information about a model instance"""
    
    def __init__(self, name: str, config: ModelConfig, status: ModelStatus):
        self.name = name
        self.config = config
        self.status = status
        self.process: Optional[subprocess.Popen] = None
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.current_resolution: Optional[OCRResolution] = None
        
        # Set default resolution for DeepSeek-OCR
        if name == "deepseek" and config.resolution_mode:
            self.current_resolution = OCRResolution(config.resolution_mode)

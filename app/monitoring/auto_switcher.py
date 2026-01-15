"""
Auto-Switching Service
Automatically switches models based on usage patterns
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.config import get_config
from app.monitoring.pattern_analyzer import PatternAnalyzer


logger = logging.getLogger(__name__)


class AutoSwitcher:
    """
    Automatic model switching based on usage patterns
    
    Features:
    - Monitors usage patterns
    - Switches to frequently used model
    - Respects cooldown period
    - Graceful switching (waits for queue to be idle)
    """
    
    def __init__(self, model_manager, queues: dict):
        self.config = get_config().auto_switch
        self.model_manager = model_manager
        self.queues = queues
        
        self.pattern_analyzer = PatternAnalyzer(
            window_days=self.config.pattern_window_days,
            min_requests=self.config.min_requests_for_switch
        )
        
        self.last_switch: Optional[datetime] = None
        self.task: Optional[asyncio.Task] = None
        self.running = False
        
        logger.info(f"AutoSwitcher initialized (enabled={self.config.enabled})")
    
    async def start(self):
        """Start auto-switching service"""
        if not self.config.enabled:
            logger.info("Auto-switching is disabled")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._switching_loop())
        logger.info("Auto-switching service started")
    
    async def stop(self):
        """Stop auto-switching service"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-switching service stopped")
    
    async def _switching_loop(self):
        """Main switching loop"""
        while self.running:
            try:
                # Wait for check interval (e.g., every 5 minutes)
                await asyncio.sleep(self.config.switch_cooldown_minutes * 60)
                
                # Check if we should switch
                await self._check_and_switch()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-switching loop: {e}")
    
    async def _check_and_switch(self):
        """Check patterns and switch if needed"""
        # Check cooldown
        if self.last_switch:
            time_since_switch = datetime.utcnow() - self.last_switch
            cooldown = timedelta(minutes=self.config.switch_cooldown_minutes)
            
            if time_since_switch < cooldown:
                logger.debug(f"In cooldown period ({time_since_switch} < {cooldown})")
                return
        
        # Get current model
        current_model = self.model_manager.current_model
        
        # Analyze patterns
        recommended = await self.pattern_analyzer.should_switch_model(current_model)
        
        if not recommended:
            logger.debug("No model switch recommended")
            return
        
        # Check if queues are idle
        if not await self._are_queues_idle():
            logger.info("Queues not idle, postponing switch")
            return
        
        # Perform switch
        logger.info(f"Auto-switching from {current_model} to {recommended}")
        
        success = await self.model_manager.switch_model(recommended)
        
        if success:
            self.last_switch = datetime.utcnow()
            logger.info(f"Successfully switched to {recommended}")
        else:
            logger.error(f"Failed to switch to {recommended}")
    
    async def _are_queues_idle(self) -> bool:
        """Check if all queues are idle (no processing requests)"""
        for queue in self.queues.values():
            metrics = queue.get_metrics()
            if metrics["processing"] > 0:
                return False
        return True
    
    async def get_status(self) -> dict:
        """Get auto-switcher status"""
        analysis = await self.pattern_analyzer.analyze_patterns()
        
        return {
            "enabled": self.config.enabled,
            "running": self.running,
            "last_switch": self.last_switch.isoformat() if self.last_switch else None,
            "current_model": self.model_manager.current_model,
            "pattern_analysis": analysis
        }

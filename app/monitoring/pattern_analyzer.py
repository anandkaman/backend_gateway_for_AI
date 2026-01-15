"""
Pattern Analyzer
Analyzes usage patterns to determine which model to keep loaded
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List
from collections import defaultdict
import logging

from app.database.mongodb import mongodb


logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """
    Analyzes request patterns to optimize model switching
    
    Features:
    - Track model usage over time
    - Identify frequently used models
    - Recommend which model to keep loaded
    - Pattern-based auto-switching
    """
    
    def __init__(self, window_days: int = 7, min_requests: int = 10):
        self.window_days = window_days
        self.min_requests = min_requests
        self._cache: Dict[str, int] = {}
        self._last_analysis: Optional[datetime] = None
    
    async def analyze_patterns(self) -> Dict[str, any]:
        """
        Analyze usage patterns over the window period
        
        Returns:
            Analysis results with recommendations
        """
        start_time = datetime.utcnow() - timedelta(days=self.window_days)
        
        # Get request history from MongoDB
        requests = await mongodb.get_request_history(limit=10000)
        
        # Count requests per model
        model_counts = defaultdict(int)
        model_recent = defaultdict(int)  # Last 24 hours
        
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        
        for req in requests:
            created_at = req.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            if created_at >= start_time:
                model_name = req.get('model_name')
                model_counts[model_name] += 1
                
                if created_at >= recent_cutoff:
                    model_recent[model_name] += 1
        
        # Calculate usage percentages
        total_requests = sum(model_counts.values())
        
        if total_requests == 0:
            return {
                "total_requests": 0,
                "recommended_model": None,
                "reason": "No requests in analysis window"
            }
        
        usage_percentages = {
            model: (count / total_requests) * 100
            for model, count in model_counts.items()
        }
        
        # Determine recommended model
        recommended_model = max(model_counts.items(), key=lambda x: x[1])[0]
        
        # Check if recommendation is strong enough
        if model_counts[recommended_model] < self.min_requests:
            return {
                "total_requests": total_requests,
                "model_counts": dict(model_counts),
                "usage_percentages": usage_percentages,
                "recent_counts": dict(model_recent),
                "recommended_model": None,
                "reason": f"Insufficient requests ({model_counts[recommended_model]} < {self.min_requests})"
            }
        
        # Calculate confidence score
        confidence = usage_percentages[recommended_model] / 100.0
        
        self._last_analysis = datetime.utcnow()
        
        return {
            "total_requests": total_requests,
            "model_counts": dict(model_counts),
            "usage_percentages": usage_percentages,
            "recent_counts": dict(model_recent),
            "recommended_model": recommended_model,
            "confidence": confidence,
            "reason": f"{recommended_model} used in {usage_percentages[recommended_model]:.1f}% of requests",
            "analyzed_at": self._last_analysis.isoformat()
        }
    
    async def should_switch_model(self, current_model: Optional[str]) -> Optional[str]:
        """
        Determine if we should switch to a different model
        
        Args:
            current_model: Currently loaded model
        
        Returns:
            Model name to switch to, or None if no switch needed
        """
        analysis = await self.analyze_patterns()
        
        recommended = analysis.get('recommended_model')
        
        if not recommended:
            return None
        
        # Don't switch if already on recommended model
        if current_model == recommended:
            return None
        
        # Check confidence threshold (at least 60% usage)
        confidence = analysis.get('confidence', 0)
        if confidence < 0.6:
            logger.info(f"Confidence too low for switch: {confidence:.2%}")
            return None
        
        logger.info(f"Recommending switch from {current_model} to {recommended} (confidence: {confidence:.2%})")
        return recommended
    
    async def get_usage_stats(self, days: int = 7) -> Dict:
        """Get detailed usage statistics"""
        start_time = datetime.utcnow() - timedelta(days=days)
        
        requests = await mongodb.get_request_history(limit=10000)
        
        # Daily breakdown
        daily_counts = defaultdict(lambda: defaultdict(int))
        
        for req in requests:
            created_at = req.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            
            if created_at >= start_time:
                date_key = created_at.date().isoformat()
                model_name = req.get('model_name')
                daily_counts[date_key][model_name] += 1
        
        return {
            "period_days": days,
            "daily_breakdown": dict(daily_counts),
            "total_days": len(daily_counts)
        }

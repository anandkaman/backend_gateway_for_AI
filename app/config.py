"""
Configuration Management
Loads and validates configuration from YAML files
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class ServerConfig(BaseModel):
    """Server configuration"""
    host: str = "0.0.0.0"
    port: int = 8080
    workers: int = 4
    reload: bool = False


class ModelConfig(BaseModel):
    """Individual model configuration"""
    name: str
    port: int
    gpu_memory: float = Field(ge=0.1, le=1.0)
    max_model_len: int = Field(gt=0)
    max_concurrent: int = Field(gt=0)
    enabled: bool = True
    resolution_mode: Optional[str] = None  # For OCR models


class QueueConfig(BaseModel):
    """Queue system configuration"""
    max_waiting: int = Field(default=10, gt=0)
    timeout: int = Field(default=300, gt=0)
    priority_enabled: bool = True
    persistence_enabled: bool = True  # Crash recovery
    recovery_check_interval: int = 60  # seconds


class AutoSwitchConfig(BaseModel):
    """Auto-switching configuration"""
    enabled: bool = True
    pattern_window_days: int = Field(default=7, gt=0)
    min_requests_for_switch: int = Field(default=10, gt=0)
    switch_cooldown_minutes: int = Field(default=5, gt=0)


class AuthConfig(BaseModel):
    """Authentication configuration"""
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7


class MongoDBConfig(BaseModel):
    """MongoDB configuration"""
    uri: str
    database: str = "ai_gateway"
    history_retention_days: int = 15
    
    class Collections(BaseModel):
        requests: str = "request_history"
        crashes: str = "crash_logs"
        metrics: str = "metrics"
        missing_models: str = "missing_model_requests"
        queue_state: str = "queue_state"  # For crash recovery
    
    collections: Collections = Collections()


class MonitoringConfig(BaseModel):
    """Monitoring configuration"""
    enabled: bool = True
    metrics_interval_seconds: int = 60
    crash_detection: bool = True
    log_level: str = "INFO"


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    enabled: bool = True
    requests_per_minute: int = 60
    burst: int = 10


class Config(BaseSettings):
    """Main configuration class"""
    server: ServerConfig
    models: Dict[str, ModelConfig]
    queue: QueueConfig
    auto_switch: AutoSwitchConfig
    auth: AuthConfig
    mongodb: MongoDBConfig
    monitoring: MonitoringConfig
    rate_limit: RateLimitConfig
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def load_config(config_path: str = "config/config.yaml") -> Config:
    """Load configuration from YAML file"""
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Replace environment variables
    config_data = _replace_env_vars(config_data)
    
    return Config(**config_data)


def _replace_env_vars(data: Any) -> Any:
    """Recursively replace ${VAR} with environment variables"""
    if isinstance(data, dict):
        return {k: _replace_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_replace_env_vars(item) for item in data]
    elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
        var_name = data[2:-1]
        return os.getenv(var_name, data)
    return data


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> Config:
    """Reload configuration from file"""
    global _config
    _config = load_config()
    return _config

"""
OpenAI Configuration Management for Phase 3 Agents
"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class OpenAIConfig:
    """OpenAI API configuration for agents"""
    api_key: str
    organization: Optional[str] = None
    base_url: Optional[str] = None
    
    # Model configurations
    conversation_model: str = "gpt-4o"
    intent_model: str = "gpt-4o-mini"
    planning_model: str = "gpt-4o"
    response_model: str = "gpt-4o-mini"
    coordination_model: str = "gpt-4o-mini"
    
    # Temperature settings
    conversation_temperature: float = 0.7
    intent_temperature: float = 0.1
    planning_temperature: float = 0.3
    response_temperature: float = 0.7
    coordination_temperature: float = 0.1
    
    # Token limits
    max_tokens: int = 4096
    max_conversation_tokens: int = 8192
    
    # Timeout settings
    request_timeout: int = 30
    long_request_timeout: int = 60
    
    @classmethod
    def from_env(cls) -> "OpenAIConfig":
        """Load configuration from environment variables"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for Phase 3 orchestration"
            )
        
        return cls(
            api_key=api_key,
            organization=os.getenv("OPENAI_ORGANIZATION"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            # Allow model overrides from environment
            conversation_model=os.getenv("OPENAI_CONVERSATION_MODEL", "gpt-4o"),
            intent_model=os.getenv("OPENAI_INTENT_MODEL", "gpt-4o-mini"),
            planning_model=os.getenv("OPENAI_PLANNING_MODEL", "gpt-4o"),
            response_model=os.getenv("OPENAI_RESPONSE_MODEL", "gpt-4o-mini"),
            coordination_model=os.getenv("OPENAI_COORDINATION_MODEL", "gpt-4o-mini"),
        )


@dataclass
class RedisConfig:
    """Redis configuration for caching and state management"""
    url: str = "redis://localhost:6379"
    max_connections: int = 10
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    socket_keepalive: bool = True
    socket_keepalive_options: Optional[dict] = None
    
    # Cache TTL settings (in seconds)
    default_ttl: int = 300  # 5 minutes
    device_ttl: int = 3600  # 1 hour
    interface_ttl: int = 300  # 5 minutes
    vlan_ttl: int = 1800  # 30 minutes
    cable_ttl: int = 7200  # 2 hours
    
    @classmethod
    def from_env(cls) -> "RedisConfig":
        """Load configuration from environment variables"""
        return cls(
            url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
            default_ttl=int(os.getenv("REDIS_DEFAULT_TTL", "300")),
        )


@dataclass
class OrchestrationConfig:
    """Overall orchestration configuration"""
    openai: OpenAIConfig
    redis: RedisConfig
    
    # Performance settings
    enable_caching: bool = True
    enable_parallel_execution: bool = True
    max_parallel_operations: int = 5
    
    # Limitation handling
    enable_workarounds: bool = True
    graceful_degradation: bool = True
    
    # Progress tracking
    enable_progress_streaming: bool = True
    progress_update_interval: float = 1.0  # seconds
    
    # Debug settings
    debug_mode: bool = False
    log_openai_requests: bool = False
    log_cache_operations: bool = False
    
    @classmethod
    def from_env(cls) -> "OrchestrationConfig":
        """Load complete orchestration configuration"""
        return cls(
            openai=OpenAIConfig.from_env(),
            redis=RedisConfig.from_env(),
            enable_caching=os.getenv("ENABLE_CACHING", "true").lower() == "true",
            enable_parallel_execution=os.getenv("ENABLE_PARALLEL", "true").lower() == "true",
            enable_workarounds=os.getenv("ENABLE_WORKAROUNDS", "true").lower() == "true",
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
        )


# Global configuration instance
_config: Optional[OrchestrationConfig] = None


def get_config() -> OrchestrationConfig:
    """Get or create the global configuration instance"""
    global _config
    if _config is None:
        _config = OrchestrationConfig.from_env()
    return _config


def set_config(config: OrchestrationConfig) -> None:
    """Set the global configuration instance (mainly for testing)"""
    global _config
    _config = config
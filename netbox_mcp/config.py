#!/usr/bin/env python3
"""
Configuration management for NetBox MCP Server

Supports YAML and TOML configuration files with environment variable overrides.
Configuration hierarchy (highest priority first):
1. Environment variables
2. Configuration file
3. Default values

Safety-focused configuration with write operation controls.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field

try:
    import yaml
except ImportError:
    yaml = None

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python versions
    except ImportError:
        tomllib = None

logger = logging.getLogger(__name__)


@dataclass
class SafetyConfig:
    """Safety configuration for write operations."""
    
    # Global safety controls
    dry_run_mode: bool = False              # Global dry-run mode
    require_confirmation: bool = True       # Require confirm=True for write ops
    enable_write_operations: bool = True    # Master switch for all write ops
    
    # Operation timeouts and limits
    write_timeout: int = 60                 # Timeout for write operations
    max_batch_size: int = 100              # Maximum objects per batch operation
    
    # Audit and logging
    audit_all_operations: bool = True       # Log all operations (read/write)
    audit_write_details: bool = True        # Detailed logging for write operations
    
    # Rollback and recovery
    enable_transaction_mode: bool = True    # Enable transaction-like operations
    auto_rollback_on_error: bool = True     # Auto-rollback on partial failures


@dataclass
class CacheTTLConfig:
    """TTL configuration for different data types."""
    
    # Core NetBox operations
    devices: int = 300                      # Device lists and lookups
    sites: int = 3600                       # Site information (rarely changes)
    manufacturers: int = 7200               # Manufacturer data (very stable)
    device_types: int = 7200               # Device types (very stable)
    device_roles: int = 7200               # Device roles (very stable)
    
    # IPAM operations
    ip_addresses: int = 600                 # IP address data
    prefixes: int = 1800                   # Network prefixes
    vlans: int = 1800                      # VLAN information
    
    # Relationships and complex queries
    device_interfaces: int = 600            # Device interface data
    device_connections: int = 600           # Device connection data
    topology_data: int = 3600              # Network topology analysis
    
    # System and status
    status: int = 60                       # NetBox status information
    health: int = 60                       # Health check data
    
    # Default TTL for unlisted operations
    default: int = 300


@dataclass
class CacheConfig:
    """Configuration for response caching."""
    
    # Basic settings
    enabled: bool = True
    backend: str = "memory"                 # 'memory' or 'disk'
    
    # Size limits
    size_limit_mb: int = 200               # Cache size limit in megabytes
    max_items: int = 2000                  # Maximum number of cached items
    
    # File-based cache settings (disk backend only)
    path: Optional[str] = "/tmp/netbox_mcp_cache"
    
    # TTL configuration
    ttl: CacheTTLConfig = field(default_factory=CacheTTLConfig)
    
    # Advanced features
    warm_on_startup: bool = False          # Whether to warm cache on startup
    compression: bool = False              # Whether to compress cached data
    
    # Statistics
    enable_stats: bool = True              # Whether to track cache statistics


@dataclass
class NetBoxConfig:
    """Configuration settings for NetBox MCP Server"""
    
    # Required NetBox connection settings
    url: str = ""
    token: str = ""
    
    # Optional connection settings
    timeout: int = 30
    verify_ssl: bool = True
    
    # Server settings
    log_level: str = "INFO"
    health_check_port: int = 8080
    
    # Safety configuration (CRITICAL)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    
    # Performance settings
    default_page_size: int = 50            # Smaller default for NetBox
    max_results: int = 1000
    
    # Feature flags
    enable_health_server: bool = True
    enable_degraded_mode: bool = True
    enable_read_operations: bool = True
    
    # Advanced settings
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Cache configuration
    cache: CacheConfig = field(default_factory=CacheConfig)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.url:
            raise ValueError("NetBox URL must be specified (NETBOX_URL)")
        if not self.token:
            raise ValueError("NetBox API token must be specified (NETBOX_TOKEN)")
        
        # Normalize URL
        self.url = self.url.rstrip('/')
        
        # Validate URL format
        if not (self.url.startswith('http://') or self.url.startswith('https://')):
            raise ValueError("NetBox URL must start with http:// or https://")
        
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.log_level}. Must be one of {valid_levels}")
        
        # Validate numeric values
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.health_check_port <= 0 or self.health_check_port > 65535:
            raise ValueError("Health check port must be between 1 and 65535")
        if self.default_page_size <= 0:
            raise ValueError("Default page size must be positive")
        if self.max_results <= 0:
            raise ValueError("Max results must be positive")
        
        # Safety validations
        if self.safety.write_timeout <= 0:
            raise ValueError("Write timeout must be positive")
        if self.safety.max_batch_size <= 0:
            raise ValueError("Max batch size must be positive")
        
        # Log safety configuration warnings
        if self.safety.dry_run_mode:
            logger.warning("NetBox MCP running in DRY-RUN mode - no actual writes will be performed")
        
        if not self.safety.require_confirmation:
            logger.warning("Confirmation requirement DISABLED - write operations can execute without confirm=True")
        
        if not self.safety.enable_write_operations:
            logger.info("Write operations DISABLED - server will be read-only")


class ConfigurationManager:
    """Manages configuration loading from multiple sources"""
    
    DEFAULT_CONFIG_PATHS = [
        "netbox-mcp.yaml",
        "netbox-mcp.yml", 
        "netbox-mcp.toml",
        "config/netbox-mcp.yaml",
        "config/netbox-mcp.yml",
        "config/netbox-mcp.toml",
        ".netbox-mcp.yaml",
        ".netbox-mcp.yml",
        ".netbox-mcp.toml",
        "/etc/netbox-mcp/config.yaml",
        "/etc/netbox-mcp/config.yml",
        "/etc/netbox-mcp/config.toml",
    ]
    
    ENV_PREFIX = "NETBOX_"
    
    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> NetBoxConfig:
        """
        Load configuration from environment variables and optional config file.
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            NetBoxConfig: Loaded and validated configuration
        """
        # Start with default configuration
        config_data = {}
        
        # Load from configuration file if found
        if config_path or cls._find_config_file():
            file_path = config_path or cls._find_config_file()
            config_data = cls._load_config_file(file_path)
            logger.info(f"Loaded configuration from {file_path}")
        
        # Override with environment variables
        env_config = cls._load_from_environment()
        config_data.update(env_config)
        
        # Create and validate configuration
        try:
            # Handle nested dataclass creation
            config_data = cls._process_nested_config(config_data)
            config = NetBoxConfig(**config_data)
            logger.info("Configuration loaded and validated successfully")
            return config
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    @classmethod
    def _find_config_file(cls) -> Optional[str]:
        """Find the first existing configuration file from default paths."""
        for path in cls.DEFAULT_CONFIG_PATHS:
            if Path(path).exists():
                return path
        return None
    
    @classmethod
    def _load_config_file(cls, file_path: str) -> Dict[str, Any]:
        """Load configuration from YAML or TOML file."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    if yaml is None:
                        raise ImportError("PyYAML is required for YAML configuration files")
                    return yaml.safe_load(f) or {}
                elif path.suffix.lower() == '.toml':
                    if tomllib is None:
                        raise ImportError("tomli/tomllib is required for TOML configuration files")
                    content = f.read()
                    return tomllib.loads(content)
                else:
                    raise ValueError(f"Unsupported configuration file format: {path.suffix}")
        except Exception as e:
            logger.error(f"Failed to load configuration file {file_path}: {e}")
            raise
    
    @classmethod
    def _load_from_environment(cls) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        
        # Direct mappings for main config
        env_mappings = {
            'NETBOX_URL': 'url',
            'NETBOX_TOKEN': 'token',
            'NETBOX_TIMEOUT': ('timeout', int),
            'NETBOX_VERIFY_SSL': ('verify_ssl', cls._parse_bool),
            'NETBOX_LOG_LEVEL': 'log_level',
            'NETBOX_HEALTH_CHECK_PORT': ('health_check_port', int),
            'NETBOX_DEFAULT_PAGE_SIZE': ('default_page_size', int),
            'NETBOX_MAX_RESULTS': ('max_results', int),
            'NETBOX_ENABLE_HEALTH_SERVER': ('enable_health_server', cls._parse_bool),
            'NETBOX_ENABLE_DEGRADED_MODE': ('enable_degraded_mode', cls._parse_bool),
            'NETBOX_ENABLE_READ_OPERATIONS': ('enable_read_operations', cls._parse_bool),
        }
        
        # Safety configuration mappings
        safety_mappings = {
            'NETBOX_DRY_RUN': ('safety.dry_run_mode', cls._parse_bool),
            'NETBOX_REQUIRE_CONFIRMATION': ('safety.require_confirmation', cls._parse_bool),
            'NETBOX_ENABLE_WRITE_OPERATIONS': ('safety.enable_write_operations', cls._parse_bool),
            'NETBOX_WRITE_TIMEOUT': ('safety.write_timeout', int),
            'NETBOX_MAX_BATCH_SIZE': ('safety.max_batch_size', int),
            'NETBOX_AUDIT_ALL_OPERATIONS': ('safety.audit_all_operations', cls._parse_bool),
            'NETBOX_AUDIT_WRITE_DETAILS': ('safety.audit_write_details', cls._parse_bool),
            'NETBOX_ENABLE_TRANSACTION_MODE': ('safety.enable_transaction_mode', cls._parse_bool),
            'NETBOX_AUTO_ROLLBACK_ON_ERROR': ('safety.auto_rollback_on_error', cls._parse_bool),
        }
        
        # Cache configuration mappings
        cache_mappings = {
            'NETBOX_CACHE_ENABLED': ('cache.enabled', cls._parse_bool),
            'NETBOX_CACHE_BACKEND': ('cache.backend', str),
            'NETBOX_CACHE_SIZE_LIMIT_MB': ('cache.size_limit_mb', int),
            'NETBOX_CACHE_MAX_ITEMS': ('cache.max_items', int),
            'NETBOX_CACHE_PATH': ('cache.path', str),
            'NETBOX_CACHE_ENABLE_STATS': ('cache.enable_stats', cls._parse_bool),
        }
        
        # Combine all mappings
        all_mappings = {**env_mappings, **safety_mappings, **cache_mappings}
        
        for env_var, config_key in all_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                if isinstance(config_key, tuple):
                    key, converter = config_key
                    try:
                        value = converter(value)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid value for {env_var}: {value} ({e})")
                        continue
                else:
                    key = config_key
                
                # Handle nested configuration
                cls._set_nested_value(config, key, value)
        
        return config
    
    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse boolean value from string."""
        if isinstance(value, bool):
            return value
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    @staticmethod
    def _set_nested_value(config: Dict[str, Any], key: str, value: Any):
        """Set nested configuration value using dot notation."""
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    @classmethod
    def _process_nested_config(cls, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process nested configuration to create proper dataclass instances."""
        processed = config_data.copy()
        
        # Handle safety configuration
        if 'safety' in processed and isinstance(processed['safety'], dict):
            processed['safety'] = SafetyConfig(**processed['safety'])
        
        # Handle cache configuration
        if 'cache' in processed and isinstance(processed['cache'], dict):
            cache_config = processed['cache'].copy()
            
            # Handle cache TTL configuration
            if 'ttl' in cache_config and isinstance(cache_config['ttl'], dict):
                cache_config['ttl'] = CacheTTLConfig(**cache_config['ttl'])
            
            processed['cache'] = CacheConfig(**cache_config)
        
        return processed


def load_config(config_path: Optional[str] = None) -> NetBoxConfig:
    """
    Convenience function to load configuration.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        NetBoxConfig: Loaded and validated configuration
    """
    return ConfigurationManager.load_config(config_path)
"""
Tests for NetBox MCP configuration management
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from netbox_mcp.config import (
    NetBoxConfig, 
    SafetyConfig, 
    CacheConfig, 
    CacheTTLConfig,
    ConfigurationManager,
    load_config
)


class TestNetBoxConfig:
    """Test NetBox configuration dataclass"""
    
    def test_minimal_config(self):
        """Test minimal valid configuration"""
        config = NetBoxConfig(
            url="https://netbox.example.com",
            token="test-token-123"
        )
        
        assert config.url == "https://netbox.example.com"
        assert config.token == "test-token-123"
        assert config.timeout == 30
        assert config.verify_ssl is True
        assert isinstance(config.safety, SafetyConfig)
        assert isinstance(config.cache, CacheConfig)
    
    def test_url_normalization(self):
        """Test URL normalization (removes trailing slash)"""
        config = NetBoxConfig(
            url="https://netbox.example.com/",
            token="test-token-123"
        )
        
        assert config.url == "https://netbox.example.com"
    
    def test_missing_url_raises_error(self):
        """Test that missing URL raises ValueError"""
        with pytest.raises(ValueError, match="NetBox URL must be specified"):
            NetBoxConfig(token="test-token")
    
    def test_missing_token_raises_error(self):
        """Test that missing token raises ValueError"""
        with pytest.raises(ValueError, match="NetBox API token must be specified"):
            NetBoxConfig(url="https://netbox.example.com")
    
    def test_invalid_url_format_raises_error(self):
        """Test that invalid URL format raises ValueError"""
        with pytest.raises(ValueError, match="NetBox URL must start with http"):
            NetBoxConfig(
                url="netbox.example.com",
                token="test-token"
            )
    
    def test_invalid_log_level_raises_error(self):
        """Test that invalid log level raises ValueError"""
        with pytest.raises(ValueError, match="Invalid log level"):
            NetBoxConfig(
                url="https://netbox.example.com",
                token="test-token",
                log_level="INVALID"
            )
    
    def test_negative_timeout_raises_error(self):
        """Test that negative timeout raises ValueError"""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            NetBoxConfig(
                url="https://netbox.example.com",
                token="test-token",
                timeout=-1
            )
    
    def test_invalid_port_raises_error(self):
        """Test that invalid port raises ValueError"""
        with pytest.raises(ValueError, match="Health check port must be between"):
            NetBoxConfig(
                url="https://netbox.example.com",
                token="test-token",
                health_check_port=70000
            )


class TestSafetyConfig:
    """Test safety configuration"""
    
    def test_default_safety_config(self):
        """Test default safety configuration"""
        config = SafetyConfig()
        
        assert config.dry_run_mode is False
        assert config.require_confirmation is True
        assert config.enable_write_operations is True
        assert config.write_timeout == 60
        assert config.max_batch_size == 100
        assert config.audit_all_operations is True
    
    def test_safety_config_customization(self):
        """Test safety configuration customization"""
        config = SafetyConfig(
            dry_run_mode=True,
            require_confirmation=False,
            write_timeout=120
        )
        
        assert config.dry_run_mode is True
        assert config.require_confirmation is False
        assert config.write_timeout == 120


class TestCacheConfig:
    """Test cache configuration"""
    
    def test_default_cache_config(self):
        """Test default cache configuration"""
        config = CacheConfig()
        
        assert config.enabled is True
        assert config.backend == "memory"
        assert config.size_limit_mb == 200
        assert isinstance(config.ttl, CacheTTLConfig)
    
    def test_cache_ttl_defaults(self):
        """Test cache TTL defaults"""
        ttl_config = CacheTTLConfig()
        
        assert ttl_config.devices == 300
        assert ttl_config.sites == 3600
        assert ttl_config.manufacturers == 7200
        assert ttl_config.default == 300


class TestConfigurationManager:
    """Test configuration manager"""
    
    def test_load_from_environment_basic(self):
        """Test loading basic configuration from environment"""
        env_vars = {
            'NETBOX_URL': 'https://netbox.test.com',
            'NETBOX_TOKEN': 'env-test-token',
            'NETBOX_TIMEOUT': '45',
            'NETBOX_VERIFY_SSL': 'false',
            'NETBOX_LOG_LEVEL': 'DEBUG'
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = ConfigurationManager.load_config()
        
        assert config.url == 'https://netbox.test.com'
        assert config.token == 'env-test-token'
        assert config.timeout == 45
        assert config.verify_ssl is False
        assert config.log_level == 'DEBUG'
    
    def test_load_from_environment_safety(self):
        """Test loading safety configuration from environment"""
        env_vars = {
            'NETBOX_URL': 'https://netbox.test.com',
            'NETBOX_TOKEN': 'test-token',
            'NETBOX_DRY_RUN': 'true',
            'NETBOX_REQUIRE_CONFIRMATION': 'false',
            'NETBOX_WRITE_TIMEOUT': '120'
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = ConfigurationManager.load_config()
        
        assert config.safety.dry_run_mode is True
        assert config.safety.require_confirmation is False
        assert config.safety.write_timeout == 120
    
    def test_load_from_environment_cache(self):
        """Test loading cache configuration from environment"""
        env_vars = {
            'NETBOX_URL': 'https://netbox.test.com',
            'NETBOX_TOKEN': 'test-token',
            'NETBOX_CACHE_ENABLED': 'false',
            'NETBOX_CACHE_BACKEND': 'disk',
            'NETBOX_CACHE_SIZE_LIMIT_MB': '500'
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = ConfigurationManager.load_config()
        
        assert config.cache.enabled is False
        assert config.cache.backend == 'disk'
        assert config.cache.size_limit_mb == 500
    
    def test_parse_bool_values(self):
        """Test boolean parsing from environment variables"""
        manager = ConfigurationManager()
        
        # Test true values
        for value in ['true', 'True', 'TRUE', '1', 'yes', 'on', 'enabled']:
            assert manager._parse_bool(value) is True
        
        # Test false values  
        for value in ['false', 'False', 'FALSE', '0', 'no', 'off', 'disabled']:
            assert manager._parse_bool(value) is False
    
    def test_load_yaml_config_file(self):
        """Test loading YAML configuration file"""
        yaml_content = """
url: "https://netbox.yaml.com"
token: "yaml-token-123"
timeout: 60
safety:
  dry_run_mode: true
  write_timeout: 90
cache:
  enabled: false
  backend: "disk"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                config = ConfigurationManager.load_config(f.name)
                
                assert config.url == "https://netbox.yaml.com"
                assert config.token == "yaml-token-123"
                assert config.timeout == 60
                assert config.safety.dry_run_mode is True
                assert config.safety.write_timeout == 90
                assert config.cache.enabled is False
                assert config.cache.backend == "disk"
            finally:
                os.unlink(f.name)
    
    def test_load_toml_config_file(self):
        """Test loading TOML configuration file"""
        toml_content = """
url = "https://netbox.toml.com"
token = "toml-token-123"
timeout = 45

[safety]
dry_run_mode = false
write_timeout = 75

[cache]
enabled = true
backend = "memory"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            
            try:
                config = ConfigurationManager.load_config(f.name)
                
                assert config.url == "https://netbox.toml.com"
                assert config.token == "toml-token-123"
                assert config.timeout == 45
                assert config.safety.dry_run_mode is False
                assert config.safety.write_timeout == 75
                assert config.cache.enabled is True
                assert config.cache.backend == "memory"
            finally:
                os.unlink(f.name)
    
    def test_environment_overrides_file(self):
        """Test that environment variables override file configuration"""
        yaml_content = """
url: "https://netbox.file.com"
token: "file-token"
timeout: 30
"""
        
        env_vars = {
            'NETBOX_URL': 'https://netbox.env.com',
            'NETBOX_TIMEOUT': '60'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                with patch.dict(os.environ, env_vars, clear=False):
                    config = ConfigurationManager.load_config(f.name)
                
                # Environment should override file
                assert config.url == "https://netbox.env.com"
                assert config.timeout == 60
                # File value should be used where no env override
                assert config.token == "file-token"
            finally:
                os.unlink(f.name)
    
    def test_convenience_load_config_function(self):
        """Test the convenience load_config function"""
        env_vars = {
            'NETBOX_URL': 'https://netbox.convenience.com',
            'NETBOX_TOKEN': 'convenience-token'
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()
        
        assert isinstance(config, NetBoxConfig)
        assert config.url == 'https://netbox.convenience.com'
        assert config.token == 'convenience-token'
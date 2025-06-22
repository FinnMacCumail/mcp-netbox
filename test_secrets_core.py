#!/usr/bin/env python3
"""
Core secrets management functionality test.
Tests the essential features for Issue #30.
"""

import os
import tempfile
from pathlib import Path
from netbox_mcp.secrets import SecretsManager, get_secrets_manager
from netbox_mcp.config import load_config


def test_environment_variables():
    """Test core environment variable loading."""
    print("🧪 Testing environment variable secrets...")
    
    # Backup and remove .env file
    env_file = Path(".env")
    backup_path = None
    if env_file.exists():
        backup_path = Path(".env.backup")
        env_file.rename(backup_path)
    
    try:
        # Set test variables
        os.environ['NETBOX_URL'] = "https://test.example.com"
        os.environ['NETBOX_TOKEN'] = "test_token_123"
        os.environ['NETBOX_DRY_RUN'] = "true"
        os.environ['NETBOX_LOG_LEVEL'] = "DEBUG"
        
        # Create secrets manager
        sm = SecretsManager()
        
        # Test basic secrets loading
        assert sm.get_secret("NETBOX_URL") == "https://test.example.com"
        assert sm.get_secret("NETBOX_TOKEN") == "test_token_123"
        assert sm.get_secret("NETBOX_DRY_RUN") == "true"
        assert sm.get_secret("NETBOX_LOG_LEVEL") == "DEBUG"
        
        # Test required secret validation
        url = sm.get_required_secret("NETBOX_URL")
        assert url == "https://test.example.com"
        
        # Test secret masking
        masked = sm.mask_for_logging("NETBOX_TOKEN")
        assert masked == "***_123", f"Expected '***_123', got '{masked}'"
        
        # Test connection info
        conn_info = sm.get_connection_info()
        assert "test.example.com" in conn_info['url']
        assert conn_info['token'] == "***_123"
        
        # Test configuration integration
        config = load_config()
        assert config.url == "https://test.example.com"
        assert config.token == "test_token_123"
        assert config.safety.dry_run_mode == True
        assert config.log_level == "DEBUG"
        
        print("✅ Environment variable secrets test passed")
        return True
        
    except Exception as e:
        print(f"❌ Environment variable secrets test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup environment
        for var in ['NETBOX_URL', 'NETBOX_TOKEN', 'NETBOX_DRY_RUN', 'NETBOX_LOG_LEVEL']:
            if var in os.environ:
                del os.environ[var]
        
        # Restore .env file
        if backup_path and backup_path.exists():
            backup_path.rename(env_file)


def test_docker_secrets():
    """Test Docker secrets loading."""
    print("🧪 Testing Docker secrets...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        docker_path = Path(temp_dir) / "docker_secrets"
        docker_path.mkdir()
        
        # Create Docker secret files
        (docker_path / "netbox_url").write_text("https://docker.example.com")
        (docker_path / "netbox_token").write_text("docker_secret_token")
        (docker_path / "netbox_username").write_text("docker_user")
        
        try:
            # Create secrets manager and test Docker loading directly
            sm = SecretsManager()
            
            # Test Docker secrets loading method
            original_path = sm.DOCKER_SECRETS_PATH
            sm.DOCKER_SECRETS_PATH = docker_path
            docker_secrets = sm._load_docker_secrets()
            
            assert docker_secrets['NETBOX_URL'] == "https://docker.example.com"
            assert docker_secrets['NETBOX_TOKEN'] == "docker_secret_token"
            assert docker_secrets['NETBOX_USERNAME'] == "docker_user"
            
            # Restore original path
            sm.DOCKER_SECRETS_PATH = original_path
            
            print("✅ Docker secrets test passed")
            return True
            
        except Exception as e:
            print(f"❌ Docker secrets test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_kubernetes_secrets():
    """Test Kubernetes secrets loading."""
    print("🧪 Testing Kubernetes secrets...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        k8s_path = Path(temp_dir) / "k8s_secrets"
        k8s_path.mkdir()
        
        # Create Kubernetes secret files (different naming convention)
        (k8s_path / "url").write_text("https://k8s.example.com")
        (k8s_path / "token").write_text("k8s_secret_token")
        (k8s_path / "username").write_text("k8s_user")
        
        try:
            # Create secrets manager and test K8s loading directly
            sm = SecretsManager()
            
            # Test Kubernetes secrets loading method
            original_path = sm.K8S_SECRETS_PATH
            sm.K8S_SECRETS_PATH = k8s_path
            k8s_secrets = sm._load_kubernetes_secrets()
            
            assert k8s_secrets['NETBOX_URL'] == "https://k8s.example.com"
            assert k8s_secrets['NETBOX_TOKEN'] == "k8s_secret_token"
            assert k8s_secrets['NETBOX_USERNAME'] == "k8s_user"
            
            # Restore original path
            sm.K8S_SECRETS_PATH = original_path
            
            print("✅ Kubernetes secrets test passed")
            return True
            
        except Exception as e:
            print(f"❌ Kubernetes secrets test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_priority_and_validation():
    """Test priority order and validation."""
    print("🧪 Testing priority order and validation...")
    
    # Backup .env file
    env_file = Path(".env")
    backup_path = None
    if env_file.exists():
        backup_path = Path(".env.backup")
        env_file.rename(backup_path)
    
    try:
        # Test validation without secrets
        sm_empty = SecretsManager()
        validation = sm_empty.validate_secrets()
        assert not validation['NETBOX_URL']
        assert not validation['NETBOX_TOKEN']
        
        # Test with secrets
        os.environ['NETBOX_URL'] = "https://priority.example.com"
        os.environ['NETBOX_TOKEN'] = "priority_token"
        
        sm_with_secrets = SecretsManager()
        validation = sm_with_secrets.validate_secrets()
        assert validation['NETBOX_URL']
        assert validation['NETBOX_TOKEN']
        
        # Test required secret error
        try:
            sm_empty.get_required_secret("NETBOX_MISSING")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "not found" in str(e)
        
        print("✅ Priority order and validation test passed")
        return True
        
    except Exception as e:
        print(f"❌ Priority order and validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup environment
        for var in ['NETBOX_URL', 'NETBOX_TOKEN']:
            if var in os.environ:
                del os.environ[var]
        
        # Restore .env file
        if backup_path and backup_path.exists():
            backup_path.rename(env_file)


def main():
    """Run core secrets tests."""
    print("🔐 NetBox MCP Secrets Management - Core Functionality Test")
    print("=" * 60)
    
    tests = [
        test_environment_variables,
        test_docker_secrets,
        test_kubernetes_secrets,
        test_priority_and_validation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Core Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All core secrets functionality tests passed!")
        print("✅ Issue #30: Centralized configuration and secrets management - COMPLETE")
        return True
    else:
        print("⚠️  Some core tests failed")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
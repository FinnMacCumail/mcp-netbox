#!/usr/bin/env python3
"""
Test suite for structured logging implementation.
Tests Issue #31: Implement structured logging (JSON).
"""

import json
import logging
import tempfile
import time
from pathlib import Path
from io import StringIO
from unittest.mock import patch

from netbox_mcp.logging_config import (
    configure_logging, get_logger, StructuredFormatter, 
    correlation_id, operation_timing, correlation_context
)
from netbox_mcp.config import load_config


def test_structured_formatter():
    """Test JSON structured log formatting."""
    print("🧪 Testing structured log formatter...")
    
    try:
        # Create formatter
        formatter = StructuredFormatter(service_name="test-service", service_version="1.0.0")
        
        # Create test log record
        logger = logging.getLogger("test.logger")
        record = logger.makeRecord(
            name="test.logger",
            level=logging.INFO,
            fn="test_file.py",
            lno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add custom fields
        record.custom_field = "custom_value"
        record.duration_ms = 123.456
        record.netbox_operation = "create"
        record.netbox_object_type = "device"
        record.http_method = "POST"
        record.http_path = "/api/dcim/devices/"
        
        # Format the record
        formatted = formatter.format(record)
        
        # Parse JSON
        log_data = json.loads(formatted)
        
        # Validate structure
        assert "timestamp" in log_data
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["service"]["name"] == "test-service"
        assert log_data["service"]["version"] == "1.0.0"
        assert log_data["source"]["file"] == "test_file.py"
        assert log_data["source"]["line"] == 42
        assert log_data["custom"]["custom_field"] == "custom_value"
        assert log_data["performance"]["duration_ms"] == 123.456
        assert log_data["netbox"]["operation"] == "create"
        assert log_data["netbox"]["object_type"] == "device"
        assert log_data["http"]["method"] == "POST"
        assert log_data["http"]["path"] == "/api/dcim/devices/"
        
        print("✅ Structured log formatter test passed")
        return True
        
    except Exception as e:
        print(f"❌ Structured log formatter test failed: {e}")
        return False


def test_correlation_id_context():
    """Test correlation ID context management."""
    print("🧪 Testing correlation ID context...")
    
    try:
        # Test initial state
        assert correlation_context.get_correlation_id() is None
        
        # Test context manager
        with correlation_id("test-123") as cid:
            assert cid == "test-123"
            assert correlation_context.get_correlation_id() == "test-123"
            
            # Test nested context
            with correlation_id("nested-456") as nested_cid:
                assert nested_cid == "nested-456"
                assert correlation_context.get_correlation_id() == "nested-456"
            
            # Should restore previous ID
            assert correlation_context.get_correlation_id() == "test-123"
        
        # Should clear after context
        assert correlation_context.get_correlation_id() is None
        
        print("✅ Correlation ID context test passed")
        return True
        
    except Exception as e:
        print(f"❌ Correlation ID context test failed: {e}")
        return False


def test_operation_timing():
    """Test operation timing context manager."""
    print("🧪 Testing operation timing...")
    
    try:
        # Capture log output
        log_output = StringIO()
        handler = logging.StreamHandler(log_output)
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        
        logger = logging.getLogger("test.timing")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Test successful operation
        with operation_timing(logger, "test_operation"):
            time.sleep(0.01)  # Small delay to ensure timing works
        
        # Get log output
        log_content = log_output.getvalue()
        log_data = json.loads(log_content.strip())
        
        # Validate timing was recorded
        assert "performance" in log_data
        assert "duration_ms" in log_data["performance"]
        assert log_data["performance"]["duration_ms"] > 0
        assert "test_operation completed" in log_data["message"]
        
        print("✅ Operation timing test passed")
        return True
        
    except Exception as e:
        print(f"❌ Operation timing test failed: {e}")
        return False


def test_netbox_operation_logger():
    """Test NetBox-specific operation logging."""
    print("🧪 Testing NetBox operation logger...")
    
    try:
        # Capture log output
        log_output = StringIO()
        handler = logging.StreamHandler(log_output)
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        
        logger = get_logger("test.netbox")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Test NetBox operation logging
        start_time = time.time()
        logger.netbox_write(
            "Created device successfully",
            operation="create",
            object_type="device",
            object_id=123,
            dry_run=False,
            start_time=start_time
        )
        
        # Get log output
        log_content = log_output.getvalue()
        log_data = json.loads(log_content.strip())
        
        # Validate NetBox context
        assert "netbox" in log_data
        assert log_data["netbox"]["operation"] == "create"
        assert log_data["netbox"]["object_type"] == "device"
        assert log_data["netbox"]["object_id"] == 123
        assert log_data["netbox"]["dry_run"] == False
        assert "performance" in log_data
        assert log_data["performance"]["duration_ms"] > 0
        
        print("✅ NetBox operation logger test passed")
        return True
        
    except Exception as e:
        print(f"❌ NetBox operation logger test failed: {e}")
        return False


def test_secrets_masking():
    """Test automatic secrets masking in logs."""
    print("🧪 Testing secrets masking...")
    
    try:
        # Create formatter
        formatter = StructuredFormatter()
        
        # Create log record with secrets
        logger = logging.getLogger("test.secrets")
        record = logger.makeRecord(
            name="test.secrets",
            level=logging.INFO,
            fn="test.py",
            lno=1,
            msg="Processing authentication",
            args=(),
            exc_info=None
        )
        
        # Add fields that look like secrets
        record.api_token = "secret_token_12345"
        record.password = "super_secret_password"
        record.auth_header = "Bearer abc123def456"
        record.normal_field = "not_a_secret"
        
        # Format the record
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        # Validate secrets are masked
        assert log_data["custom"]["api_token"] == "***2345"
        assert log_data["custom"]["password"] == "***word"
        assert log_data["custom"]["auth_header"] == "***f456"
        assert log_data["custom"]["normal_field"] == "not_a_secret"
        
        print("✅ Secrets masking test passed")
        return True
        
    except Exception as e:
        print(f"❌ Secrets masking test failed: {e}")
        return False


def test_configuration_integration():
    """Test integration with configuration system."""
    print("🧪 Testing configuration integration...")
    
    # Backup .env file
    env_file = Path(".env")
    backup_path = None
    if env_file.exists():
        backup_path = Path(".env.backup")
        env_file.rename(backup_path)
    
    try:
        import os
        
        # Set logging configuration via environment
        os.environ['NETBOX_URL'] = "https://test.example.com"
        os.environ['NETBOX_TOKEN'] = "test_token"
        os.environ['NETBOX_LOG_LEVEL'] = "DEBUG"
        os.environ['NETBOX_LOG_FORMAT'] = "json"
        os.environ['NETBOX_LOG_SERVICE_NAME'] = "test-mcp"
        os.environ['NETBOX_LOG_ENABLE_PERFORMANCE'] = "true"
        
        # Load configuration
        config = load_config()
        
        # Validate logging configuration
        assert config.logging.level == "DEBUG"
        assert config.logging.format == "json"
        assert config.logging.service_name == "test-mcp"
        assert config.logging.enable_performance_logging == True
        
        print("✅ Configuration integration test passed")
        return True
        
    except Exception as e:
        print(f"❌ Configuration integration test failed: {e}")
        return False
        
    finally:
        # Cleanup environment
        env_vars = ['NETBOX_URL', 'NETBOX_TOKEN', 'NETBOX_LOG_LEVEL', 
                   'NETBOX_LOG_FORMAT', 'NETBOX_LOG_SERVICE_NAME', 
                   'NETBOX_LOG_ENABLE_PERFORMANCE']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
        
        # Restore .env file
        if backup_path and backup_path.exists():
            backup_path.rename(env_file)


def test_full_logging_pipeline():
    """Test complete logging pipeline with file output."""
    print("🧪 Testing full logging pipeline...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # Configure structured logging
            configure_logging(
                log_level="INFO",
                log_format="json",
                log_file=str(log_file),
                service_name="test-pipeline",
                service_version="1.0.0"
            )
            
            # Get logger and log some events
            logger = get_logger("test.pipeline")
            
            with correlation_id("pipeline-test"):
                logger.info("Starting test pipeline")
                
                with operation_timing(logger, "test_operation"):
                    logger.netbox_read("Reading devices", "/api/dcim/devices/")
                    time.sleep(0.001)  # Small delay
                
                logger.netbox_write(
                    "Created test device",
                    operation="create",
                    object_type="device",
                    object_id=456,
                    dry_run=True
                )
                
                logger.info("Test pipeline completed")
            
            # Verify log file was created and contains structured logs
            assert log_file.exists()
            
            with open(log_file, 'r') as f:
                log_lines = f.readlines()
            
            assert len(log_lines) >= 4  # At least 4 log entries
            
            # Validate each line is valid JSON with expected structure
            for line in log_lines:
                log_data = json.loads(line.strip())
                assert "timestamp" in log_data
                assert "level" in log_data
                assert "service" in log_data
                assert log_data["service"]["name"] == "test-pipeline"
                assert "correlation_id" in log_data
                assert log_data["correlation_id"] == "pipeline-test"
            
            print("✅ Full logging pipeline test passed")
            return True
            
    except Exception as e:
        print(f"❌ Full logging pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_tests():
    """Run all structured logging tests."""
    tests = [
        test_structured_formatter,
        test_correlation_id_context,
        test_operation_timing,
        test_netbox_operation_logger,
        test_secrets_masking,
        test_configuration_integration,
        test_full_logging_pipeline
    ]
    
    passed = 0
    failed = 0
    
    print("📝 NetBox MCP Structured Logging Tests")
    print("=" * 50)
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All structured logging tests passed!")
        print("✅ Issue #31: Implement structured logging (JSON) - COMPLETE")
        return True
    else:
        print("⚠️  Some tests failed - please review the implementation")
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
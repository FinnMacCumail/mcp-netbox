#!/usr/bin/env python3
"""
Integration Test Runner for Week 9-12 Real NetBox Integration
Real NetBox Integration & Advanced Conversation Management

This script provides an easy way to run comprehensive integration tests
for the real NetBox MCP integration with various configuration options.
"""

import asyncio
import sys
import os
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class IntegrationTestRunner:
    """Test runner for NetBox MCP integration tests"""
    
    def __init__(self):
        self.project_root = project_root
        self.test_dir = self.project_root / "tests" / "integration"
        
    def check_dependencies(self) -> bool:
        """Check if all dependencies are available"""
        try:
            import pytest
            import redis
            import asyncio_throttle
            return True
        except ImportError as e:
            print(f"❌ Missing dependency: {e}")
            print("Install dependencies with: pip install -e .")
            return False
    
    def check_redis(self) -> bool:
        """Check if Redis is available"""
        try:
            import redis
            client = redis.Redis(host='localhost', port=6379, db=0)
            client.ping()
            return True
        except Exception:
            return False
    
    def run_basic_validation(self) -> bool:
        """Run basic validation of components"""
        print("🔍 Running basic component validation...")
        
        try:
            # Test tool registry
            from netbox_mcp.orchestration.tool_registry import ReadOnlyToolRegistry
            registry = ReadOnlyToolRegistry()
            tool_count = len(registry._tool_registry)
            print(f"✅ Tool Registry: {tool_count} tools registered")
            
            # Test performance monitor
            from netbox_mcp.orchestration.performance_monitor import PerformanceMonitor
            monitor = PerformanceMonitor()
            print("✅ Performance Monitor: initialized")
            
            # Test entity tracker
            from netbox_mcp.orchestration.entity_tracker import EntityTracker, EntityType
            tracker = EntityTracker("test_session")
            entity_id = tracker.track_entity(EntityType.DEVICE, "test-device")
            print("✅ Entity Tracker: working")
            
            # Test real API handler
            from netbox_mcp.orchestration.real_api_handler import RealAPIHandler
            handler = RealAPIHandler()
            print("✅ Real API Handler: initialized")
            
            # Test cache (if Redis available)
            if self.check_redis():
                from netbox_mcp.orchestration.cache import OrchestrationCache
                cache = OrchestrationCache()
                print("✅ Cache: Redis available")
            else:
                print("⚠️ Cache: Redis not available (cache tests will be skipped)")
            
            return True
            
        except Exception as e:
            print(f"❌ Component validation failed: {e}")
            return False
    
    def run_pytest(self, args: List[str]) -> int:
        """Run pytest with specified arguments"""
        cmd = ["python", "-m", "pytest"] + args
        print(f"🚀 Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, cwd=self.project_root)
        return result.returncode
    
    def run_quick_tests(self) -> int:
        """Run quick integration tests (no slow tests)"""
        print("⚡ Running quick integration tests...")
        
        args = [
            str(self.test_dir),
            "-v",
            "-m", "not slow",
            "--tb=short",
            "-x"  # Stop on first failure
        ]
        
        return self.run_pytest(args)
    
    def run_full_tests(self) -> int:
        """Run full integration test suite"""
        print("🔄 Running full integration test suite...")
        
        args = [
            str(self.test_dir),
            "-v",
            "--tb=long",
            "--capture=no"
        ]
        
        return self.run_pytest(args)
    
    def run_performance_tests(self) -> int:
        """Run performance-focused tests"""
        print("⚡ Running performance tests...")
        
        args = [
            str(self.test_dir),
            "-v", 
            "-m", "performance",
            "--tb=short"
        ]
        
        return self.run_pytest(args)
    
    def run_cache_tests(self) -> int:
        """Run cache-specific tests"""
        if not self.check_redis():
            print("❌ Redis is required for cache tests")
            return 1
        
        print("💾 Running cache integration tests...")
        
        args = [
            str(self.test_dir),
            "-v",
            "-m", "redis_required",
            "--tb=short"
        ]
        
        return self.run_pytest(args)
    
    def run_specific_test(self, test_path: str) -> int:
        """Run a specific test file or test method"""
        print(f"🎯 Running specific test: {test_path}")
        
        args = [
            test_path,
            "-v",
            "--tb=long"
        ]
        
        return self.run_pytest(args)
    
    def generate_coverage_report(self) -> int:
        """Generate test coverage report"""
        print("📊 Generating coverage report...")
        
        args = [
            str(self.test_dir),
            "--cov=netbox_mcp.orchestration",
            "--cov-report=html",
            "--cov-report=term-missing",
            "-v"
        ]
        
        return self.run_pytest(args)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Integration Test Runner for NetBox MCP Week 9-12"
    )
    
    parser.add_argument(
        "command",
        choices=[
            "validate", "quick", "full", "performance", 
            "cache", "coverage", "specific"
        ],
        help="Test command to run"
    )
    
    parser.add_argument(
        "--test-path",
        help="Specific test path for 'specific' command"
    )
    
    parser.add_argument(
        "--no-deps-check",
        action="store_true",
        help="Skip dependency checking"
    )
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner()
    
    # Check dependencies unless skipped
    if not args.no_deps_check:
        if not runner.check_dependencies():
            return 1
    
    # Run the specified command
    if args.command == "validate":
        if runner.run_basic_validation():
            print("✅ All components validated successfully!")
            return 0
        else:
            return 1
            
    elif args.command == "quick":
        return runner.run_quick_tests()
        
    elif args.command == "full":
        return runner.run_full_tests()
        
    elif args.command == "performance":
        return runner.run_performance_tests()
        
    elif args.command == "cache":
        return runner.run_cache_tests()
        
    elif args.command == "coverage":
        return runner.generate_coverage_report()
        
    elif args.command == "specific":
        if not args.test_path:
            print("❌ --test-path is required for 'specific' command")
            return 1
        return runner.run_specific_test(args.test_path)
    
    else:
        print(f"❌ Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
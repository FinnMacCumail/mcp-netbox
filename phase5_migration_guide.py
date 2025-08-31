#!/usr/bin/env python3
"""
Phase 5 Migration Guide - NetBox MCP CLI Integration

This script provides a complete migration path from the original NetBox MCP CLI 
to the new intelligent system with backward compatibility and validation.

Features:
1. CLI entry point updates
2. Backward compatibility integration
3. Migration validation
4. Performance monitoring
5. Rollback procedures

Usage:
    python phase5_migration_guide.py --mode [validate|migrate|rollback|monitor]
"""

import asyncio
import sys
import os
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from netbox_mcp.orchestration.backward_compatibility import (
    BackwardCompatibilityManager, CompatibilityConfig, MigrationPhase, 
    FeatureFlag, create_backward_compatibility_manager, CompatibleCLIProcessor
)
from phase5_comprehensive_validation import Phase5ComprehensiveValidator


class Phase5MigrationManager:
    """
    Manages the complete migration process for Phase 5
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.compatibility_manager: Optional[BackwardCompatibilityManager] = None
        self.validator: Optional[Phase5ComprehensiveValidator] = None
    
    async def validate_migration(self) -> Dict[str, Any]:
        """
        Validate that the migration is ready and successful
        """
        self.logger.info("🔍 Validating Phase 5 Migration Readiness")
        self.logger.info("=" * 50)
        
        try:
            # Run comprehensive validation
            validator = Phase5ComprehensiveValidator()
            validation_report = await validator.run_comprehensive_validation()
            
            # Check if migration is ready
            migration_ready = self._assess_migration_readiness(validation_report)
            
            # Save validation report
            report_file = f"migration_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(validation_report, f, indent=2, default=str)
            
            self.logger.info(f"Validation report saved: {report_file}")
            
            return {
                "validation_successful": migration_ready,
                "report_file": report_file,
                "validation_report": validation_report,
                "recommendations": self._generate_migration_recommendations(validation_report)
            }
            
        except Exception as e:
            self.logger.error(f"Migration validation failed: {e}")
            return {
                "validation_successful": False,
                "error": str(e)
            }
    
    async def execute_migration(self, phase: MigrationPhase = MigrationPhase.MIXED_MODE) -> Dict[str, Any]:
        """
        Execute the migration to the specified phase
        """
        self.logger.info(f"🚀 Executing Migration to Phase: {phase.value}")
        self.logger.info("=" * 50)
        
        try:
            # Create compatibility manager for the specified phase
            self.compatibility_manager = await create_backward_compatibility_manager(
                migration_phase=phase,
                a_b_testing_percentage=50.0 if phase == MigrationPhase.MIXED_MODE else 100.0
            )
            
            # Test the migration with sample queries
            test_results = await self._test_migration_with_samples()
            
            # Update CLI integration
            cli_integration_results = await self._update_cli_integration()
            
            # Generate migration success report
            migration_report = {
                "migration_phase": phase.value,
                "migration_timestamp": datetime.now().isoformat(),
                "compatibility_manager_initialized": self.compatibility_manager is not None,
                "test_results": test_results,
                "cli_integration": cli_integration_results,
                "success": test_results.get("all_tests_passed", False)
            }
            
            # Save migration report
            report_file = f"migration_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(migration_report, f, indent=2, default=str)
            
            self.logger.info(f"Migration execution report saved: {report_file}")
            
            return migration_report
            
        except Exception as e:
            self.logger.error(f"Migration execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "migration_phase": phase.value
            }
    
    async def monitor_migration(self, duration_minutes: int = 10) -> Dict[str, Any]:
        """
        Monitor the migration for the specified duration
        """
        self.logger.info(f"📊 Monitoring Migration for {duration_minutes} minutes")
        self.logger.info("=" * 50)
        
        if not self.compatibility_manager:
            self.compatibility_manager = await create_backward_compatibility_manager()
        
        # Run monitoring queries periodically
        monitoring_queries = [
            "device type information for Cisco C9200-48P",
            "device info for dc1-sw01",
            "rack elevation for R01-A15",
            "show interfaces for device dc1-sw01",
            "list all sites",
            "show all devices"
        ]
        
        results = []
        end_time = datetime.now().timestamp() + (duration_minutes * 60)
        
        while datetime.now().timestamp() < end_time:
            for query in monitoring_queries:
                try:
                    result = await self.compatibility_manager.process_query(
                        query=query,
                        session_id=f"monitor_session_{datetime.now().strftime('%H%M%S')}"
                    )
                    
                    results.append({
                        "timestamp": datetime.now().isoformat(),
                        "query": query,
                        "success": result.get("success", False),
                        "system_used": result.get("compatibility_metadata", {}).get("system_used"),
                        "response_time": result.get("execution_metrics", {}).get("total_workflow_time", 0)
                    })
                    
                except Exception as e:
                    results.append({
                        "timestamp": datetime.now().isoformat(),
                        "query": query,
                        "success": False,
                        "error": str(e)
                    })
            
            # Wait 30 seconds before next round
            await asyncio.sleep(30)
        
        # Generate monitoring report
        monitoring_report = self._analyze_monitoring_results(results)
        
        # Save monitoring report
        report_file = f"migration_monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(monitoring_report, f, indent=2, default=str)
        
        self.logger.info(f"Monitoring report saved: {report_file}")
        
        return monitoring_report
    
    async def rollback_migration(self) -> Dict[str, Any]:
        """
        Rollback to legacy system in case of issues
        """
        self.logger.info("⚠️ Executing Migration Rollback")
        self.logger.info("=" * 50)
        
        try:
            # Create compatibility manager in legacy-only mode
            self.compatibility_manager = await create_backward_compatibility_manager(
                migration_phase=MigrationPhase.LEGACY_ONLY
            )
            
            # Test rollback with sample queries
            rollback_test_results = await self._test_migration_with_samples()
            
            rollback_report = {
                "rollback_timestamp": datetime.now().isoformat(),
                "rollback_successful": rollback_test_results.get("all_tests_passed", False),
                "system_mode": "legacy_only",
                "test_results": rollback_test_results
            }
            
            # Save rollback report
            report_file = f"migration_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(rollback_report, f, indent=2, default=str)
            
            self.logger.info(f"Rollback report saved: {report_file}")
            
            return rollback_report
            
        except Exception as e:
            self.logger.error(f"Migration rollback failed: {e}")
            return {
                "rollback_successful": False,
                "error": str(e)
            }
    
    async def _test_migration_with_samples(self) -> Dict[str, Any]:
        """Test migration with sample queries"""
        
        test_queries = [
            "device type information for Cisco C9200-48P",
            "device info for dc1-sw01", 
            "rack elevation for R01-A15",
            "show interfaces for device dc1-sw01"
        ]
        
        results = []
        
        for query in test_queries:
            try:
                start_time = datetime.now()
                result = await self.compatibility_manager.process_query(
                    query=query,
                    session_id=f"test_session_{hash(query)}"
                )
                test_time = (datetime.now() - start_time).total_seconds()
                
                results.append({
                    "query": query,
                    "success": result.get("success", False),
                    "response_time": test_time,
                    "system_used": result.get("compatibility_metadata", {}).get("system_used"),
                    "error": result.get("error") if not result.get("success") else None
                })
                
            except Exception as e:
                results.append({
                    "query": query,
                    "success": False,
                    "error": str(e)
                })
        
        passed_tests = sum(1 for r in results if r["success"])
        total_tests = len(results)
        
        return {
            "test_results": results,
            "tests_passed": passed_tests,
            "total_tests": total_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests else 0,
            "all_tests_passed": passed_tests == total_tests
        }
    
    async def _update_cli_integration(self) -> Dict[str, Any]:
        """Update CLI integration points"""
        
        try:
            # Create compatible CLI processor
            cli_processor = CompatibleCLIProcessor(self.compatibility_manager)
            
            # Test CLI interface compatibility
            test_request = {
                "query": "device type information for Cisco C9200-48P",
                "session_id": "cli_integration_test"
            }
            
            cli_result = await cli_processor.process_cli_request(test_request)
            
            return {
                "cli_processor_created": True,
                "cli_interface_compatible": cli_result.get("success", False),
                "test_result": cli_result
            }
            
        except Exception as e:
            self.logger.error(f"CLI integration update failed: {e}")
            return {
                "cli_processor_created": False,
                "error": str(e)
            }
    
    def _assess_migration_readiness(self, validation_report: Dict[str, Any]) -> bool:
        """Assess if migration is ready based on validation results"""
        
        summary = validation_report.get("validation_summary", {})
        conclusions = validation_report.get("conclusions", {})
        
        # Check critical criteria
        parity_achieved = summary.get("claude_code_cli_parity_achieved", False)
        success_rate = summary.get("overall_success_rate", 0)
        ready_for_production = conclusions.get("ready_for_production", False)
        
        # Migration is ready if:
        # 1. Claude Code CLI parity achieved
        # 2. Overall success rate >= 85%
        # 3. System is ready for production
        
        return parity_achieved and success_rate >= 85.0 and ready_for_production
    
    def _generate_migration_recommendations(self, validation_report: Dict[str, Any]) -> List[str]:
        """Generate migration recommendations based on validation"""
        
        recommendations = []
        
        summary = validation_report.get("validation_summary", {})
        conclusions = validation_report.get("conclusions", {})
        
        if summary.get("claude_code_cli_parity_achieved"):
            recommendations.append("✅ Claude Code CLI parity achieved - Ready for migration")
        else:
            recommendations.append("❌ Claude Code CLI parity NOT achieved - Fix critical queries first")
        
        if conclusions.get("performance_targets_met"):
            recommendations.append("✅ Performance targets met")
        else:
            recommendations.append("⚡ Performance optimization needed before migration")
        
        if conclusions.get("ready_for_production"):
            recommendations.append("🚀 Recommended migration phase: MIXED_MODE with 25% intelligent traffic")
        else:
            recommendations.append("🔧 System needs fixes before production migration")
        
        recommendations.extend(conclusions.get("next_steps", []))
        
        return recommendations
    
    def _analyze_monitoring_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze monitoring results"""
        
        if not results:
            return {"error": "No monitoring results available"}
        
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r.get("success"))
        
        # Group by system used
        intelligent_requests = [r for r in results if r.get("system_used") == "intelligent"]
        legacy_requests = [r for r in results if r.get("system_used") == "legacy"]
        
        # Calculate averages
        avg_response_time = (
            sum(r.get("response_time", 0) for r in results if r.get("response_time")) /
            len([r for r in results if r.get("response_time")]) if results else 0
        )
        
        return {
            "monitoring_summary": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate": (successful_requests / total_requests) * 100 if total_requests else 0,
                "avg_response_time": avg_response_time,
                "intelligent_system_usage": len(intelligent_requests),
                "legacy_system_usage": len(legacy_requests)
            },
            "detailed_results": results,
            "system_performance": {
                "intelligent_system": self._analyze_system_performance(intelligent_requests),
                "legacy_system": self._analyze_system_performance(legacy_requests)
            },
            "monitoring_period": {
                "start_time": results[0]["timestamp"] if results else None,
                "end_time": results[-1]["timestamp"] if results else None,
                "duration_minutes": len(results) * 0.5 if results else 0  # Approximate
            }
        }
    
    def _analyze_system_performance(self, system_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance for a specific system"""
        
        if not system_results:
            return {"requests": 0, "performance": "No data"}
        
        successful = sum(1 for r in system_results if r.get("success"))
        avg_time = (
            sum(r.get("response_time", 0) for r in system_results if r.get("response_time")) /
            len([r for r in system_results if r.get("response_time")]) if system_results else 0
        )
        
        return {
            "requests": len(system_results),
            "success_rate": (successful / len(system_results)) * 100,
            "avg_response_time": avg_time,
            "performance_rating": "Good" if avg_time < 3.0 and (successful / len(system_results)) > 0.9 else "Needs attention"
        }


async def main():
    """Main entry point for Phase 5 migration"""
    
    parser = argparse.ArgumentParser(
        description="Phase 5 Migration Guide - NetBox MCP CLI Integration"
    )
    
    parser.add_argument(
        "mode",
        choices=["validate", "migrate", "monitor", "rollback"],
        help="Migration operation to perform"
    )
    
    parser.add_argument(
        "--phase",
        choices=["legacy_only", "mixed_mode", "intelligent_preferred", "intelligent_only"],
        default="mixed_mode",
        help="Migration phase for migrate command"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Duration in minutes for monitor command"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 NetBox MCP Phase 5 Migration Guide")
    print("=" * 50)
    print(f"Mode: {args.mode}")
    print("=" * 50)
    
    try:
        manager = Phase5MigrationManager()
        
        if args.mode == "validate":
            result = await manager.validate_migration()
            
            if result["validation_successful"]:
                print("\n✅ Migration validation SUCCESSFUL")
                print("🎉 Claude Code CLI parity achieved!")
                print("🚀 Ready for migration")
            else:
                print("\n❌ Migration validation FAILED")
                print("🔧 Fixes needed before migration")
            
            print(f"\nRecommendations:")
            for rec in result.get("recommendations", []):
                print(f"  {rec}")
        
        elif args.mode == "migrate":
            phase_map = {
                "legacy_only": MigrationPhase.LEGACY_ONLY,
                "mixed_mode": MigrationPhase.MIXED_MODE,
                "intelligent_preferred": MigrationPhase.INTELLIGENT_PREFERRED,
                "intelligent_only": MigrationPhase.INTELLIGENT_ONLY
            }
            
            phase = phase_map[args.phase]
            result = await manager.execute_migration(phase)
            
            if result["success"]:
                print(f"\n✅ Migration to {args.phase} SUCCESSFUL")
                print("🎉 System ready for use")
            else:
                print(f"\n❌ Migration to {args.phase} FAILED")
                print("🔧 Check logs for details")
        
        elif args.mode == "monitor":
            result = await manager.monitor_migration(args.duration)
            
            summary = result["monitoring_summary"]
            print(f"\n📊 Monitoring Results ({args.duration} minutes):")
            print(f"  Total requests: {summary['total_requests']}")
            print(f"  Success rate: {summary['success_rate']:.1f}%")
            print(f"  Avg response time: {summary['avg_response_time']:.2f}s")
            print(f"  Intelligent system usage: {summary['intelligent_system_usage']}")
            print(f"  Legacy system usage: {summary['legacy_system_usage']}")
        
        elif args.mode == "rollback":
            result = await manager.rollback_migration()
            
            if result["rollback_successful"]:
                print("\n✅ Migration rollback SUCCESSFUL")
                print("🔄 System restored to legacy mode")
            else:
                print("\n❌ Migration rollback FAILED")
                print("🚨 Manual intervention may be required")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Migration operation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Migration operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
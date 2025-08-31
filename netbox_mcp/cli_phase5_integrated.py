#!/usr/bin/env python3
"""
Phase 5 Integrated CLI - NetBox MCP with Backward Compatibility

This CLI provides seamless integration between the legacy NetBox MCP system
and the new intelligent Phase 1-4 system with backward compatibility,
feature flags, and migration support.

Features:
1. Seamless backward compatibility 
2. A/B testing capability
3. Performance monitoring
4. Migration tracking
5. Claude Code CLI parity validation

Usage:
    python -m netbox_mcp.cli_phase5_integrated [options]
"""

import asyncio
import sys
import os
import logging
import argparse
from datetime import datetime
from typing import Optional, Dict, Any
import json
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from netbox_mcp.orchestration.backward_compatibility import (
    BackwardCompatibilityManager, CompatibilityConfig, MigrationPhase,
    FeatureFlag, create_backward_compatibility_manager, CompatibleCLIProcessor
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class Phase5IntegratedCLI:
    """
    Phase 5 CLI with backward compatibility and migration support
    """
    
    def __init__(self, migration_phase: MigrationPhase = MigrationPhase.MIXED_MODE):
        self.compatibility_manager: Optional[BackwardCompatibilityManager] = None
        self.cli_processor: Optional[CompatibleCLIProcessor] = None
        self.session_id = f"phase5_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.migration_phase = migration_phase
        self.running = False
        self.query_count = 0
        self.system_stats = {
            "intelligent_queries": 0,
            "legacy_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_response_time": 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize the integrated CLI with backward compatibility"""
        try:
            print(f"🚀 Initializing Phase 5 Integrated NetBox MCP CLI")
            print(f"📊 Migration Phase: {self.migration_phase.value}")
            print("=" * 60)
            
            # Create backward compatibility manager
            self.compatibility_manager = await create_backward_compatibility_manager(
                migration_phase=self.migration_phase,
                a_b_testing_percentage=50.0  # 50% A/B split for mixed mode
            )
            
            print("✅ Backward compatibility system initialized")
            
            # Create compatible CLI processor
            self.cli_processor = CompatibleCLIProcessor(self.compatibility_manager)
            print("✅ CLI processor with compatibility layer ready")
            
            print(f"📱 Session ID: {self.session_id}")
            
            # Display system capabilities based on migration phase
            await self._display_system_capabilities()
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            logger.exception("Full error details:")
            return False
    
    async def _display_system_capabilities(self):
        """Display current system capabilities"""
        print(f"\n🧠 System Capabilities:")
        
        if self.migration_phase == MigrationPhase.INTELLIGENT_ONLY:
            print("  • Phase 1: IntelligentToolSelector - LLM-powered tool selection")
            print("  • Phase 2: ToolAwareParameterExtractor - Context-preserving parameters")
            print("  • Phase 3: LangGraph 3-Node Workflow - Intelligent orchestration") 
            print("  • Phase 4: Intelligent Fallback System - Error recovery")
            print("  • ✅ Claude Code CLI Parity Achieved")
            
        elif self.migration_phase == MigrationPhase.MIXED_MODE:
            print("  • 🔄 Hybrid System: Intelligent + Legacy with A/B testing")
            print("  • 📊 50% traffic using intelligent system")
            print("  • 📊 50% traffic using legacy system")
            print("  • 🛡️ Automatic fallback on failures")
            print("  • 📈 Performance monitoring and comparison")
            
        elif self.migration_phase == MigrationPhase.LEGACY_ONLY:
            print("  • 🔙 Legacy System Only - Original NetBox MCP behavior")
            print("  • ⚠️ Known limitations present")
            
        print(f"\n🛠️ NetBox Tools: 142+ MCP tools available")
        print(f"🔧 Feature Flags: Active for {self.migration_phase.value} mode")
    
    async def process_query(self, query: str, force_system: Optional[str] = None) -> bool:
        """Process a user query with compatibility support"""
        if not self.cli_processor:
            print("❌ CLI processor not initialized")
            return False
        
        print(f"\n🔍 Processing: '{query}'")
        if force_system:
            print(f"🎯 Forced system: {force_system}")
        
        start_time = datetime.now()
        self.query_count += 1
        
        try:
            # Create request for CLI processor
            request = {
                "query": query,
                "session_id": self.session_id,
                "correlation_id": f"{self.session_id}_{self.query_count}",
                "force_system": force_system
            }
            
            # Process with compatibility layer
            result = await self.cli_processor.process_cli_request(request)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            success = result.get("success", False)
            
            # Update stats
            self._update_stats(result, processing_time, success)
            
            if success:
                print(f"✅ Query completed successfully ({processing_time:.2f}s)")
                
                # Display system used
                metadata = result.get("compatibility_metadata", {})
                system_used = metadata.get("system_used", "unknown")
                print(f"🤖 System used: {system_used}")
                
                if metadata.get("fallback_used"):
                    print(f"🔄 Fallback used: {metadata.get('original_system_failed')} → {metadata.get('fallback_system')}")
                
                # Display response
                response = result.get("response", "No response generated")
                print(f"\n💬 Response:")
                print("-" * 60)
                print(response)
                print("-" * 60)
                
                # Display user options if available
                user_options = result.get("user_options", [])
                if user_options:
                    print(f"\n🎛️ Available Options:")
                    for i, option in enumerate(user_options, 1):
                        print(f"   {i}. {option}")
                
                # Show performance metrics if available
                metrics = result.get("execution_metrics", {})
                if metrics:
                    workflow_time = metrics.get("total_workflow_time")
                    if workflow_time:
                        print(f"\n⚡ Performance: {workflow_time:.2f}s workflow time")
                
                return True
            else:
                error = result.get("error", "Unknown error")
                print(f"❌ Query failed: {error}")
                
                # Show fallback information if available
                metadata = result.get("compatibility_metadata", {})
                if metadata.get("all_systems_failed"):
                    print("🚨 Both intelligent and legacy systems failed")
                
                return False
                
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats({}, processing_time, False)
            
            print(f"❌ Error processing query: {e}")
            logger.exception("Full error details:")
            return False
    
    def _update_stats(self, result: Dict[str, Any], processing_time: float, success: bool):
        """Update system statistics"""
        metadata = result.get("compatibility_metadata", {})
        system_used = metadata.get("system_used", "unknown")
        
        if system_used == "intelligent":
            self.system_stats["intelligent_queries"] += 1
        elif system_used == "legacy":
            self.system_stats["legacy_queries"] += 1
        
        if success:
            self.system_stats["successful_queries"] += 1
        else:
            self.system_stats["failed_queries"] += 1
        
        # Update average response time
        total_queries = self.system_stats["successful_queries"] + self.system_stats["failed_queries"]
        if total_queries > 1:
            self.system_stats["avg_response_time"] = (
                (self.system_stats["avg_response_time"] * (total_queries - 1) + processing_time) / 
                total_queries
            )
        else:
            self.system_stats["avg_response_time"] = processing_time
    
    async def run_interactive(self):
        """Run interactive CLI mode"""
        print("\n" + "=" * 80)
        print("🚀 NetBox MCP Phase 5 Integrated CLI - Interactive Mode")
        print("=" * 80)
        print("\nWelcome to the integrated NetBox MCP CLI with backward compatibility!")
        print(f"Current mode: {self.migration_phase.value}")
        print("\n🎯 Features:")
        print("  • Seamless backward compatibility between systems")
        print("  • A/B testing for performance comparison")
        print("  • Intelligent fallback on failures")
        print("  • Migration tracking and analysis")
        print("  • Claude Code CLI parity validation")
        
        print("\n📖 Example queries to try:")
        print("  • 'device type information for Cisco C9200-48P' (originally failing)")
        print("  • 'device info for dc1-sw01' (originally failing)")
        print("  • 'rack elevation for R01-A15' (originally failing)")
        print("  • 'show interfaces for device dc1-sw01' (originally failing)")
        print("  • 'list all sites in NetBox'")
        print("  • 'show all devices'")
        
        print("\n💡 Commands:")
        print("  • 'quit' or 'exit' - Exit the CLI")
        print("  • 'stats' - Show system statistics")
        print("  • 'migration-report' - Generate migration analysis")
        print("  • 'switch-to intelligent' - Force intelligent system")
        print("  • 'switch-to legacy' - Force legacy system")
        print("  • 'switch-to mixed' - Return to A/B testing")
        print("  • 'validate-parity' - Run Claude Code CLI parity validation")
        print("  • 'clear' - Clear screen")
        print("-" * 80)
        
        self.running = True
        force_system = None
        
        while self.running:
            try:
                # Get user input
                system_indicator = ""
                if force_system:
                    system_indicator = f" [{force_system}]"
                
                user_input = input(f"\n🤖 NetBox{system_indicator}> ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye! Shutting down integrated CLI...")
                    break
                    
                elif user_input.lower() == 'stats':
                    await self.show_system_stats()
                    continue
                    
                elif user_input.lower() == 'migration-report':
                    await self.generate_migration_report()
                    continue
                    
                elif user_input.lower().startswith('switch-to '):
                    system = user_input.lower().replace('switch-to ', '').strip()
                    if system in ['intelligent', 'legacy']:
                        force_system = system
                        print(f"🔄 Switched to {system} system (forced)")
                    elif system == 'mixed':
                        force_system = None
                        print("🔄 Returned to A/B testing mode")
                    else:
                        print("❌ Invalid system. Use: intelligent, legacy, or mixed")
                    continue
                    
                elif user_input.lower() == 'validate-parity':
                    await self.run_parity_validation()
                    continue
                    
                elif user_input.lower() == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    continue
                    
                elif user_input.lower() in ['help', '?']:
                    self.show_help()
                    continue
                
                # Process the query
                await self.process_query(user_input, force_system)
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Interrupted by user. Shutting down...")
                break
            except EOFError:
                print("\n\n👋 Session ended. Shutting down...")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                logger.exception("Full error details:")
    
    async def show_system_stats(self):
        """Show system statistics"""
        print(f"\n📊 System Statistics (Session: {self.session_id})")
        print("-" * 50)
        print(f"  📈 Total queries: {self.query_count}")
        print(f"  🤖 Intelligent system: {self.system_stats['intelligent_queries']}")
        print(f"  🔙 Legacy system: {self.system_stats['legacy_queries']}")
        print(f"  ✅ Successful: {self.system_stats['successful_queries']}")
        print(f"  ❌ Failed: {self.system_stats['failed_queries']}")
        
        if self.query_count > 0:
            success_rate = (self.system_stats['successful_queries'] / self.query_count) * 100
            print(f"  📊 Success rate: {success_rate:.1f}%")
            print(f"  ⚡ Avg response time: {self.system_stats['avg_response_time']:.2f}s")
        
        print(f"  🔧 Migration phase: {self.migration_phase.value}")
    
    async def generate_migration_report(self):
        """Generate and display migration analysis report"""
        if not self.compatibility_manager:
            print("❌ Compatibility manager not available")
            return
        
        try:
            print("📊 Generating migration analysis report...")
            report = await self.compatibility_manager.generate_migration_report()
            
            if "error" in report:
                print(f"❌ {report['error']}")
                return
            
            analysis = report["migration_analysis"]
            config = report["current_config"]
            
            print("\n📈 Migration Analysis Report")
            print("-" * 40)
            print(f"  📊 Total requests: {analysis['total_requests']}")
            print(f"  🤖 Intelligent system:")
            print(f"     Requests: {analysis['intelligent_system']['requests']}")
            print(f"     Success rate: {analysis['intelligent_system']['success_rate']:.1f}%")
            print(f"     Avg time: {analysis['intelligent_system']['avg_response_time']:.2f}s")
            print(f"  🔙 Legacy system:")
            print(f"     Requests: {analysis['legacy_system']['requests']}")
            print(f"     Success rate: {analysis['legacy_system']['success_rate']:.1f}%")
            print(f"     Avg time: {analysis['legacy_system']['avg_response_time']:.2f}s")
            
            print(f"\n🎯 Recommendation: {analysis['recommendation']}")
            print(f"📅 Generated: {report['generated_at']}")
            
            # Save detailed report
            report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"💾 Detailed report saved: {report_file}")
            
        except Exception as e:
            print(f"❌ Error generating migration report: {e}")
    
    async def run_parity_validation(self):
        """Run Claude Code CLI parity validation"""
        print("🔍 Running Claude Code CLI Parity Validation...")
        print("Testing original failing queries with current system...")
        
        # Test the original failing queries
        critical_queries = [
            ("Device Type Query", "device type information for Cisco C9200-48P"),
            ("Device Info Query", "device info for dc1-sw01"),
            ("Rack Elevation Query", "rack elevation for R01-A15"),
            ("Device Interfaces Query", "show interfaces for device dc1-sw01")
        ]
        
        results = []
        
        for name, query in critical_queries:
            print(f"\n🧪 Testing: {name}")
            success = await self.process_query(query, force_system="intelligent")
            results.append((name, success))
            
        # Summary
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        print(f"\n📊 Claude Code CLI Parity Validation Results:")
        print("-" * 50)
        for name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status}: {name}")
        
        print(f"\n🎯 Overall: {passed}/{total} queries working")
        
        if passed == total:
            print("🎉 CLAUDE CODE CLI PARITY ACHIEVED!")
            print("✅ All originally failing queries now work correctly")
        else:
            print("⚠️ Parity not yet achieved - some queries still failing")
            print("🔧 Additional fixes needed")
    
    def show_help(self):
        """Show help information"""
        print(f"\n📚 Phase 5 Integrated CLI Help:")
        print(f"\n🎯 What This Demonstrates:")
        print(f"  • Backward compatibility between legacy and intelligent systems")
        print(f"  • A/B testing for migration validation")
        print(f"  • Seamless fallback on system failures")
        print(f"  • Migration tracking and analysis")
        print(f"  • Claude Code CLI parity validation")
        
        print(f"\n🤖 System Integration:")
        print(f"  • Phase 1: IntelligentToolSelector - LLM-powered tool selection")
        print(f"  • Phase 2: ToolAwareParameterExtractor - Context preservation")
        print(f"  • Phase 3: LangGraph Workflow - Intelligent orchestration")
        print(f"  • Phase 4: Intelligent Fallback - Error recovery")
        print(f"  • Phase 5: Backward Compatibility - Migration support")
        
        print(f"\n🔧 Current Integration:")
        print(f"  • Migration Phase: {self.migration_phase.value}")
        print(f"  • Feature Flags: Active for current phase")
        print(f"  • Performance Monitoring: Enabled")
        print(f"  • Migration Tracking: Enabled")
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.compatibility_manager:
                # Save final tracking data
                await self.compatibility_manager._persist_tracking_data()
                print("✅ Compatibility system shut down successfully")
        except Exception as e:
            print(f"⚠️ Warning during cleanup: {e}")


async def run_batch_validation():
    """Run batch validation of critical queries"""
    cli = Phase5IntegratedCLI(MigrationPhase.INTELLIGENT_ONLY)
    
    if not await cli.initialize():
        return False
    
    print("\n🧪 Running Batch Validation - Critical Failing Queries")
    print("=" * 60)
    
    critical_queries = [
        "device type information for Cisco C9200-48P",
        "device info for dc1-sw01", 
        "rack elevation for R01-A15",
        "show interfaces for device dc1-sw01"
    ]
    
    success_count = 0
    for i, query in enumerate(critical_queries, 1):
        print(f"\n📝 Critical Test {i}/{len(critical_queries)}")
        if await cli.process_query(query):
            success_count += 1
    
    print(f"\n📊 Critical Query Validation Results:")
    print(f"  ✅ Successful: {success_count}/{len(critical_queries)}")
    print(f"  📈 Success rate: {(success_count/len(critical_queries)*100):.1f}%")
    
    parity_achieved = success_count == len(critical_queries)
    
    if parity_achieved:
        print("\n🎉 CLAUDE CODE CLI PARITY ACHIEVED!")
        print("✅ All originally failing queries now work correctly")
        print("🚀 Migration to intelligent system recommended")
    else:
        print("\n⚠️ Claude Code CLI parity NOT achieved")
        print("🔧 Additional fixes needed before migration")
    
    await cli.cleanup()
    return parity_achieved


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Phase 5 Integrated NetBox MCP CLI with Backward Compatibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode with mixed system
  netbox-mcp-phase5 --interactive --phase mixed_mode
  
  # Batch validation of critical queries  
  netbox-mcp-phase5 --batch-validate
  
  # Single query with intelligent system
  netbox-mcp-phase5 --query "device info for dc1-sw01" --phase intelligent_only
  
  # Migration phase testing
  netbox-mcp-phase5 --interactive --phase legacy_only
        """
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start interactive CLI mode (default)"
    )
    
    parser.add_argument(
        "--batch-validate", "-b",
        action="store_true",
        help="Run batch validation of critical failing queries"
    )
    
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Process a single query and exit"
    )
    
    parser.add_argument(
        "--phase", "-p",
        choices=["legacy_only", "mixed_mode", "intelligent_preferred", "intelligent_only"],
        default="mixed_mode",
        help="Migration phase to use (default: mixed_mode)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Map phase string to enum
    phase_map = {
        "legacy_only": MigrationPhase.LEGACY_ONLY,
        "mixed_mode": MigrationPhase.MIXED_MODE,
        "intelligent_preferred": MigrationPhase.INTELLIGENT_PREFERRED,
        "intelligent_only": MigrationPhase.INTELLIGENT_ONLY
    }
    
    migration_phase = phase_map[args.phase]
    
    async def main_async():
        """Async main function"""
        
        if args.batch_validate:
            success = await run_batch_validation()
            return 0 if success else 1
        
        cli = Phase5IntegratedCLI(migration_phase)
        
        try:
            if not await cli.initialize():
                return 1
            
            if args.query:
                success = await cli.process_query(args.query)
                await cli.cleanup()
                return 0 if success else 1
            else:
                # Default to interactive mode
                await cli.run_interactive()
                await cli.cleanup()
                return 0
                
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            logger.exception("Full error details:")
            return 1
    
    # Run the async main function
    try:
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
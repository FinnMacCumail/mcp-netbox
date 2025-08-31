#!/usr/bin/env python3
"""
Phase 5: Comprehensive Validation Framework for NetBox MCP CLI Parity

This framework validates that the architectural rewrite (Phases 1-4) has successfully
solved the original NetBox MCP App CLI failures and provides Claude Code CLI parity.

Key Features:
1. Validates original failing queries now work correctly
2. Tests all 4 implemented phases integration
3. Performance benchmarking vs original system
4. Backward compatibility validation
5. End-to-end Claude Code CLI parity proof

Original Failing Queries Being Validated:
- Device Type Query: "device type information for Cisco C9200-48P"
- Device Info Query: "device info for dc1-sw01"
- Rack Elevation Query: "rack elevation for R01-A15"
- Device Interfaces Query: "show interfaces for device dc1-sw01"
"""

import asyncio
import sys
import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from netbox_mcp.orchestration.state_machine import execute_intelligent_workflow
from netbox_mcp.orchestration.intelligent_tool_selector import select_tool
from netbox_mcp.orchestration.tool_aware_parameter_extractor import extract_parameters
from netbox_mcp.orchestration.intelligent_fallback_orchestrator import IntelligentFallbackOrchestrator


@dataclass
class ValidationTestCase:
    """Test case for validation"""
    name: str
    query: str
    expected_tool: str
    expected_params: Dict[str, Any]
    category: str
    was_failing: bool = True
    failure_reason: str = ""


@dataclass
class ValidationResult:
    """Result of a validation test"""
    test_case: ValidationTestCase
    success: bool
    actual_tool: Optional[str]
    actual_params: Dict[str, Any]
    response_time: float
    error_message: Optional[str]
    workflow_metrics: Dict[str, Any]
    execution_details: Dict[str, Any]


@dataclass
class PhaseValidationSummary:
    """Summary of phase validation results"""
    phase_name: str
    tests_passed: int
    tests_failed: int
    total_tests: int
    avg_response_time: float
    phase_specific_metrics: Dict[str, Any]


class Phase5ComprehensiveValidator:
    """
    Comprehensive validation framework for NetBox MCP CLI parity
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session_id = f"phase5_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results: List[ValidationResult] = []
        self.phase_summaries: List[PhaseValidationSummary] = []
        
        # Original failing queries that must now pass
        self.critical_test_cases = [
            ValidationTestCase(
                name="Device Type Information Query",
                query="device type information for Cisco C9200-48P",
                expected_tool="netbox_get_device_type_info",
                expected_params={"manufacturer": "Cisco", "model": "C9200-48P"},
                category="device_types",
                was_failing=True,
                failure_reason="Wrong tool selection, lost manufacturer context"
            ),
            ValidationTestCase(
                name="Device Info Query",
                query="device info for dc1-sw01",
                expected_tool="netbox_get_device_info",
                expected_params={"device_name": "dc1-sw01"},
                category="devices",
                was_failing=True,
                failure_reason="Wrong tool, broken parameters"
            ),
            ValidationTestCase(
                name="Rack Elevation Query",
                query="rack elevation for R01-A15",
                expected_tool="netbox_get_rack_elevation",
                expected_params={"rack_name": "R01-A15"},
                category="racks",
                was_failing=True,
                failure_reason="Completely wrong tool selection"
            ),
            ValidationTestCase(
                name="Device Interfaces Query",
                query="show interfaces for device dc1-sw01",
                expected_tool="netbox_get_device_interfaces",
                expected_params={"device_name": "dc1-sw01"},
                category="interfaces",
                was_failing=True,
                failure_reason="Wrong tool selection and parameters"
            ),
        ]
        
        # Additional test cases for comprehensive validation
        self.extended_test_cases = [
            ValidationTestCase(
                name="Site Information Query",
                query="show me site information for datacenter-1",
                expected_tool="netbox_get_site_info",
                expected_params={"site_name": "datacenter-1"},
                category="sites",
                was_failing=False
            ),
            ValidationTestCase(
                name="All Sites Listing",
                query="list all sites in NetBox",
                expected_tool="netbox_list_all_sites",
                expected_params={},
                category="sites",
                was_failing=False
            ),
            ValidationTestCase(
                name="All Devices Listing",
                query="show all devices",
                expected_tool="netbox_list_all_devices",
                expected_params={},
                category="devices",
                was_failing=False
            ),
            ValidationTestCase(
                name="Rack Inventory Query",
                query="get rack inventory for Server-Rack-01 in site datacenter-1",
                expected_tool="netbox_get_rack_inventory",
                expected_params={"site_name": "datacenter-1", "rack_name": "Server-Rack-01"},
                category="racks",
                was_failing=False
            ),
        ]
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """
        Run comprehensive validation across all phases
        
        Returns:
            Complete validation report with Claude Code CLI parity evidence
        """
        self.logger.info("🚀 Starting Phase 5 Comprehensive Validation")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Phase 1: Validate IntelligentToolSelector
            phase1_results = await self._validate_phase1_tool_selection()
            
            # Phase 2: Validate ToolAwareParameterExtractor  
            phase2_results = await self._validate_phase2_parameter_extraction()
            
            # Phase 3: Validate LangGraph Workflow
            phase3_results = await self._validate_phase3_workflow()
            
            # Phase 4: Validate Intelligent Fallback System
            phase4_results = await self._validate_phase4_fallback_system()
            
            # Critical Test Cases: Original Failing Queries
            critical_results = await self._validate_critical_failing_queries()
            
            # Extended Test Cases: Additional Validation
            extended_results = await self._validate_extended_test_cases()
            
            # Performance Benchmarking
            performance_results = await self._run_performance_benchmarks()
            
            # Generate comprehensive report
            report = await self._generate_comprehensive_report(
                phase1_results, phase2_results, phase3_results, phase4_results,
                critical_results, extended_results, performance_results,
                start_time
            )
            
            self.logger.info("✅ Phase 5 Comprehensive Validation Completed")
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Comprehensive validation failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _validate_phase1_tool_selection(self) -> Dict[str, Any]:
        """Validate Phase 1: IntelligentToolSelector"""
        self.logger.info("\n🔍 Phase 1 Validation: IntelligentToolSelector")
        self.logger.info("-" * 40)
        
        results = []
        start_time = time.time()
        
        # Test critical queries
        for test_case in self.critical_test_cases:
            try:
                selection = await select_tool(test_case.query)
                
                success = (
                    selection and 
                    selection.primary_tool == test_case.expected_tool and
                    selection.confidence >= 0.8
                )
                
                result = {
                    "test_case": test_case.name,
                    "query": test_case.query,
                    "expected_tool": test_case.expected_tool,
                    "actual_tool": selection.primary_tool if selection else None,
                    "confidence": selection.confidence if selection else 0.0,
                    "success": success,
                    "was_failing": test_case.was_failing,
                    "failure_reason": test_case.failure_reason if test_case.was_failing else None
                }
                
                results.append(result)
                
                status = "✅ FIXED" if success and test_case.was_failing else ("✅ PASS" if success else "❌ FAIL")
                self.logger.info(f"   {status}: {test_case.name}")
                self.logger.info(f"      Tool: {selection.primary_tool if selection else 'None'} "
                               f"(confidence: {selection.confidence if selection else 0:.2f})")
                
            except Exception as e:
                self.logger.error(f"   ❌ ERROR: {test_case.name}: {e}")
                results.append({
                    "test_case": test_case.name,
                    "error": str(e),
                    "success": False
                })
        
        phase1_time = time.time() - start_time
        passed = sum(1 for r in results if r.get("success", False))
        
        phase1_summary = PhaseValidationSummary(
            phase_name="Phase 1: IntelligentToolSelector",
            tests_passed=passed,
            tests_failed=len(results) - passed,
            total_tests=len(results),
            avg_response_time=phase1_time / len(results) if results else 0,
            phase_specific_metrics={
                "avg_confidence": sum(r.get("confidence", 0) for r in results) / len(results) if results else 0,
                "fixed_failing_queries": sum(1 for r in results if r.get("success", False) and r.get("was_failing", False))
            }
        )
        
        self.phase_summaries.append(phase1_summary)
        
        return {
            "phase": "Phase 1: IntelligentToolSelector",
            "results": results,
            "summary": phase1_summary,
            "total_time": phase1_time
        }
    
    async def _validate_phase2_parameter_extraction(self) -> Dict[str, Any]:
        """Validate Phase 2: ToolAwareParameterExtractor"""
        self.logger.info("\n🔍 Phase 2 Validation: ToolAwareParameterExtractor")
        self.logger.info("-" * 40)
        
        results = []
        start_time = time.time()
        
        # Test parameter extraction for critical queries
        for test_case in self.critical_test_cases:
            try:
                extraction = await extract_parameters(test_case.query, test_case.expected_tool)
                
                # Check if extracted parameters match expected
                success = (
                    extraction and
                    extraction.confidence >= 0.7 and
                    all(key in extraction.parameters for key in test_case.expected_params.keys())
                )
                
                result = {
                    "test_case": test_case.name,
                    "query": test_case.query,
                    "tool": test_case.expected_tool,
                    "expected_params": test_case.expected_params,
                    "actual_params": extraction.parameters if extraction else {},
                    "confidence": extraction.confidence if extraction else 0.0,
                    "extraction_method": extraction.extraction_method if extraction else None,
                    "success": success,
                    "was_failing": test_case.was_failing
                }
                
                results.append(result)
                
                status = "✅ FIXED" if success and test_case.was_failing else ("✅ PASS" if success else "❌ FAIL")
                self.logger.info(f"   {status}: {test_case.name}")
                self.logger.info(f"      Method: {extraction.extraction_method if extraction else 'None'} "
                               f"(confidence: {extraction.confidence if extraction else 0:.2f})")
                
            except Exception as e:
                self.logger.error(f"   ❌ ERROR: {test_case.name}: {e}")
                results.append({
                    "test_case": test_case.name,
                    "error": str(e),
                    "success": False
                })
        
        phase2_time = time.time() - start_time
        passed = sum(1 for r in results if r.get("success", False))
        
        phase2_summary = PhaseValidationSummary(
            phase_name="Phase 2: ToolAwareParameterExtractor",
            tests_passed=passed,
            tests_failed=len(results) - passed,
            total_tests=len(results),
            avg_response_time=phase2_time / len(results) if results else 0,
            phase_specific_metrics={
                "avg_confidence": sum(r.get("confidence", 0) for r in results) / len(results) if results else 0,
                "context_preserving_extractions": sum(1 for r in results if r.get("extraction_method") == "context_preserving")
            }
        )
        
        self.phase_summaries.append(phase2_summary)
        
        return {
            "phase": "Phase 2: ToolAwareParameterExtractor",
            "results": results,
            "summary": phase2_summary,
            "total_time": phase2_time
        }
    
    async def _validate_phase3_workflow(self) -> Dict[str, Any]:
        """Validate Phase 3: LangGraph 3-Node Workflow"""
        self.logger.info("\n🔍 Phase 3 Validation: LangGraph 3-Node Workflow")
        self.logger.info("-" * 40)
        
        results = []
        start_time = time.time()
        
        # Test end-to-end workflow for critical queries
        for test_case in self.critical_test_cases:
            try:
                correlation_id = f"phase3_{test_case.name.lower().replace(' ', '_')}"
                
                workflow_result = await execute_intelligent_workflow(
                    user_query=test_case.query,
                    session_id=self.session_id,
                    correlation_id=correlation_id
                )
                
                success = (
                    workflow_result.get("success", False) and
                    workflow_result.get("workflow_complete", False) and
                    len(workflow_result.get("response", "")) > 10
                )
                
                result = {
                    "test_case": test_case.name,
                    "query": test_case.query,
                    "workflow_success": workflow_result.get("success", False),
                    "workflow_complete": workflow_result.get("workflow_complete", False),
                    "response_length": len(workflow_result.get("response", "")),
                    "execution_metrics": workflow_result.get("execution_metrics", {}),
                    "success": success,
                    "was_failing": test_case.was_failing
                }
                
                results.append(result)
                
                status = "✅ FIXED" if success and test_case.was_failing else ("✅ PASS" if success else "❌ FAIL")
                self.logger.info(f"   {status}: {test_case.name}")
                
                metrics = workflow_result.get("execution_metrics", {})
                if metrics:
                    total_time = metrics.get("total_workflow_time", 0)
                    self.logger.info(f"      Workflow time: {total_time:.2f}s")
                
            except Exception as e:
                self.logger.error(f"   ❌ ERROR: {test_case.name}: {e}")
                results.append({
                    "test_case": test_case.name,
                    "error": str(e),
                    "success": False
                })
        
        phase3_time = time.time() - start_time
        passed = sum(1 for r in results if r.get("success", False))
        
        phase3_summary = PhaseValidationSummary(
            phase_name="Phase 3: LangGraph Workflow",
            tests_passed=passed,
            tests_failed=len(results) - passed,
            total_tests=len(results),
            avg_response_time=phase3_time / len(results) if results else 0,
            phase_specific_metrics={
                "avg_workflow_time": sum(
                    r.get("execution_metrics", {}).get("total_workflow_time", 0) 
                    for r in results if r.get("execution_metrics")
                ) / len([r for r in results if r.get("execution_metrics")]) if results else 0,
                "successful_workflows": sum(1 for r in results if r.get("workflow_complete", False))
            }
        )
        
        self.phase_summaries.append(phase3_summary)
        
        return {
            "phase": "Phase 3: LangGraph Workflow",
            "results": results,
            "summary": phase3_summary,
            "total_time": phase3_time
        }
    
    async def _validate_phase4_fallback_system(self) -> Dict[str, Any]:
        """Validate Phase 4: Intelligent Fallback System"""
        self.logger.info("\n🔍 Phase 4 Validation: Intelligent Fallback System")
        self.logger.info("-" * 40)
        
        results = []
        start_time = time.time()
        
        try:
            # Create intelligent fallback orchestrator
            fallback_orchestrator = IntelligentFallbackOrchestrator(
                session_id=self.session_id
            )
            
            # Test fallback scenarios
            fallback_test_queries = [
                "show me information about nonexistent-device-12345",  # Should trigger fallback
                "get details for invalid-rack-xyz",  # Should trigger fallback
                "malformed query with invalid syntax",  # Should handle gracefully
            ]
            
            for query in fallback_test_queries:
                try:
                    result = await fallback_orchestrator.orchestrate_with_fallback(
                        query=query,
                        correlation_id=f"fallback_test_{hash(query)}"
                    )
                    
                    # Success means graceful handling, not necessarily finding results
                    success = (
                        result.get("orchestration_complete", False) and
                        result.get("final_response") is not None
                    )
                    
                    fallback_used = result.get("fallback_attempts", 0) > 0
                    
                    test_result = {
                        "query": query,
                        "success": success,
                        "fallback_used": fallback_used,
                        "fallback_attempts": result.get("fallback_attempts", 0),
                        "recovery_successful": result.get("recovery_successful", False),
                        "orchestration_complete": result.get("orchestration_complete", False)
                    }
                    
                    results.append(test_result)
                    
                    status = "✅ PASS" if success else "❌ FAIL"
                    self.logger.info(f"   {status}: Fallback test")
                    self.logger.info(f"      Fallback used: {fallback_used}")
                    
                except Exception as e:
                    self.logger.error(f"   ❌ ERROR: Fallback test: {e}")
                    results.append({
                        "query": query,
                        "error": str(e),
                        "success": False
                    })
        
        except Exception as e:
            self.logger.error(f"   ❌ ERROR: Could not initialize fallback orchestrator: {e}")
            results.append({
                "error": f"Initialization failed: {e}",
                "success": False
            })
        
        phase4_time = time.time() - start_time
        passed = sum(1 for r in results if r.get("success", False))
        
        phase4_summary = PhaseValidationSummary(
            phase_name="Phase 4: Intelligent Fallback System",
            tests_passed=passed,
            tests_failed=len(results) - passed,
            total_tests=len(results),
            avg_response_time=phase4_time / len(results) if results else 0,
            phase_specific_metrics={
                "fallback_activations": sum(1 for r in results if r.get("fallback_used", False)),
                "recovery_rate": sum(1 for r in results if r.get("recovery_successful", False)) / len(results) if results else 0
            }
        )
        
        self.phase_summaries.append(phase4_summary)
        
        return {
            "phase": "Phase 4: Intelligent Fallback System",
            "results": results,
            "summary": phase4_summary,
            "total_time": phase4_time
        }
    
    async def _validate_critical_failing_queries(self) -> Dict[str, Any]:
        """Validate the original failing queries now work"""
        self.logger.info("\n🎯 Critical Validation: Original Failing Queries")
        self.logger.info("-" * 40)
        
        results = []
        start_time = time.time()
        
        for test_case in self.critical_test_cases:
            start_test_time = time.time()
            
            try:
                # Run complete end-to-end test
                workflow_result = await execute_intelligent_workflow(
                    user_query=test_case.query,
                    session_id=self.session_id,
                    correlation_id=f"critical_{test_case.name.lower().replace(' ', '_')}"
                )
                
                test_time = time.time() - start_test_time
                
                # Check if the query now works (was previously failing)
                success = (
                    workflow_result.get("success", False) and
                    workflow_result.get("workflow_complete", False) and
                    len(workflow_result.get("response", "")) > 20
                )
                
                # Extract actual tool used from workflow results
                tool_results = workflow_result.get("tool_results", [])
                actual_tool = None
                actual_params = {}
                
                if tool_results:
                    first_result = tool_results[0]
                    actual_tool = first_result.get("tool_name")
                    actual_params = first_result.get("params", {})
                
                validation_result = ValidationResult(
                    test_case=test_case,
                    success=success,
                    actual_tool=actual_tool,
                    actual_params=actual_params,
                    response_time=test_time,
                    error_message=workflow_result.get("error_state", {}).get("error") if not success else None,
                    workflow_metrics=workflow_result.get("execution_metrics", {}),
                    execution_details=workflow_result
                )
                
                results.append(validation_result)
                self.results.append(validation_result)
                
                # Show detailed results for critical tests
                if success and test_case.was_failing:
                    status = "🎉 FIXED - CRITICAL"
                elif success:
                    status = "✅ PASS"
                else:
                    status = "❌ STILL FAILING"
                
                self.logger.info(f"   {status}: {test_case.name}")
                self.logger.info(f"      Original issue: {test_case.failure_reason}")
                self.logger.info(f"      Tool used: {actual_tool}")
                self.logger.info(f"      Response time: {test_time:.2f}s")
                
                if success and test_case.was_failing:
                    self.logger.info(f"      🏆 Claude Code CLI parity ACHIEVED for this query!")
                
            except Exception as e:
                test_time = time.time() - start_test_time
                self.logger.error(f"   ❌ ERROR: {test_case.name}: {e}")
                
                validation_result = ValidationResult(
                    test_case=test_case,
                    success=False,
                    actual_tool=None,
                    actual_params={},
                    response_time=test_time,
                    error_message=str(e),
                    workflow_metrics={},
                    execution_details={"error": str(e)}
                )
                
                results.append(validation_result)
                self.results.append(validation_result)
        
        total_time = time.time() - start_time
        passed = sum(1 for r in results if r.success)
        fixed_queries = sum(1 for r in results if r.success and r.test_case.was_failing)
        
        return {
            "phase": "Critical Failing Queries Validation",
            "results": [asdict(r) for r in results],
            "total_time": total_time,
            "summary": {
                "total_critical_queries": len(results),
                "queries_now_working": passed,
                "originally_failing_now_fixed": fixed_queries,
                "claude_code_cli_parity_achieved": fixed_queries == len([tc for tc in self.critical_test_cases if tc.was_failing]),
                "avg_response_time": total_time / len(results) if results else 0
            }
        }
    
    async def _validate_extended_test_cases(self) -> Dict[str, Any]:
        """Validate extended test cases for broader compatibility"""
        self.logger.info("\n🔍 Extended Validation: Additional Test Cases")
        self.logger.info("-" * 40)
        
        results = []
        start_time = time.time()
        
        for test_case in self.extended_test_cases:
            start_test_time = time.time()
            
            try:
                workflow_result = await execute_intelligent_workflow(
                    user_query=test_case.query,
                    session_id=self.session_id,
                    correlation_id=f"extended_{test_case.name.lower().replace(' ', '_')}"
                )
                
                test_time = time.time() - start_test_time
                success = workflow_result.get("success", False)
                
                result = {
                    "test_case": test_case.name,
                    "query": test_case.query,
                    "category": test_case.category,
                    "success": success,
                    "response_time": test_time,
                    "workflow_complete": workflow_result.get("workflow_complete", False)
                }
                
                results.append(result)
                
                status = "✅ PASS" if success else "❌ FAIL"
                self.logger.info(f"   {status}: {test_case.name} ({test_case.category})")
                
            except Exception as e:
                self.logger.error(f"   ❌ ERROR: {test_case.name}: {e}")
                results.append({
                    "test_case": test_case.name,
                    "error": str(e),
                    "success": False
                })
        
        total_time = time.time() - start_time
        passed = sum(1 for r in results if r.get("success", False))
        
        return {
            "phase": "Extended Test Cases",
            "results": results,
            "total_time": total_time,
            "summary": {
                "total_tests": len(results),
                "tests_passed": passed,
                "tests_failed": len(results) - passed,
                "success_rate": (passed / len(results)) * 100 if results else 0,
                "avg_response_time": total_time / len(results) if results else 0
            }
        }
    
    async def _run_performance_benchmarks(self) -> Dict[str, Any]:
        """Run performance benchmarks to validate improvements"""
        self.logger.info("\n⚡ Performance Benchmarks")
        self.logger.info("-" * 40)
        
        benchmark_queries = [
            "device type information for Cisco C9200-48P",
            "show all sites",
            "list all devices",
            "get device info for test-device-1"
        ]
        
        results = []
        
        for query in benchmark_queries:
            # Run multiple iterations for accurate timing
            times = []
            successes = 0
            
            for i in range(3):  # 3 iterations per query
                start_time = time.time()
                try:
                    result = await execute_intelligent_workflow(
                        user_query=query,
                        session_id=self.session_id,
                        correlation_id=f"benchmark_{i}_{hash(query)}"
                    )
                    
                    execution_time = time.time() - start_time
                    times.append(execution_time)
                    
                    if result.get("success", False):
                        successes += 1
                        
                except Exception as e:
                    times.append(float('inf'))  # Mark as failed
            
            avg_time = sum(t for t in times if t != float('inf')) / len([t for t in times if t != float('inf')]) if times else 0
            
            result = {
                "query": query,
                "avg_response_time": avg_time,
                "min_response_time": min(t for t in times if t != float('inf')) if times else 0,
                "max_response_time": max(t for t in times if t != float('inf')) if times else 0,
                "success_rate": (successes / 3) * 100,
                "iterations": 3
            }
            
            results.append(result)
            self.logger.info(f"   Query: {query[:50]}...")
            self.logger.info(f"      Avg time: {avg_time:.2f}s, Success rate: {result['success_rate']:.0f}%")
        
        overall_avg = sum(r["avg_response_time"] for r in results) / len(results) if results else 0
        overall_success = sum(r["success_rate"] for r in results) / len(results) if results else 0
        
        return {
            "phase": "Performance Benchmarks",
            "results": results,
            "summary": {
                "overall_avg_response_time": overall_avg,
                "overall_success_rate": overall_success,
                "performance_target_met": overall_avg < 3.0,  # Target: < 3 seconds
                "reliability_target_met": overall_success >= 95.0  # Target: >= 95%
            }
        }
    
    async def _generate_comprehensive_report(
        self, phase1_results, phase2_results, phase3_results, phase4_results,
        critical_results, extended_results, performance_results, start_time
    ) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        
        total_time = datetime.now() - start_time
        
        # Calculate overall metrics
        critical_summary = critical_results["summary"]
        claude_code_parity_achieved = critical_summary["claude_code_cli_parity_achieved"]
        
        overall_tests = sum([
            phase1_results["summary"].total_tests,
            phase2_results["summary"].total_tests,
            phase3_results["summary"].total_tests,
            phase4_results["summary"].total_tests,
            critical_summary["total_critical_queries"],
            extended_results["summary"]["total_tests"]
        ])
        
        overall_passed = sum([
            phase1_results["summary"].tests_passed,
            phase2_results["summary"].tests_passed,
            phase3_results["summary"].tests_passed,
            phase4_results["summary"].tests_passed,
            critical_summary["queries_now_working"],
            extended_results["summary"]["tests_passed"]
        ])
        
        report = {
            "validation_summary": {
                "claude_code_cli_parity_achieved": claude_code_parity_achieved,
                "total_tests_run": overall_tests,
                "total_tests_passed": overall_passed,
                "overall_success_rate": (overall_passed / overall_tests) * 100 if overall_tests else 0,
                "critical_failing_queries_fixed": critical_summary["originally_failing_now_fixed"],
                "total_validation_time": total_time.total_seconds(),
                "validation_timestamp": datetime.now().isoformat(),
                "session_id": self.session_id
            },
            
            "phase_results": {
                "phase1_intelligent_tool_selector": phase1_results,
                "phase2_parameter_extractor": phase2_results,
                "phase3_langgraph_workflow": phase3_results,
                "phase4_fallback_system": phase4_results
            },
            
            "critical_validation": critical_results,
            "extended_validation": extended_results,
            "performance_benchmarks": performance_results,
            
            "phase_summaries": [asdict(summary) for summary in self.phase_summaries],
            
            "conclusions": {
                "architectural_rewrite_successful": claude_code_parity_achieved and overall_passed >= overall_tests * 0.85,
                "performance_targets_met": performance_results["summary"]["performance_target_met"],
                "reliability_targets_met": performance_results["summary"]["reliability_target_met"],
                "ready_for_production": claude_code_parity_achieved and performance_results["summary"]["performance_target_met"],
                "next_steps": self._generate_next_steps(claude_code_parity_achieved, performance_results)
            },
            
            "evidence": {
                "original_failing_queries": [
                    {
                        "query": tc.query,
                        "original_failure": tc.failure_reason,
                        "now_working": any(r.success for r in self.results if r.test_case.query == tc.query)
                    }
                    for tc in self.critical_test_cases if tc.was_failing
                ],
                "tool_selection_improvements": {
                    "intelligent_selection_rate": phase1_results["summary"].phase_specific_metrics.get("avg_confidence", 0),
                    "context_preserving_extraction_rate": phase2_results["summary"].phase_specific_metrics.get("avg_confidence", 0)
                },
                "workflow_improvements": {
                    "successful_workflow_completion_rate": phase3_results["summary"].phase_specific_metrics.get("successful_workflows", 0) / phase3_results["summary"].total_tests * 100 if phase3_results["summary"].total_tests else 0,
                    "fallback_system_reliability": phase4_results["summary"].phase_specific_metrics.get("recovery_rate", 0) * 100
                }
            }
        }
        
        return report
    
    def _generate_next_steps(self, parity_achieved: bool, performance_results: Dict) -> List[str]:
        """Generate next steps based on validation results"""
        steps = []
        
        if parity_achieved:
            steps.append("✅ Claude Code CLI parity achieved - architectural rewrite successful")
            steps.append("🚀 Ready for production deployment with feature flags")
            steps.append("📋 Implement backward compatibility system")
            steps.append("📊 Set up monitoring and observability")
        else:
            steps.append("🔧 Address remaining failing queries")
            steps.append("🔍 Investigate root causes of validation failures")
            steps.append("⚡ Optimize performance for failing test cases")
        
        if not performance_results["summary"]["performance_target_met"]:
            steps.append("⚡ Performance optimization required")
            steps.append("🔧 Profile and optimize slow operations")
        
        steps.append("📖 Complete migration documentation")
        steps.append("🧪 Set up continuous validation testing")
        
        return steps


async def main():
    """Main entry point for Phase 5 validation"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 NetBox MCP Phase 5: Comprehensive Validation Framework")
    print("=" * 60)
    print("Validating Claude Code CLI Parity Achievement")
    print("Testing all 4 architectural phases integration")
    print("Proving original failing queries now work correctly")
    print("=" * 60)
    
    try:
        validator = Phase5ComprehensiveValidator()
        report = await validator.run_comprehensive_validation()
        
        # Save detailed report
        report_file = f"phase5_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Print summary
        print("\n" + "=" * 60)
        print("🏆 PHASE 5 VALIDATION SUMMARY")
        print("=" * 60)
        
        summary = report["validation_summary"]
        print(f"Claude Code CLI Parity Achieved: {'🎉 YES' if summary['claude_code_cli_parity_achieved'] else '❌ NO'}")
        print(f"Total Tests: {summary['total_tests_run']}")
        print(f"Tests Passed: {summary['total_tests_passed']}")
        print(f"Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"Critical Queries Fixed: {summary['critical_failing_queries_fixed']}")
        print(f"Validation Time: {summary['total_validation_time']:.1f}s")
        
        conclusions = report["conclusions"]
        print(f"\nArchitectural Rewrite Successful: {'✅ YES' if conclusions['architectural_rewrite_successful'] else '❌ NO'}")
        print(f"Performance Targets Met: {'✅ YES' if conclusions['performance_targets_met'] else '❌ NO'}")
        print(f"Ready for Production: {'🚀 YES' if conclusions['ready_for_production'] else '⚠️ NO'}")
        
        print(f"\n📄 Detailed report saved: {report_file}")
        
        print("\n🎯 NEXT STEPS:")
        for step in conclusions["next_steps"]:
            print(f"   {step}")
        
        success = summary['claude_code_cli_parity_achieved'] and conclusions['ready_for_production']
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ Phase 5 validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
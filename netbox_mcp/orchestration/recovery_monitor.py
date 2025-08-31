#!/usr/bin/env python3
"""
Error Recovery System Monitoring and Statistics

This module provides comprehensive monitoring capabilities for the error recovery
system, including real-time statistics, health checks, and performance metrics.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from .error_recovery import get_recovery_statistics, error_recovery_engine
from .param_validator import parameter_validator

logger = logging.getLogger(__name__)


@dataclass
class SystemHealthStatus:
    """Overall system health status."""
    status: str  # healthy, degraded, critical
    recovery_rate: float
    circuit_breakers_open: int
    total_tools: int
    error_trends: Dict[str, Any]
    recommendations: List[str]
    timestamp: str


class RecoveryMonitor:
    """
    Comprehensive monitoring system for error recovery operations.
    
    Provides real-time insights into recovery performance, tool reliability,
    and system health to enable proactive maintenance and optimization.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.monitoring_stats = {
            "monitoring_start_time": datetime.now(),
            "total_monitoring_calls": 0,
            "health_check_calls": 0,
            "statistics_requests": 0
        }
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive recovery system statistics."""
        self.monitoring_stats["statistics_requests"] += 1
        
        # Get recovery statistics
        recovery_stats = get_recovery_statistics()
        
        # Add parameter validator statistics
        param_stats = {
            "total_tools_configured": len(parameter_validator.tool_specs),
            "global_aliases_count": len(parameter_validator.global_aliases),
            "parameter_specs_count": sum(
                len(specs) for specs in parameter_validator.tool_specs.values()
            )
        }
        
        # Calculate derived metrics
        total_errors = recovery_stats["recovery_stats"]["total_errors"]
        recovered_errors = recovery_stats["recovery_stats"]["recovered_errors"]
        recovery_rate = (recovered_errors / total_errors * 100) if total_errors > 0 else 100.0
        
        # Tool reliability analysis
        tool_reliability = self._analyze_tool_reliability(recovery_stats)
        
        # Error pattern analysis
        error_patterns = self._analyze_error_patterns(recovery_stats)
        
        return {
            "overview": {
                "recovery_rate_percent": round(recovery_rate, 2),
                "total_errors_handled": total_errors,
                "successful_recoveries": recovered_errors,
                "fallback_successes": recovery_stats["recovery_stats"]["fallback_successes"],
                "circuit_breaks_active": recovery_stats["recovery_stats"]["circuit_breaks"],
                "parameter_corrections": recovery_stats["recovery_stats"]["parameter_corrections"]
            },
            "recovery_statistics": recovery_stats,
            "parameter_validation": param_stats,
            "tool_reliability": tool_reliability,
            "error_patterns": error_patterns,
            "monitoring_metadata": {
                **self.monitoring_stats,
                "uptime_seconds": (datetime.now() - self.monitoring_stats["monitoring_start_time"]).total_seconds(),
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def get_system_health(self) -> SystemHealthStatus:
        """Assess overall system health."""
        self.monitoring_stats["health_check_calls"] += 1
        
        recovery_stats = get_recovery_statistics()
        
        # Calculate health metrics
        total_errors = recovery_stats["recovery_stats"]["total_errors"]
        recovered_errors = recovery_stats["recovery_stats"]["recovered_errors"]
        recovery_rate = (recovered_errors / total_errors) if total_errors > 0 else 1.0
        
        circuit_breakers_open = len([
            cb for cb in recovery_stats["circuit_breaker_status"].values()
            if cb["state"] == "open"
        ])
        
        # Determine overall health status
        status = "healthy"
        recommendations = []
        
        if recovery_rate < 0.5:
            status = "critical"
            recommendations.append("Recovery rate is critically low - investigate failing tools")
        elif recovery_rate < 0.8:
            status = "degraded"
            recommendations.append("Recovery rate is below optimal - monitor tool performance")
        
        if circuit_breakers_open > 3:
            status = "critical" if status != "critical" else status
            recommendations.append(f"{circuit_breakers_open} circuit breakers are open - check tool connectivity")
        elif circuit_breakers_open > 0:
            recommendations.append(f"{circuit_breakers_open} circuit breaker(s) active - monitor affected tools")
        
        # Error trend analysis
        error_trends = self._analyze_error_trends(recovery_stats)
        if error_trends.get("increasing_failures", False):
            if status == "healthy":
                status = "degraded"
            recommendations.append("Error rate is increasing - investigate root causes")
        
        # Add general recommendations
        if not recommendations:
            recommendations.append("System is operating normally")
        
        return SystemHealthStatus(
            status=status,
            recovery_rate=recovery_rate,
            circuit_breakers_open=circuit_breakers_open,
            total_tools=len(parameter_validator.tool_specs),
            error_trends=error_trends,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )
    
    def get_tool_performance_report(self, top_n: int = 10) -> Dict[str, Any]:
        """Get detailed performance report for top failing tools."""
        recovery_stats = get_recovery_statistics()
        
        # Analyze circuit breaker data for tool performance
        tool_performance = []
        
        for tool_name, cb_data in recovery_stats["circuit_breaker_status"].items():
            failure_count = cb_data["failure_count"]
            state = cb_data["state"]
            
            performance_data = {
                "tool_name": tool_name,
                "failure_count": failure_count,
                "circuit_state": state,
                "last_failure": cb_data["last_failure"],
                "reliability_score": self._calculate_reliability_score(failure_count, state)
            }
            
            tool_performance.append(performance_data)
        
        # Sort by failure count (worst first)
        tool_performance.sort(key=lambda x: x["failure_count"], reverse=True)
        
        return {
            "top_failing_tools": tool_performance[:top_n],
            "total_tools_monitored": len(tool_performance),
            "tools_with_failures": len([t for t in tool_performance if t["failure_count"] > 0]),
            "tools_with_open_circuits": len([t for t in tool_performance if t["circuit_state"] == "open"]),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def get_recovery_strategy_effectiveness(self) -> Dict[str, Any]:
        """Analyze effectiveness of different recovery strategies."""
        # This would require tracking strategy success rates
        # For now, return basic strategy information
        
        return {
            "strategy_overview": {
                "retry": "Handles transient network and timeout errors",
                "fallback": "Uses alternative tools when primary tools fail",
                "parameter_correction": "Fixes common parameter validation issues",
                "graceful_degradation": "Provides helpful error responses when recovery fails"
            },
            "strategy_metrics": {
                "fallback_success_rate": "Tracked in recovery statistics",
                "parameter_correction_success_rate": "Tracked in recovery statistics",
                "retry_success_rate": "Varies by error type"
            },
            "recommendations": [
                "Monitor fallback tool reliability",
                "Keep parameter validation rules up to date",
                "Review retry thresholds for optimal performance"
            ]
        }
    
    def _analyze_tool_reliability(self, recovery_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze tool reliability based on circuit breaker data."""
        cb_status = recovery_stats["circuit_breaker_status"]
        
        if not cb_status:
            return {"status": "no_data", "message": "No circuit breaker data available"}
        
        # Categorize tools by reliability
        highly_reliable = []  # No failures
        moderately_reliable = []  # Some failures, circuit closed
        problematic = []  # High failures or open circuit
        
        for tool, data in cb_status.items():
            failure_count = data["failure_count"]
            state = data["state"]
            
            if failure_count == 0:
                highly_reliable.append(tool)
            elif failure_count < 5 and state == "closed":
                moderately_reliable.append(tool)
            else:
                problematic.append(tool)
        
        return {
            "highly_reliable_tools": len(highly_reliable),
            "moderately_reliable_tools": len(moderately_reliable),
            "problematic_tools": len(problematic),
            "problematic_tool_list": problematic[:10],  # Top 10 most problematic
            "reliability_distribution": {
                "high": len(highly_reliable),
                "moderate": len(moderately_reliable),
                "low": len(problematic)
            }
        }
    
    def _analyze_error_patterns(self, recovery_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze common error patterns."""
        error_history = recovery_stats.get("error_history", {})
        
        if not error_history:
            return {"status": "no_data", "message": "No error history available"}
        
        # Count total errors by tool
        total_errors = sum(error_history.values())
        
        # Identify most error-prone tools
        if error_history:
            most_errors_tool = max(error_history.items(), key=lambda x: x[1])
        else:
            most_errors_tool = ("none", 0)
        
        return {
            "total_recent_errors": total_errors,
            "tools_with_errors": len(error_history),
            "most_error_prone_tool": {
                "name": most_errors_tool[0],
                "error_count": most_errors_tool[1]
            },
            "error_distribution": dict(sorted(error_history.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    def _analyze_error_trends(self, recovery_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error trends over time."""
        # Simple trend analysis based on available data
        error_history = recovery_stats.get("error_history", {})
        total_recent_errors = sum(error_history.values())
        
        # Basic trend indicators
        return {
            "total_recent_errors": total_recent_errors,
            "increasing_failures": total_recent_errors > 10,  # Simple threshold
            "error_concentration": len([t for t in error_history.values() if t > 3]),
            "trend_analysis": "Basic trend analysis - enhanced monitoring needed for detailed trends"
        }
    
    def _calculate_reliability_score(self, failure_count: int, circuit_state: str) -> float:
        """Calculate a reliability score for a tool."""
        base_score = 100.0
        
        # Deduct points for failures
        failure_penalty = min(failure_count * 10, 80)  # Max 80 point deduction
        
        # Additional penalty for open circuit
        circuit_penalty = 20 if circuit_state == "open" else 0
        
        # Half penalty for half-open
        if circuit_state == "half_open":
            circuit_penalty = 10
        
        score = base_score - failure_penalty - circuit_penalty
        return max(score, 0.0)
    
    def generate_health_report(self) -> str:
        """Generate a human-readable health report."""
        health = self.get_system_health()
        stats = self.get_comprehensive_statistics()
        
        report = f"""
NetBox MCP Error Recovery System Health Report
Generated: {health.timestamp}

OVERALL STATUS: {health.status.upper()}
Recovery Rate: {health.recovery_rate:.1%}
Active Circuit Breakers: {health.circuit_breakers_open}

RECOVERY STATISTICS:
- Total Errors Handled: {stats['overview']['total_errors_handled']}
- Successful Recoveries: {stats['overview']['successful_recoveries']}
- Fallback Successes: {stats['overview']['fallback_successes']}
- Parameter Corrections: {stats['overview']['parameter_corrections']}

TOOL CONFIGURATION:
- Total Tools Configured: {stats['parameter_validation']['total_tools_configured']}
- Parameter Specifications: {stats['parameter_validation']['parameter_specs_count']}
- Global Aliases: {stats['parameter_validation']['global_aliases_count']}

RECOMMENDATIONS:
"""
        for rec in health.recommendations:
            report += f"- {rec}\n"
        
        return report.strip()


# Global monitor instance
recovery_monitor = RecoveryMonitor()


def get_system_health() -> SystemHealthStatus:
    """Get current system health status."""
    return recovery_monitor.get_system_health()


def get_recovery_statistics() -> Dict[str, Any]:
    """Get comprehensive recovery statistics."""
    return recovery_monitor.get_comprehensive_statistics()


def get_tool_performance_report(top_n: int = 10) -> Dict[str, Any]:
    """Get tool performance report."""
    return recovery_monitor.get_tool_performance_report(top_n)


def generate_health_report() -> str:
    """Generate human-readable health report."""
    return recovery_monitor.generate_health_report()
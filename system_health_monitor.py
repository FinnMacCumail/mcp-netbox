#!/usr/bin/env python3
"""
System Health Monitor
Real-time monitoring and health assessment for NetBox MCP production system

This module provides comprehensive monitoring of the NetBox MCP system components
including performance metrics, error rates, resource usage, and overall health
assessment for production deployment and ongoing operations.
"""

import asyncio
import sys
import os
import json
import time
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import traceback
import argparse
from collections import defaultdict, deque

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


@dataclass
class ComponentHealth:
    """Health status of a system component"""
    name: str
    status: str  # "healthy", "degraded", "critical", "offline"
    last_check: datetime
    response_time_ms: Optional[float] = None
    error_rate: Optional[float] = None
    resource_usage: Optional[Dict[str, float]] = None
    details: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None


@dataclass
class SystemMetrics:
    """System-wide metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Dict[str, int]
    process_count: int
    active_connections: int
    response_times: Dict[str, float]
    error_rates: Dict[str, float]
    cache_hit_rates: Dict[str, float]


@dataclass
class HealthAlert:
    """Health alert for issues requiring attention"""
    severity: str  # "info", "warning", "critical"
    component: str
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    resolved: bool = False


class SystemHealthMonitor:
    """Real-time system health monitoring"""
    
    def __init__(self, monitoring_interval: float = 30.0):
        self.logger = logging.getLogger(__name__)
        self.monitoring_interval = monitoring_interval
        self.monitoring_active = False
        
        # Health tracking
        self.component_health: Dict[str, ComponentHealth] = {}
        self.metrics_history: deque = deque(maxlen=100)  # Last 100 metrics
        self.alerts: List[HealthAlert] = []
        
        # Performance thresholds
        self.thresholds = {
            "cpu_percent": {"warning": 70, "critical": 90},
            "memory_percent": {"warning": 80, "critical": 95},
            "disk_usage_percent": {"warning": 85, "critical": 95},
            "response_time_ms": {"warning": 2000, "critical": 5000},
            "error_rate": {"warning": 0.05, "critical": 0.1},
            "cache_hit_rate": {"warning": 0.7, "critical": 0.5}
        }
        
        # Component monitors
        self.component_monitors = {}
        
    async def initialize(self) -> bool:
        """Initialize the health monitoring system"""
        try:
            print("🏥 Initializing System Health Monitor...")
            print("=" * 60)
            
            # Initialize component monitors
            await self._initialize_component_monitors()
            
            # Perform initial health check
            await self._perform_initial_health_check()
            
            print("✅ System Health Monitor initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize health monitor: {e}")
            self.logger.exception("Initialization error:")
            return False
    
    async def _initialize_component_monitors(self):
        """Initialize monitors for each system component"""
        components = {
            'system_resources': self._monitor_system_resources,
            'query_processor': self._monitor_query_processor,
            'tool_coordination': self._monitor_tool_coordination,
            'cache_system': self._monitor_cache_system,
            'performance_monitor': self._monitor_performance_system,
            'error_recovery': self._monitor_error_recovery,
            'conversation_manager': self._monitor_conversation_manager
        }
        
        for name, monitor_func in components.items():
            self.component_monitors[name] = monitor_func
            print(f"  📊 {name.replace('_', ' ').title()}: Monitor configured")
    
    async def _perform_initial_health_check(self):
        """Perform initial health check of all components"""
        print("🔍 Performing initial health assessment...")
        
        for component_name, monitor_func in self.component_monitors.items():
            try:
                health = await monitor_func()
                self.component_health[component_name] = health
                
                status_emoji = {
                    "healthy": "✅",
                    "degraded": "⚠️",
                    "critical": "❌",
                    "offline": "🔴"
                }.get(health.status, "❓")
                
                print(f"  {status_emoji} {health.name}: {health.status}")
                
                if health.status in ["critical", "offline"]:
                    self._create_alert("critical", component_name, 
                                     f"{health.name} is {health.status}")
                elif health.status == "degraded":
                    self._create_alert("warning", component_name,
                                     f"{health.name} performance degraded")
                
            except Exception as e:
                print(f"  ❌ {component_name}: Health check failed - {e}")
                self._create_alert("critical", component_name,
                                 f"Health check failed: {str(e)}")
    
    async def start_monitoring(self):
        """Start continuous monitoring"""
        print(f"🚀 Starting continuous health monitoring (interval: {self.monitoring_interval}s)")
        
        self.monitoring_active = True
        
        try:
            while self.monitoring_active:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Update component health
                await self._update_component_health()
                
                # Check for alerts
                await self._check_alert_conditions()
                
                # Sleep until next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
        except asyncio.CancelledError:
            print("⏹️ Monitoring stopped by cancellation")
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
            self.logger.exception("Monitoring error:")
        finally:
            self.monitoring_active = False
    
    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        print("⏹️ Stopping health monitoring...")
        self.monitoring_active = False
    
    async def _collect_system_metrics(self):
        """Collect comprehensive system metrics"""
        try:
            # System resource metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Process metrics
            current_process = psutil.Process()
            process_count = len(psutil.pids())
            
            # Network connections
            connections = len(psutil.net_connections())
            
            # Create metrics object
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_io={
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                process_count=process_count,
                active_connections=connections,
                response_times={},  # Will be populated by component monitors
                error_rates={},     # Will be populated by component monitors
                cache_hit_rates={}  # Will be populated by component monitors
            )
            
            self.metrics_history.append(metrics)
            
        except Exception as e:
            self.logger.exception("Error collecting system metrics:")
    
    async def _update_component_health(self):
        """Update health status of all components"""
        for component_name, monitor_func in self.component_monitors.items():
            try:
                health = await monitor_func()
                self.component_health[component_name] = health
                
            except Exception as e:
                # Component health check failed
                self.component_health[component_name] = ComponentHealth(
                    name=component_name.replace('_', ' ').title(),
                    status="critical",
                    last_check=datetime.now(),
                    details={"error": str(e)},
                    recommendations=["Check component availability", "Review error logs"]
                )
    
    async def _check_alert_conditions(self):
        """Check for conditions that should trigger alerts"""
        if not self.metrics_history:
            return
        
        latest_metrics = self.metrics_history[-1]
        
        # Check system resource thresholds
        self._check_threshold_alert("cpu_percent", latest_metrics.cpu_percent, "System CPU")
        self._check_threshold_alert("memory_percent", latest_metrics.memory_percent, "System Memory")
        self._check_threshold_alert("disk_usage_percent", latest_metrics.disk_usage_percent, "System Disk")
        
        # Check component health for alerts
        for component_name, health in self.component_health.items():
            if health.status == "critical":
                self._create_alert("critical", component_name, f"{health.name} is critical")
            elif health.status == "degraded":
                self._create_alert("warning", component_name, f"{health.name} performance degraded")
    
    def _check_threshold_alert(self, metric_name: str, value: float, display_name: str):
        """Check if a metric value exceeds alert thresholds"""
        thresholds = self.thresholds.get(metric_name, {})
        
        if value >= thresholds.get("critical", float('inf')):
            self._create_alert("critical", "system", 
                             f"{display_name} critical: {value:.1f}%")
        elif value >= thresholds.get("warning", float('inf')):
            self._create_alert("warning", "system",
                             f"{display_name} warning: {value:.1f}%")
    
    def _create_alert(self, severity: str, component: str, message: str, details: Optional[Dict] = None):
        """Create a new health alert"""
        # Check if similar alert already exists and is recent
        recent_alerts = [
            a for a in self.alerts
            if a.component == component and a.message == message
            and (datetime.now() - a.timestamp).seconds < 300  # 5 minutes
            and not a.resolved
        ]
        
        if recent_alerts:
            return  # Don't duplicate recent alerts
        
        alert = HealthAlert(
            severity=severity,
            component=component,
            message=message,
            timestamp=datetime.now(),
            details=details
        )
        
        self.alerts.append(alert)
    
    # Component-specific monitoring functions
    async def _monitor_system_resources(self) -> ComponentHealth:
        """Monitor system resources (CPU, Memory, Disk)"""
        try:
            # Get current system metrics
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine overall status
            critical_conditions = [
                cpu_percent >= self.thresholds["cpu_percent"]["critical"],
                memory.percent >= self.thresholds["memory_percent"]["critical"],
                disk.percent >= self.thresholds["disk_usage_percent"]["critical"]
            ]
            
            warning_conditions = [
                cpu_percent >= self.thresholds["cpu_percent"]["warning"],
                memory.percent >= self.thresholds["memory_percent"]["warning"],
                disk.percent >= self.thresholds["disk_usage_percent"]["warning"]
            ]
            
            if any(critical_conditions):
                status = "critical"
            elif any(warning_conditions):
                status = "degraded"
            else:
                status = "healthy"
            
            return ComponentHealth(
                name="System Resources",
                status=status,
                last_check=datetime.now(),
                resource_usage={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent
                },
                details={
                    "cpu_cores": psutil.cpu_count(),
                    "memory_total_gb": memory.total / (1024**3),
                    "disk_total_gb": disk.total / (1024**3)
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="System Resources",
                status="critical",
                last_check=datetime.now(),
                details={"error": str(e)}
            )
    
    async def _monitor_query_processor(self) -> ComponentHealth:
        """Monitor query processing system"""
        try:
            # Try to import and test query processor
            start_time = time.time()
            
            try:
                from netbox_mcp.orchestration.state_machine import QueryProcessor
                processor = QueryProcessor()
                # Test basic functionality
                response_time_ms = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="Query Processor",
                    status="healthy",
                    last_check=datetime.now(),
                    response_time_ms=response_time_ms,
                    details={
                        "import_successful": True,
                        "initialization_time_ms": response_time_ms
                    }
                )
                
            except ImportError:
                return ComponentHealth(
                    name="Query Processor",
                    status="offline",
                    last_check=datetime.now(),
                    details={"error": "Query processor module not available"}
                )
                
        except Exception as e:
            return ComponentHealth(
                name="Query Processor",
                status="critical",
                last_check=datetime.now(),
                details={"error": str(e)}
            )
    
    async def _monitor_tool_coordination(self) -> ComponentHealth:
        """Monitor tool coordination system"""
        try:
            start_time = time.time()
            
            try:
                from netbox_mcp.orchestration.coordination import ToolCoordinator
                coordinator = ToolCoordinator()
                response_time_ms = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="Tool Coordination",
                    status="healthy",
                    last_check=datetime.now(),
                    response_time_ms=response_time_ms,
                    details={
                        "import_successful": True,
                        "initialization_time_ms": response_time_ms
                    }
                )
                
            except ImportError:
                return ComponentHealth(
                    name="Tool Coordination",
                    status="degraded",
                    last_check=datetime.now(),
                    details={"error": "Tool coordination module not available"}
                )
                
        except Exception as e:
            return ComponentHealth(
                name="Tool Coordination",
                status="critical",
                last_check=datetime.now(),
                details={"error": str(e)}
            )
    
    async def _monitor_cache_system(self) -> ComponentHealth:
        """Monitor cache system"""
        try:
            start_time = time.time()
            
            try:
                from netbox_mcp.orchestration.cache import OrchestrationCache
                cache = OrchestrationCache()
                
                # Test cache connectivity
                cache_available = await cache.initialize()
                response_time_ms = (time.time() - start_time) * 1000
                
                if cache_available:
                    status = "healthy"
                    details = {
                        "cache_available": True,
                        "connection_time_ms": response_time_ms
                    }
                else:
                    status = "degraded"
                    details = {
                        "cache_available": False,
                        "fallback_mode": True
                    }
                
                return ComponentHealth(
                    name="Cache System",
                    status=status,
                    last_check=datetime.now(),
                    response_time_ms=response_time_ms,
                    details=details
                )
                
            except ImportError:
                return ComponentHealth(
                    name="Cache System",
                    status="degraded",
                    last_check=datetime.now(),
                    details={"error": "Cache module not available"}
                )
                
        except Exception as e:
            return ComponentHealth(
                name="Cache System",
                status="critical",
                last_check=datetime.now(),
                details={"error": str(e)}
            )
    
    async def _monitor_performance_system(self) -> ComponentHealth:
        """Monitor performance monitoring system"""
        try:
            start_time = time.time()
            
            try:
                from netbox_mcp.orchestration.performance_monitor import PerformanceMonitor
                monitor = PerformanceMonitor()
                response_time_ms = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="Performance Monitor",
                    status="healthy",
                    last_check=datetime.now(),
                    response_time_ms=response_time_ms,
                    details={
                        "monitoring_available": True,
                        "initialization_time_ms": response_time_ms
                    }
                )
                
            except ImportError:
                return ComponentHealth(
                    name="Performance Monitor",
                    status="degraded",
                    last_check=datetime.now(),
                    details={"error": "Performance monitoring not available"}
                )
                
        except Exception as e:
            return ComponentHealth(
                name="Performance Monitor",
                status="critical",
                last_check=datetime.now(),
                details={"error": str(e)}
            )
    
    async def _monitor_error_recovery(self) -> ComponentHealth:
        """Monitor error recovery system"""
        try:
            start_time = time.time()
            
            try:
                from netbox_mcp.orchestration.error_recovery import ErrorRecoverySystem
                recovery = ErrorRecoverySystem()
                response_time_ms = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="Error Recovery",
                    status="healthy",
                    last_check=datetime.now(),
                    response_time_ms=response_time_ms,
                    details={
                        "recovery_available": True,
                        "initialization_time_ms": response_time_ms
                    }
                )
                
            except ImportError:
                return ComponentHealth(
                    name="Error Recovery",
                    status="degraded",
                    last_check=datetime.now(),
                    details={"error": "Error recovery system not available"}
                )
                
        except Exception as e:
            return ComponentHealth(
                name="Error Recovery",
                status="critical",
                last_check=datetime.now(),
                details={"error": str(e)}
            )
    
    async def _monitor_conversation_manager(self) -> ComponentHealth:
        """Monitor conversation management system"""
        try:
            start_time = time.time()
            
            try:
                from netbox_mcp.agents.conversation_manager import ConversationManager
                manager = ConversationManager()
                response_time_ms = (time.time() - start_time) * 1000
                
                return ComponentHealth(
                    name="Conversation Manager",
                    status="healthy",
                    last_check=datetime.now(),
                    response_time_ms=response_time_ms,
                    details={
                        "manager_available": True,
                        "initialization_time_ms": response_time_ms
                    }
                )
                
            except ImportError:
                return ComponentHealth(
                    name="Conversation Manager",
                    status="degraded",
                    last_check=datetime.now(),
                    details={"error": "Conversation manager not available"}
                )
                
        except Exception as e:
            return ComponentHealth(
                name="Conversation Manager",
                status="critical",
                last_check=datetime.now(),
                details={"error": str(e)}
            )
    
    def get_system_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive system health report"""
        # Overall system status
        component_statuses = [health.status for health in self.component_health.values()]
        
        if "critical" in component_statuses or "offline" in component_statuses:
            overall_status = "critical"
        elif "degraded" in component_statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        # Recent metrics
        recent_metrics = list(self.metrics_history)[-10:] if self.metrics_history else []
        
        # Active alerts
        active_alerts = [a for a in self.alerts if not a.resolved]
        critical_alerts = [a for a in active_alerts if a.severity == "critical"]
        warning_alerts = [a for a in active_alerts if a.severity == "warning"]
        
        # Performance summary
        if recent_metrics:
            latest = recent_metrics[-1]
            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        else:
            latest = None
            avg_cpu = 0
            avg_memory = 0
        
        # Component health summary
        component_summary = {}
        for name, health in self.component_health.items():
            component_summary[name] = {
                "status": health.status,
                "last_check": health.last_check.isoformat(),
                "response_time_ms": health.response_time_ms,
                "error_rate": health.error_rate
            }
        
        return {
            "system_status": {
                "overall_status": overall_status,
                "timestamp": datetime.now().isoformat(),
                "monitoring_active": self.monitoring_active,
                "uptime_seconds": time.time()  # Simplified uptime
            },
            "component_health": component_summary,
            "performance_metrics": {
                "current_cpu_percent": latest.cpu_percent if latest else None,
                "current_memory_percent": latest.memory_percent if latest else None,
                "current_disk_percent": latest.disk_usage_percent if latest else None,
                "avg_cpu_percent": avg_cpu,
                "avg_memory_percent": avg_memory,
                "active_connections": latest.active_connections if latest else None
            },
            "alerts": {
                "total_active_alerts": len(active_alerts),
                "critical_alerts": len(critical_alerts),
                "warning_alerts": len(warning_alerts),
                "recent_alerts": [
                    {
                        "severity": a.severity,
                        "component": a.component,
                        "message": a.message,
                        "timestamp": a.timestamp.isoformat()
                    }
                    for a in active_alerts[-10:]  # Last 10 alerts
                ]
            },
            "recommendations": self._generate_health_recommendations()
        }
    
    def _generate_health_recommendations(self) -> List[str]:
        """Generate health recommendations based on current status"""
        recommendations = []
        
        # Check component health
        critical_components = [
            name for name, health in self.component_health.items()
            if health.status in ["critical", "offline"]
        ]
        
        degraded_components = [
            name for name, health in self.component_health.items()
            if health.status == "degraded"
        ]
        
        if critical_components:
            recommendations.append(f"CRITICAL: Address issues with {', '.join(critical_components)}")
        
        if degraded_components:
            recommendations.append(f"WARNING: Review degraded components: {', '.join(degraded_components)}")
        
        # Check recent metrics
        if self.metrics_history:
            latest = self.metrics_history[-1]
            
            if latest.cpu_percent > 80:
                recommendations.append("High CPU usage detected - consider scaling or optimization")
            
            if latest.memory_percent > 85:
                recommendations.append("High memory usage detected - monitor for memory leaks")
            
            if latest.disk_usage_percent > 90:
                recommendations.append("Low disk space - consider cleanup or expansion")
        
        # Check alerts
        active_critical_alerts = [
            a for a in self.alerts
            if a.severity == "critical" and not a.resolved
        ]
        
        if active_critical_alerts:
            recommendations.append(f"Resolve {len(active_critical_alerts)} critical alerts immediately")
        
        if not recommendations:
            recommendations.append("System appears healthy - continue monitoring")
        
        return recommendations


async def run_health_check():
    """Run a one-time comprehensive health check"""
    monitor = SystemHealthMonitor()
    
    if not await monitor.initialize():
        return {"error": "Failed to initialize health monitor"}
    
    # Get health report
    report = monitor.get_system_health_report()
    
    return report


async def run_continuous_monitoring(duration_minutes: int = 60):
    """Run continuous monitoring for specified duration"""
    monitor = SystemHealthMonitor(monitoring_interval=30.0)
    
    if not await monitor.initialize():
        print("❌ Failed to initialize monitoring")
        return 1
    
    print(f"🔄 Starting continuous monitoring for {duration_minutes} minutes...")
    
    # Start monitoring task
    monitor_task = asyncio.create_task(monitor.start_monitoring())
    
    # Run for specified duration
    await asyncio.sleep(duration_minutes * 60)
    
    # Stop monitoring
    await monitor.stop_monitoring()
    monitor_task.cancel()
    
    # Generate final report
    final_report = monitor.get_system_health_report()
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"health_monitoring_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(final_report, f, indent=2)
    
    print(f"📄 Health monitoring report saved to: {report_file}")
    
    return 0


async def main():
    """Main health monitoring entry point"""
    parser = argparse.ArgumentParser(
        description="NetBox MCP System Health Monitor"
    )
    
    parser.add_argument(
        "--mode",
        choices=["check", "monitor"],
        default="check",
        help="Mode: 'check' for one-time health check, 'monitor' for continuous monitoring"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration for continuous monitoring in minutes (default: 60)"
    )
    
    parser.add_argument(
        "--output",
        default="system_health_report.json",
        help="Output file for health report"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    print("🏥 NetBox MCP System Health Monitor")
    print("=" * 50)
    
    if args.mode == "check":
        # One-time health check
        print("🔍 Performing comprehensive health check...")
        
        report = await run_health_check()
        
        if "error" in report:
            print(f"❌ Health check failed: {report['error']}")
            return 1
        
        # Save report
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Display summary
        status = report['system_status']['overall_status']
        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️", 
            "critical": "❌"
        }.get(status, "❓")
        
        print(f"\n{status_emoji} Overall System Status: {status.upper()}")
        
        print(f"\n📊 Component Status:")
        for component, health in report['component_health'].items():
            comp_status = health['status']
            comp_emoji = {
                "healthy": "✅",
                "degraded": "⚠️",
                "critical": "❌",
                "offline": "🔴"
            }.get(comp_status, "❓")
            print(f"  {comp_emoji} {component.replace('_', ' ').title()}: {comp_status}")
        
        alerts = report['alerts']
        if alerts['total_active_alerts'] > 0:
            print(f"\n🚨 Active Alerts: {alerts['total_active_alerts']}")
            print(f"   Critical: {alerts['critical_alerts']}")
            print(f"   Warnings: {alerts['warning_alerts']}")
        
        print(f"\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        print(f"\n📄 Detailed report saved to: {args.output}")
        
        return 0 if status != "critical" else 1
        
    elif args.mode == "monitor":
        # Continuous monitoring
        return await run_continuous_monitoring(args.duration)


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Monitoring interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
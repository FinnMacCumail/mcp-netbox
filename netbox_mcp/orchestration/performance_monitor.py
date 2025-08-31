"""
PerformanceMonitor for Real NetBox API Performance Tracking
Week 9-12: Real NetBox Integration & Advanced Conversation Management

This module provides comprehensive performance monitoring, metrics collection,
and analysis for real NetBox MCP tool execution and API performance tracking.
"""

import asyncio
import logging
import time
import psutil
import threading
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    EXECUTION_TIME = "execution_time"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    RESOURCE_USAGE = "resource_usage"
    RETRY_COUNT = "retry_count"


class PerformanceLevel(Enum):
    """Performance level classifications"""
    EXCELLENT = "excellent"    # < 1s response, >95% success
    GOOD = "good"             # < 3s response, >90% success
    ACCEPTABLE = "acceptable"  # < 5s response, >85% success
    POOR = "poor"             # < 10s response, >70% success
    CRITICAL = "critical"     # >10s response or <70% success


@dataclass
class PerformanceMetric:
    """Individual performance metric data point"""
    timestamp: datetime
    metric_type: MetricType
    tool_name: str
    value: float
    context: Dict[str, Any] = field(default_factory=dict)
    
    def age_minutes(self) -> float:
        """Get age of metric in minutes"""
        return (datetime.now() - self.timestamp).total_seconds() / 60


@dataclass
class ToolPerformanceProfile:
    """Performance profile for a specific NetBox tool"""
    tool_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    retry_count: int = 0
    error_patterns: Dict[str, int] = field(default_factory=dict)
    last_execution: Optional[datetime] = None
    performance_level: PerformanceLevel = PerformanceLevel.ACCEPTABLE
    
    def update_execution(self, execution_time: float, success: bool, cached: bool = False, error_type: Optional[str] = None):
        """Update performance profile with new execution data"""
        self.total_executions += 1
        self.last_execution = datetime.now()
        
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
            if error_type:
                self.error_patterns[error_type] = self.error_patterns.get(error_type, 0) + 1
        
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        # Update timing statistics
        self.total_execution_time += execution_time
        self.min_execution_time = min(self.min_execution_time, execution_time)
        self.max_execution_time = max(self.max_execution_time, execution_time)
        self.avg_execution_time = self.total_execution_time / self.total_executions
        
        # Update performance level
        self._calculate_performance_level()
    
    def _calculate_performance_level(self):
        """Calculate current performance level based on metrics"""
        if self.total_executions == 0:
            self.performance_level = PerformanceLevel.ACCEPTABLE
            return
        
        success_rate = self.successful_executions / self.total_executions
        avg_time = self.avg_execution_time
        
        if avg_time < 1.0 and success_rate > 0.95:
            self.performance_level = PerformanceLevel.EXCELLENT
        elif avg_time < 3.0 and success_rate > 0.90:
            self.performance_level = PerformanceLevel.GOOD
        elif avg_time < 5.0 and success_rate > 0.85:
            self.performance_level = PerformanceLevel.ACCEPTABLE
        elif avg_time < 10.0 and success_rate > 0.70:
            self.performance_level = PerformanceLevel.POOR
        else:
            self.performance_level = PerformanceLevel.CRITICAL
    
    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate percentage"""
        total_cache_attempts = self.cache_hits + self.cache_misses
        return (self.cache_hits / total_cache_attempts * 100) if total_cache_attempts > 0 else 0.0
    
    def get_success_rate(self) -> float:
        """Get success rate percentage"""
        return (self.successful_executions / self.total_executions * 100) if self.total_executions > 0 else 0.0


class PerformanceMonitor:
    """
    Comprehensive performance monitor for NetBox MCP tool execution.
    
    Tracks real-time performance metrics, analyzes trends, identifies bottlenecks,
    and provides optimization recommendations for NetBox API interactions.
    """
    
    def __init__(self, max_metrics_age_hours: int = 24, sampling_interval_seconds: int = 30):
        self.logger = logging.getLogger(__name__)
        self.max_metrics_age_hours = max_metrics_age_hours
        self.sampling_interval_seconds = sampling_interval_seconds
        
        # Metrics storage
        self.metrics: deque = deque()                            # Time-series metrics
        self.tool_profiles: Dict[str, ToolPerformanceProfile] = {}  # Per-tool performance profiles
        self.system_metrics: deque = deque()                    # System resource metrics
        
        # Real-time tracking
        self.active_executions: Dict[str, datetime] = {}        # Currently executing tools
        self.recent_errors: deque = deque(maxlen=100)           # Recent error tracking
        self.performance_alerts: List[Dict[str, Any]] = []      # Performance alerts
        
        # Trend analysis
        self.trend_window_minutes = 15                          # Window for trend analysis
        self.performance_thresholds = {
            "execution_time_warning": 5.0,                     # seconds
            "execution_time_critical": 10.0,                   # seconds
            "success_rate_warning": 0.90,                      # 90%
            "success_rate_critical": 0.70,                     # 70%
            "cache_hit_rate_warning": 0.60,                    # 60%
            "cache_hit_rate_critical": 0.30                    # 30%
        }
        
        # Background monitoring
        self._monitoring_active = False
        self._monitoring_task = None
        
        # Statistics
        self.monitoring_stats = {
            "total_metrics_collected": 0,
            "performance_alerts_generated": 0,
            "tools_monitored": 0,
            "monitoring_start_time": datetime.now(),
            "last_cleanup_time": datetime.now()
        }
    
    async def start_monitoring(self):
        """Start background performance monitoring"""
        if self._monitoring_active:
            self.logger.warning("Performance monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop background performance monitoring"""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Performance monitoring stopped")
    
    def record_tool_execution(
        self,
        tool_name: str,
        execution_time: float,
        success: bool,
        cached: bool = False,
        error_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Record a tool execution for performance tracking"""
        
        # Update tool profile
        if tool_name not in self.tool_profiles:
            self.tool_profiles[tool_name] = ToolPerformanceProfile(tool_name)
            self.monitoring_stats["tools_monitored"] += 1
        
        profile = self.tool_profiles[tool_name]
        profile.update_execution(execution_time, success, cached, error_type)
        
        # Record metrics
        timestamp = datetime.now()
        
        # Execution time metric
        self._add_metric(MetricType.EXECUTION_TIME, tool_name, execution_time, context or {})
        
        # Success/failure metric
        success_value = 1.0 if success else 0.0
        self._add_metric(MetricType.SUCCESS_RATE, tool_name, success_value, context or {})
        
        # Cache hit metric
        if cached:
            self._add_metric(MetricType.CACHE_HIT_RATE, tool_name, 1.0, context or {})
        else:
            self._add_metric(MetricType.CACHE_HIT_RATE, tool_name, 0.0, context or {})
        
        # Track errors
        if not success and error_type:
            self.recent_errors.append({
                "timestamp": timestamp,
                "tool_name": tool_name,
                "error_type": error_type,
                "execution_time": execution_time,
                "context": context or {}
            })
        
        # Check for performance alerts
        self._check_performance_alerts(tool_name, profile)
        
        self.monitoring_stats["total_metrics_collected"] += 1
    
    def start_tool_execution(self, tool_name: str, execution_id: str):
        """Mark the start of a tool execution for latency tracking"""
        self.active_executions[execution_id] = datetime.now()
    
    def end_tool_execution(self, execution_id: str) -> Optional[float]:
        """Mark the end of a tool execution and return execution time"""
        if execution_id in self.active_executions:
            start_time = self.active_executions.pop(execution_id)
            execution_time = (datetime.now() - start_time).total_seconds()
            return execution_time
        return None
    
    def get_tool_performance_summary(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive performance summary for a specific tool"""
        if tool_name not in self.tool_profiles:
            return None
        
        profile = self.tool_profiles[tool_name]
        
        return {
            "tool_name": tool_name,
            "performance_level": profile.performance_level.value,
            "execution_stats": {
                "total_executions": profile.total_executions,
                "successful_executions": profile.successful_executions,
                "failed_executions": profile.failed_executions,
                "success_rate": profile.get_success_rate(),
                "retry_count": profile.retry_count
            },
            "timing_stats": {
                "avg_execution_time": profile.avg_execution_time,
                "min_execution_time": profile.min_execution_time if profile.min_execution_time != float('inf') else 0,
                "max_execution_time": profile.max_execution_time,
                "total_execution_time": profile.total_execution_time
            },
            "cache_stats": {
                "cache_hits": profile.cache_hits,
                "cache_misses": profile.cache_misses,
                "cache_hit_rate": profile.get_cache_hit_rate()
            },
            "error_analysis": {
                "error_patterns": dict(profile.error_patterns),
                "most_common_error": max(profile.error_patterns.keys(), key=profile.error_patterns.get) if profile.error_patterns else None
            },
            "last_execution": profile.last_execution.isoformat() if profile.last_execution else None
        }
    
    def get_overall_performance_summary(self) -> Dict[str, Any]:
        """Get overall system performance summary"""
        if not self.tool_profiles:
            return {"error": "No performance data available"}
        
        # Aggregate statistics
        total_executions = sum(p.total_executions for p in self.tool_profiles.values())
        total_successful = sum(p.successful_executions for p in self.tool_profiles.values())
        total_failed = sum(p.failed_executions for p in self.tool_profiles.values())
        total_cache_hits = sum(p.cache_hits for p in self.tool_profiles.values())
        total_cache_attempts = sum(p.cache_hits + p.cache_misses for p in self.tool_profiles.values())
        
        # Average execution times
        avg_execution_times = [p.avg_execution_time for p in self.tool_profiles.values() if p.total_executions > 0]
        overall_avg_time = statistics.mean(avg_execution_times) if avg_execution_times else 0.0
        
        # Performance level distribution
        performance_levels = defaultdict(int)
        for profile in self.tool_profiles.values():
            performance_levels[profile.performance_level.value] += 1
        
        # Recent trends (last 15 minutes)
        recent_metrics = self._get_recent_metrics(self.trend_window_minutes)
        trend_analysis = self._analyze_trends(recent_metrics)
        
        return {
            "monitoring_period": {
                "start_time": self.monitoring_stats["monitoring_start_time"].isoformat(),
                "duration_hours": (datetime.now() - self.monitoring_stats["monitoring_start_time"]).total_seconds() / 3600
            },
            "overall_stats": {
                "total_executions": total_executions,
                "overall_success_rate": (total_successful / total_executions * 100) if total_executions > 0 else 0,
                "overall_failure_rate": (total_failed / total_executions * 100) if total_executions > 0 else 0,
                "overall_cache_hit_rate": (total_cache_hits / total_cache_attempts * 100) if total_cache_attempts > 0 else 0,
                "average_execution_time": overall_avg_time,
                "tools_monitored": len(self.tool_profiles)
            },
            "performance_distribution": dict(performance_levels),
            "trend_analysis": trend_analysis,
            "top_performers": self._get_top_performing_tools(5),
            "bottlenecks": self._identify_bottlenecks(),
            "recent_alerts": self.performance_alerts[-10:],  # Last 10 alerts
            "system_health": self._get_system_health_summary(),
            "monitoring_stats": self.monitoring_stats
        }
    
    def get_performance_recommendations(self) -> List[Dict[str, Any]]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        for tool_name, profile in self.tool_profiles.items():
            # Slow execution time recommendations
            if profile.avg_execution_time > self.performance_thresholds["execution_time_warning"]:
                recommendations.append({
                    "type": "performance_optimization",
                    "priority": "high" if profile.avg_execution_time > self.performance_thresholds["execution_time_critical"] else "medium",
                    "tool": tool_name,
                    "issue": f"Average execution time ({profile.avg_execution_time:.2f}s) exceeds threshold",
                    "recommendation": "Consider optimizing API queries, implementing request batching, or increasing cache TTL",
                    "impact": "Reduced user experience and increased resource usage"
                })
            
            # Low success rate recommendations
            success_rate = profile.get_success_rate() / 100
            if success_rate < self.performance_thresholds["success_rate_warning"]:
                recommendations.append({
                    "type": "reliability_improvement",
                    "priority": "high" if success_rate < self.performance_thresholds["success_rate_critical"] else "medium",
                    "tool": tool_name,
                    "issue": f"Success rate ({success_rate:.1%}) below threshold",
                    "recommendation": "Investigate error patterns, improve error handling, implement circuit breakers",
                    "impact": "Failed operations and degraded user experience"
                })
            
            # Low cache hit rate recommendations
            cache_rate = profile.get_cache_hit_rate() / 100
            if cache_rate < self.performance_thresholds["cache_hit_rate_warning"]:
                recommendations.append({
                    "type": "caching_optimization",
                    "priority": "medium",
                    "tool": tool_name,
                    "issue": f"Cache hit rate ({cache_rate:.1%}) below optimal",
                    "recommendation": "Review cache TTL settings, implement intelligent cache warming, optimize cache keys",
                    "impact": "Increased API load and slower response times"
                })
        
        # Sort by priority
        priority_order = {"high": 3, "medium": 2, "low": 1}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 0), reverse=True)
        
        return recommendations
    
    def _add_metric(self, metric_type: MetricType, tool_name: str, value: float, context: Dict[str, Any]):
        """Add a performance metric to the collection"""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_type=metric_type,
            tool_name=tool_name,
            value=value,
            context=context
        )
        
        self.metrics.append(metric)
        
        # Cleanup old metrics if needed
        if len(self.metrics) % 1000 == 0:  # Check every 1000 metrics
            self._cleanup_old_metrics()
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than max_metrics_age_hours"""
        cutoff_time = datetime.now() - timedelta(hours=self.max_metrics_age_hours)
        
        # Remove old metrics
        while self.metrics and self.metrics[0].timestamp < cutoff_time:
            self.metrics.popleft()
        
        # Remove old system metrics
        while self.system_metrics and self.system_metrics[0]["timestamp"] < cutoff_time:
            self.system_metrics.popleft()
        
        self.monitoring_stats["last_cleanup_time"] = datetime.now()
    
    def _check_performance_alerts(self, tool_name: str, profile: ToolPerformanceProfile):
        """Check for performance issues and generate alerts"""
        alerts = []
        
        # Critical execution time
        if profile.avg_execution_time > self.performance_thresholds["execution_time_critical"]:
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "severity": "critical",
                "type": "slow_execution",
                "tool": tool_name,
                "message": f"Tool {tool_name} average execution time ({profile.avg_execution_time:.2f}s) exceeds critical threshold",
                "value": profile.avg_execution_time,
                "threshold": self.performance_thresholds["execution_time_critical"]
            })
        
        # Critical success rate
        success_rate = profile.get_success_rate() / 100
        if success_rate < self.performance_thresholds["success_rate_critical"]:
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "severity": "critical",
                "type": "low_success_rate",
                "tool": tool_name,
                "message": f"Tool {tool_name} success rate ({success_rate:.1%}) below critical threshold",
                "value": success_rate,
                "threshold": self.performance_thresholds["success_rate_critical"]
            })
        
        # Add alerts to collection
        for alert in alerts:
            self.performance_alerts.append(alert)
            self.monitoring_stats["performance_alerts_generated"] += 1
            self.logger.warning(f"Performance alert: {alert['message']}")
        
        # Keep only recent alerts (last 100)
        self.performance_alerts = self.performance_alerts[-100:]
    
    def _get_recent_metrics(self, window_minutes: int) -> List[PerformanceMetric]:
        """Get metrics from the specified time window"""
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        return [m for m in self.metrics if m.timestamp >= cutoff_time]
    
    def _analyze_trends(self, metrics: List[PerformanceMetric]) -> Dict[str, Any]:
        """Analyze performance trends from recent metrics"""
        if len(metrics) < 2:
            return {"status": "insufficient_data"}
        
        # Group metrics by type and tool
        grouped_metrics = defaultdict(lambda: defaultdict(list))
        for metric in metrics:
            grouped_metrics[metric.metric_type][metric.tool_name].append(metric.value)
        
        trends = {}
        
        # Analyze execution time trends
        if MetricType.EXECUTION_TIME in grouped_metrics:
            exec_trends = {}
            for tool, values in grouped_metrics[MetricType.EXECUTION_TIME].items():
                if len(values) >= 2:
                    recent_avg = statistics.mean(values[-5:])  # Last 5 values
                    overall_avg = statistics.mean(values)
                    trend = "improving" if recent_avg < overall_avg else "degrading" if recent_avg > overall_avg else "stable"
                    exec_trends[tool] = {
                        "trend": trend,
                        "recent_avg": recent_avg,
                        "overall_avg": overall_avg,
                        "change_percent": ((recent_avg - overall_avg) / overall_avg * 100) if overall_avg > 0 else 0
                    }
            trends["execution_time"] = exec_trends
        
        # Analyze success rate trends
        if MetricType.SUCCESS_RATE in grouped_metrics:
            success_trends = {}
            for tool, values in grouped_metrics[MetricType.SUCCESS_RATE].items():
                if len(values) >= 2:
                    recent_avg = statistics.mean(values[-10:])  # Last 10 values
                    overall_avg = statistics.mean(values)
                    trend = "improving" if recent_avg > overall_avg else "degrading" if recent_avg < overall_avg else "stable"
                    success_trends[tool] = {
                        "trend": trend,
                        "recent_avg": recent_avg,
                        "overall_avg": overall_avg
                    }
            trends["success_rate"] = success_trends
        
        return trends
    
    def _get_top_performing_tools(self, limit: int) -> List[Dict[str, Any]]:
        """Get top performing tools based on composite score"""
        tool_scores = []
        
        for tool_name, profile in self.tool_profiles.items():
            if profile.total_executions > 0:
                # Composite performance score
                success_rate = profile.get_success_rate() / 100
                cache_rate = profile.get_cache_hit_rate() / 100
                speed_score = max(0, 1 - (profile.avg_execution_time / 10))  # Normalize to 0-1
                
                composite_score = (success_rate * 0.4) + (speed_score * 0.4) + (cache_rate * 0.2)
                
                tool_scores.append({
                    "tool_name": tool_name,
                    "composite_score": composite_score,
                    "success_rate": success_rate,
                    "avg_execution_time": profile.avg_execution_time,
                    "cache_hit_rate": cache_rate,
                    "total_executions": profile.total_executions
                })
        
        # Sort by composite score
        tool_scores.sort(key=lambda x: x["composite_score"], reverse=True)
        return tool_scores[:limit]
    
    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        for tool_name, profile in self.tool_profiles.items():
            issues = []
            
            if profile.avg_execution_time > self.performance_thresholds["execution_time_warning"]:
                issues.append("slow_execution")
            
            if profile.get_success_rate() < self.performance_thresholds["success_rate_warning"] * 100:
                issues.append("low_success_rate")
            
            if profile.get_cache_hit_rate() < self.performance_thresholds["cache_hit_rate_warning"] * 100:
                issues.append("poor_caching")
            
            if profile.retry_count > profile.successful_executions * 0.1:  # More than 10% retries
                issues.append("excessive_retries")
            
            if issues:
                bottlenecks.append({
                    "tool_name": tool_name,
                    "issues": issues,
                    "severity": "critical" if len(issues) >= 3 else "warning",
                    "avg_execution_time": profile.avg_execution_time,
                    "success_rate": profile.get_success_rate(),
                    "cache_hit_rate": profile.get_cache_hit_rate()
                })
        
        # Sort by severity and number of issues
        bottlenecks.sort(key=lambda x: (x["severity"] == "critical", len(x["issues"])), reverse=True)
        return bottlenecks
    
    def _get_system_health_summary(self) -> Dict[str, Any]:
        """Get current system health metrics"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_usage_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "active_executions": len(self.active_executions),
                "health_status": self._calculate_system_health_status(cpu_percent, memory.percent, disk.percent)
            }
        except Exception as e:
            self.logger.error(f"Error getting system health: {e}")
            return {"error": "Unable to retrieve system health metrics"}
    
    def _calculate_system_health_status(self, cpu_percent: float, memory_percent: float, disk_percent: float) -> str:
        """Calculate overall system health status"""
        if cpu_percent > 90 or memory_percent > 90 or disk_percent > 95:
            return "critical"
        elif cpu_percent > 75 or memory_percent > 75 or disk_percent > 85:
            return "warning"
        else:
            return "healthy"
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        try:
            while self._monitoring_active:
                # Collect system metrics
                try:
                    system_health = self._get_system_health_summary()
                    self.system_metrics.append({
                        "timestamp": datetime.now(),
                        **system_health
                    })
                    
                    # Keep only recent system metrics (last 24 hours worth)
                    max_system_metrics = (24 * 3600) // self.sampling_interval_seconds
                    if len(self.system_metrics) > max_system_metrics:
                        self.system_metrics.popleft()
                    
                except Exception as e:
                    self.logger.error(f"Error collecting system metrics: {e}")
                
                # Periodic cleanup
                if (datetime.now() - self.monitoring_stats["last_cleanup_time"]).total_seconds() > 3600:  # Every hour
                    self._cleanup_old_metrics()
                
                # Wait for next sampling interval
                await asyncio.sleep(self.sampling_interval_seconds)
                
        except asyncio.CancelledError:
            self.logger.info("Performance monitoring loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {e}")
    
    def export_metrics(self, format_type: str = "json") -> Union[str, Dict[str, Any]]:
        """Export performance metrics in specified format"""
        data = {
            "export_timestamp": datetime.now().isoformat(),
            "monitoring_summary": self.get_overall_performance_summary(),
            "tool_profiles": {
                name: self.get_tool_performance_summary(name) 
                for name in self.tool_profiles.keys()
            },
            "recent_metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "type": m.metric_type.value,
                    "tool": m.tool_name,
                    "value": m.value,
                    "context": m.context
                }
                for m in list(self.metrics)[-1000:]  # Last 1000 metrics
            ],
            "performance_recommendations": self.get_performance_recommendations()
        }
        
        if format_type.lower() == "json":
            import json
            return json.dumps(data, indent=2, default=str)
        else:
            return data
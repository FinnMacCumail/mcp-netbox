#!/usr/bin/env python3
"""
NetBox MCP Performance Dashboard
Real-time performance monitoring, optimization tracking, and alerting dashboard.

Features:
- Real-time performance metrics visualization
- Bottleneck identification and alerts
- Optimization recommendations
- Cache performance analysis
- System resource monitoring
- Performance regression detection
"""

import asyncio
import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import asdict

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from netbox_mcp.orchestration.performance_monitor import PerformanceMonitor
from netbox_mcp.orchestration.performance_optimizer import PerformanceOptimizer
from netbox_mcp.orchestration.cache import OrchestrationCache

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PerformanceDashboard:
    """Comprehensive performance monitoring and optimization dashboard"""
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.performance_optimizer = PerformanceOptimizer()
        self.cache = OrchestrationCache()
        
        self.dashboard_config = {
            "refresh_interval_seconds": 30,
            "alert_thresholds": {
                "response_time_critical": 5.0,      # 5 seconds
                "success_rate_critical": 0.7,       # 70%
                "cache_hit_rate_warning": 0.6,      # 60%
                "memory_usage_warning": 80,          # 80%
                "cpu_usage_warning": 75              # 75%
            },
            "performance_targets": {
                "simple_queries": 0.5,              # 500ms
                "intermediate_queries": 1.0,        # 1s
                "complex_queries": 3.0               # 3s
            }
        }
        
        self.active_alerts: List[Dict[str, Any]] = []
        self.performance_history: List[Dict[str, Any]] = []
        
    async def initialize(self) -> bool:
        """Initialize dashboard components"""
        try:
            logger.info("Initializing performance dashboard...")
            
            # Initialize components
            await self.performance_monitor.start_monitoring()
            await self.performance_optimizer.initialize()
            await self.cache.initialize()
            
            logger.info("Performance dashboard initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Dashboard initialization failed: {e}")
            return False
    
    async def collect_comprehensive_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive performance metrics from all sources"""
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system_overview": {},
            "tool_performance": {},
            "cache_performance": {},
            "optimization_status": {},
            "alerts": [],
            "recommendations": []
        }
        
        try:
            # System overview
            system_summary = self.performance_monitor.get_overall_performance_summary()
            metrics["system_overview"] = {
                "total_executions": system_summary.get("overall_stats", {}).get("total_executions", 0),
                "overall_success_rate": system_summary.get("overall_stats", {}).get("overall_success_rate", 0),
                "average_execution_time": system_summary.get("overall_stats", {}).get("average_execution_time", 0),
                "tools_monitored": system_summary.get("overall_stats", {}).get("tools_monitored", 0),
                "performance_distribution": system_summary.get("performance_distribution", {}),
                "system_health": system_summary.get("system_health", {})
            }
            
            # Tool-specific performance
            tool_performance = {}
            for tool_name in self.performance_monitor.tool_profiles.keys():
                tool_summary = self.performance_monitor.get_tool_performance_summary(tool_name)
                if tool_summary:
                    tool_performance[tool_name] = {
                        "performance_level": tool_summary["performance_level"],
                        "success_rate": tool_summary["execution_stats"]["success_rate"],
                        "avg_execution_time": tool_summary["timing_stats"]["avg_execution_time"],
                        "cache_hit_rate": tool_summary["cache_stats"]["cache_hit_rate"],
                        "total_executions": tool_summary["execution_stats"]["total_executions"]
                    }
            
            metrics["tool_performance"] = tool_performance
            
            # Cache performance
            cache_stats = await self.cache.get_cache_statistics()
            metrics["cache_performance"] = cache_stats
            
            # Optimization status
            optimization_summary = await self.performance_optimizer.get_optimization_summary()
            metrics["optimization_status"] = optimization_summary
            
            # Generate alerts
            alerts = await self.generate_performance_alerts(metrics)
            metrics["alerts"] = alerts
            self.active_alerts = alerts
            
            # Generate recommendations
            bottlenecks = await self.performance_optimizer.identify_performance_bottlenecks(system_summary)
            recommendations = await self.performance_optimizer.generate_optimization_recommendations(bottlenecks)
            metrics["recommendations"] = recommendations
            
            # Store in history
            self.performance_history.append(metrics)
            
            # Keep only last 100 entries
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect comprehensive metrics: {e}")
            return metrics
    
    async def generate_performance_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance alerts based on thresholds"""
        
        alerts = []
        thresholds = self.dashboard_config["alert_thresholds"]
        
        try:
            # System-wide alerts
            system_overview = metrics.get("system_overview", {})
            
            # Overall success rate alert
            success_rate = system_overview.get("overall_success_rate", 100) / 100
            if success_rate < thresholds["success_rate_critical"]:
                alerts.append({
                    "severity": "critical",
                    "type": "success_rate",
                    "title": "Critical Success Rate",
                    "description": f"System success rate ({success_rate:.1%}) below critical threshold",
                    "metric_value": success_rate,
                    "threshold": thresholds["success_rate_critical"],
                    "timestamp": datetime.now().isoformat(),
                    "recommended_action": "Investigate failing tools and improve error handling"
                })
            
            # Average execution time alert
            avg_time = system_overview.get("average_execution_time", 0)
            if avg_time > thresholds["response_time_critical"]:
                alerts.append({
                    "severity": "critical",
                    "type": "response_time",
                    "title": "High Average Response Time",
                    "description": f"Average execution time ({avg_time:.2f}s) exceeds critical threshold",
                    "metric_value": avg_time,
                    "threshold": thresholds["response_time_critical"],
                    "timestamp": datetime.now().isoformat(),
                    "recommended_action": "Enable caching and optimize slow tools"
                })
            
            # Cache performance alert
            cache_perf = metrics.get("cache_performance", {})
            hit_rate = cache_perf.get("hit_rate", 100) / 100
            if hit_rate < thresholds["cache_hit_rate_warning"]:
                alerts.append({
                    "severity": "warning",
                    "type": "cache_performance",
                    "title": "Low Cache Hit Rate",
                    "description": f"Cache hit rate ({hit_rate:.1%}) below optimal threshold",
                    "metric_value": hit_rate,
                    "threshold": thresholds["cache_hit_rate_warning"],
                    "timestamp": datetime.now().isoformat(),
                    "recommended_action": "Optimize cache TTL settings and implement cache warming"
                })
            
            # System resource alerts
            system_health = system_overview.get("system_health", {})
            
            memory_usage = system_health.get("memory_usage_percent", 0)
            if memory_usage > thresholds["memory_usage_warning"]:
                alerts.append({
                    "severity": "warning",
                    "type": "memory_usage",
                    "title": "High Memory Usage",
                    "description": f"Memory usage ({memory_usage:.1f}%) exceeds warning threshold",
                    "metric_value": memory_usage,
                    "threshold": thresholds["memory_usage_warning"],
                    "timestamp": datetime.now().isoformat(),
                    "recommended_action": "Implement result pagination and memory optimization"
                })
            
            cpu_usage = system_health.get("cpu_usage_percent", 0)
            if cpu_usage > thresholds["cpu_usage_warning"]:
                alerts.append({
                    "severity": "warning", 
                    "type": "cpu_usage",
                    "title": "High CPU Usage",
                    "description": f"CPU usage ({cpu_usage:.1f}%) exceeds warning threshold",
                    "metric_value": cpu_usage,
                    "threshold": thresholds["cpu_usage_warning"],
                    "timestamp": datetime.now().isoformat(),
                    "recommended_action": "Implement async processing and optimize computational complexity"
                })
            
            # Tool-specific alerts
            tool_performance = metrics.get("tool_performance", {})
            for tool_name, tool_metrics in tool_performance.items():
                tool_success_rate = tool_metrics.get("success_rate", 100) / 100
                tool_avg_time = tool_metrics.get("avg_execution_time", 0)
                
                # Tool success rate alert
                if tool_success_rate < thresholds["success_rate_critical"]:
                    alerts.append({
                        "severity": "high",
                        "type": "tool_reliability",
                        "title": f"Unreliable Tool: {tool_name}",
                        "description": f"Tool {tool_name} success rate ({tool_success_rate:.1%}) below threshold",
                        "tool_name": tool_name,
                        "metric_value": tool_success_rate,
                        "threshold": thresholds["success_rate_critical"],
                        "timestamp": datetime.now().isoformat(),
                        "recommended_action": f"Investigate {tool_name} errors and improve error handling"
                    })
                
                # Tool performance alert based on complexity
                performance_level = tool_metrics.get("performance_level", "acceptable")
                if performance_level in ["poor", "critical"]:
                    alerts.append({
                        "severity": "high" if performance_level == "critical" else "medium",
                        "type": "tool_performance",
                        "title": f"Poor Performance: {tool_name}",
                        "description": f"Tool {tool_name} performance level: {performance_level}",
                        "tool_name": tool_name,
                        "performance_level": performance_level,
                        "avg_execution_time": tool_avg_time,
                        "timestamp": datetime.now().isoformat(),
                        "recommended_action": f"Optimize {tool_name} or enable aggressive caching"
                    })
            
        except Exception as e:
            logger.error(f"Alert generation failed: {e}")
        
        return alerts
    
    def print_dashboard_header(self):
        """Print dashboard header with branding"""
        print("\n" + "="*100)
        print("🚀 NETBOX MCP PERFORMANCE MONITORING DASHBOARD")
        print("="*100)
        print(f"📊 Real-time Performance Analytics | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*100)
    
    def print_system_overview(self, metrics: Dict[str, Any]):
        """Print system overview section"""
        system_overview = metrics.get("system_overview", {})
        
        print("\n📈 SYSTEM OVERVIEW")
        print("-" * 50)
        
        total_executions = system_overview.get("total_executions", 0)
        success_rate = system_overview.get("overall_success_rate", 0)
        avg_time = system_overview.get("average_execution_time", 0)
        tools_monitored = system_overview.get("tools_monitored", 0)
        
        # Status indicators
        success_status = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
        performance_status = "✅" if avg_time < 1.0 else "⚠️" if avg_time < 3.0 else "❌"
        
        print(f"  Total Executions: {total_executions:,}")
        print(f"  Success Rate: {success_status} {success_rate:.1f}%")
        print(f"  Average Response Time: {performance_status} {avg_time:.3f}s")
        print(f"  Tools Monitored: {tools_monitored}")
        
        # Performance distribution
        perf_dist = system_overview.get("performance_distribution", {})
        if perf_dist:
            print(f"\n  Performance Distribution:")
            for level, count in perf_dist.items():
                print(f"    {level.capitalize()}: {count} tools")
        
        # System health
        system_health = system_overview.get("system_health", {})
        if system_health:
            health_status = system_health.get("health_status", "unknown")
            status_icon = "✅" if health_status == "healthy" else "⚠️" if health_status == "warning" else "❌"
            
            print(f"\n  System Health: {status_icon} {health_status.upper()}")
            print(f"    CPU Usage: {system_health.get('cpu_usage_percent', 0):.1f}%")
            print(f"    Memory Usage: {system_health.get('memory_usage_percent', 0):.1f}%")
            print(f"    Disk Usage: {system_health.get('disk_usage_percent', 0):.1f}%")
    
    def print_cache_performance(self, metrics: Dict[str, Any]):
        """Print cache performance section"""
        cache_perf = metrics.get("cache_performance", {})
        
        print("\n💾 CACHE PERFORMANCE")
        print("-" * 50)
        
        hit_rate = cache_perf.get("hit_rate", 0)
        total_requests = cache_perf.get("total_requests", 0)
        cache_hits = cache_perf.get("cache_hits", 0)
        cache_misses = cache_perf.get("cache_misses", 0)
        
        # Cache status
        cache_status = "✅" if hit_rate >= 70 else "⚠️" if hit_rate >= 50 else "❌"
        
        print(f"  Hit Rate: {cache_status} {hit_rate:.1f}%")
        print(f"  Total Requests: {total_requests:,}")
        print(f"  Cache Hits: {cache_hits:,}")
        print(f"  Cache Misses: {cache_misses:,}")
        
        # Performance impact
        perf_impact = cache_perf.get("performance_impact", {})
        if perf_impact:
            api_calls_saved = perf_impact.get("estimated_api_calls_saved", 0)
            time_saved = perf_impact.get("estimated_time_saved_seconds", 0)
            cache_efficiency = perf_impact.get("cache_efficiency", "Unknown")
            
            print(f"\n  Performance Impact:")
            print(f"    API Calls Saved: {api_calls_saved:,}")
            print(f"    Time Saved: {time_saved:.1f}s")
            print(f"    Cache Efficiency: {cache_efficiency}")
    
    def print_top_tools_performance(self, metrics: Dict[str, Any], limit: int = 10):
        """Print top performing and worst performing tools"""
        tool_performance = metrics.get("tool_performance", {})
        
        if not tool_performance:
            return
        
        print(f"\n🏆 TOP {limit} TOOL PERFORMANCE")
        print("-" * 50)
        
        # Sort tools by composite performance score
        def calculate_score(tool_metrics):
            success_rate = tool_metrics.get("success_rate", 0) / 100
            # Inverse of execution time (lower is better)
            speed_score = max(0, 1 - (tool_metrics.get("avg_execution_time", 0) / 5))
            cache_rate = tool_metrics.get("cache_hit_rate", 0) / 100
            
            return (success_rate * 0.4) + (speed_score * 0.4) + (cache_rate * 0.2)
        
        sorted_tools = sorted(
            tool_performance.items(),
            key=lambda x: calculate_score(x[1]),
            reverse=True
        )
        
        print("  🟢 Best Performing Tools:")
        for i, (tool_name, tool_metrics) in enumerate(sorted_tools[:limit//2]):
            score = calculate_score(tool_metrics) * 100
            success_rate = tool_metrics.get("success_rate", 0)
            avg_time = tool_metrics.get("avg_execution_time", 0)
            
            tool_display = tool_name.replace("mcp__netbox__", "").replace("netbox_", "")
            print(f"    {i+1}. {tool_display[:30]:<30} Score: {score:5.1f}% | Success: {success_rate:5.1f}% | Time: {avg_time:6.3f}s")
        
        print("\n  🔴 Needs Optimization:")
        worst_tools = sorted_tools[-limit//2:]
        for i, (tool_name, tool_metrics) in enumerate(reversed(worst_tools)):
            score = calculate_score(tool_metrics) * 100
            success_rate = tool_metrics.get("success_rate", 0)
            avg_time = tool_metrics.get("avg_execution_time", 0)
            
            tool_display = tool_name.replace("mcp__netbox__", "").replace("netbox_", "")
            print(f"    {i+1}. {tool_display[:30]:<30} Score: {score:5.1f}% | Success: {success_rate:5.1f}% | Time: {avg_time:6.3f}s")
    
    def print_alerts_and_recommendations(self, metrics: Dict[str, Any]):
        """Print active alerts and recommendations"""
        alerts = metrics.get("alerts", [])
        recommendations = metrics.get("recommendations", [])
        
        if alerts:
            print(f"\n🚨 ACTIVE ALERTS ({len(alerts)})")
            print("-" * 50)
            
            # Group alerts by severity
            critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
            high_alerts = [a for a in alerts if a.get("severity") == "high"]
            warning_alerts = [a for a in alerts if a.get("severity") == "warning"]
            
            if critical_alerts:
                print("  🔴 CRITICAL:")
                for alert in critical_alerts:
                    print(f"    • {alert['title']}: {alert['description']}")
                    print(f"      Action: {alert['recommended_action']}")
            
            if high_alerts:
                print("  🟡 HIGH:")
                for alert in high_alerts:
                    print(f"    • {alert['title']}: {alert['description']}")
            
            if warning_alerts:
                print("  🟠 WARNING:")
                for alert in warning_alerts[:3]:  # Show only top 3 warnings
                    print(f"    • {alert['title']}: {alert['description']}")
        else:
            print("\n✅ NO ACTIVE ALERTS - System performing within normal parameters")
        
        if recommendations:
            print(f"\n💡 OPTIMIZATION RECOMMENDATIONS ({len(recommendations)})")
            print("-" * 50)
            
            for i, rec in enumerate(recommendations[:3], 1):  # Show top 3 recommendations
                priority_icon = "🔴" if rec.get("priority") == "critical" else "🟡" if rec.get("priority") == "high" else "🟢"
                print(f"  {i}. {priority_icon} {rec['title']}")
                print(f"     {rec['description']}")
                print(f"     Impact: {rec.get('estimated_impact', 'Unknown')}")
                print()
    
    def print_optimization_status(self, metrics: Dict[str, Any]):
        """Print optimization status"""
        opt_status = metrics.get("optimization_status", {})
        
        print("\n⚡ OPTIMIZATION STATUS")
        print("-" * 50)
        
        opt_summary = opt_status.get("optimization_summary", {})
        total_opts = opt_summary.get("total_optimizations", 0)
        successful_opts = opt_summary.get("successful_optimizations", 0)
        success_rate = opt_summary.get("success_rate", 0)
        
        print(f"  Total Optimizations Applied: {total_opts}")
        print(f"  Successful Optimizations: {successful_opts}")
        print(f"  Optimization Success Rate: {success_rate:.1f}%")
        
        # Estimated improvements
        improvements = opt_status.get("estimated_improvements", {})
        if improvements:
            print(f"\n  Estimated Improvements:")
            
            if "openai_api_calls_saved" in improvements:
                print(f"    API Calls Saved: {improvements['openai_api_calls_saved']:,}")
            
            if "cost_savings" in improvements:
                print(f"    Cost Savings: ${improvements['cost_savings']:.2f}")
            
            if "pattern_matching_speedup" in improvements:
                print(f"    Pattern Matching Speedup: {improvements['pattern_matching_speedup']:.1f}%")
        
        # Cache stats from optimizer
        cache_stats = opt_status.get("cache_stats", {})
        if cache_stats and cache_stats.get("total_requests", 0) > 0:
            print(f"\n  OpenAI Cache Performance:")
            print(f"    Hit Rate: {cache_stats.get('hit_rate', 0):.1f}%")
            print(f"    Total Requests: {cache_stats.get('total_requests', 0):,}")
            print(f"    Estimated Cost Savings: ${cache_stats.get('estimated_cost_savings', 0):.2f}")
    
    async def run_dashboard_loop(self, duration_minutes: int = 60):
        """Run the dashboard for a specified duration"""
        
        print("🚀 Starting NetBox MCP Performance Dashboard...")
        print(f"Running for {duration_minutes} minutes with {self.dashboard_config['refresh_interval_seconds']}s refresh interval")
        
        end_time = time.time() + (duration_minutes * 60)
        
        try:
            while time.time() < end_time:
                # Collect comprehensive metrics
                metrics = await self.collect_comprehensive_metrics()
                
                # Clear screen (Unix/Linux/Mac)
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Print dashboard
                self.print_dashboard_header()
                self.print_system_overview(metrics)
                self.print_cache_performance(metrics)
                self.print_top_tools_performance(metrics)
                self.print_optimization_status(metrics)
                self.print_alerts_and_recommendations(metrics)
                
                print(f"\n⏰ Next refresh in {self.dashboard_config['refresh_interval_seconds']}s | Press Ctrl+C to stop")
                print("="*100)
                
                # Wait for refresh interval
                await asyncio.sleep(self.dashboard_config["refresh_interval_seconds"])
                
        except KeyboardInterrupt:
            print("\n\n🛑 Dashboard stopped by user")
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
    
    async def generate_performance_report(self, output_file: str = "performance_report.json"):
        """Generate comprehensive performance report"""
        
        logger.info("Generating comprehensive performance report...")
        
        try:
            # Collect final metrics
            final_metrics = await self.collect_comprehensive_metrics()
            
            # Add historical data
            report = {
                "report_timestamp": datetime.now().isoformat(),
                "report_period": {
                    "start_time": self.performance_history[0]["timestamp"] if self.performance_history else None,
                    "end_time": final_metrics["timestamp"],
                    "total_data_points": len(self.performance_history)
                },
                "current_metrics": final_metrics,
                "historical_data": self.performance_history,
                "summary": {
                    "avg_success_rate": 0,
                    "avg_response_time": 0,
                    "total_optimizations": 0,
                    "active_alerts": len(self.active_alerts),
                    "recommendations_count": len(final_metrics.get("recommendations", []))
                }
            }
            
            # Calculate summary statistics
            if self.performance_history:
                success_rates = [
                    h.get("system_overview", {}).get("overall_success_rate", 0)
                    for h in self.performance_history
                ]
                response_times = [
                    h.get("system_overview", {}).get("average_execution_time", 0)
                    for h in self.performance_history
                ]
                
                if success_rates:
                    report["summary"]["avg_success_rate"] = sum(success_rates) / len(success_rates)
                if response_times:
                    report["summary"]["avg_response_time"] = sum(response_times) / len(response_times)
            
            # Save report
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Performance report saved to: {output_file}")
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {}
    
    async def cleanup(self):
        """Cleanup dashboard resources"""
        await self.performance_monitor.stop_monitoring()
        await self.performance_optimizer.cleanup()


async def main():
    """Main dashboard execution"""
    
    dashboard = PerformanceDashboard()
    
    try:
        # Initialize dashboard
        if not await dashboard.initialize():
            print("❌ Failed to initialize performance dashboard")
            return
        
        # Show menu options
        print("\n🌟 NetBox MCP Performance Dashboard")
        print("Choose an option:")
        print("1. Run real-time dashboard (60 minutes)")
        print("2. Run real-time dashboard (custom duration)")
        print("3. Generate performance report")
        print("4. Run quick performance check")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            await dashboard.run_dashboard_loop(duration_minutes=60)
        
        elif choice == "2":
            duration = int(input("Enter duration in minutes: "))
            await dashboard.run_dashboard_loop(duration_minutes=duration)
        
        elif choice == "3":
            report_file = input("Enter report filename (default: performance_report.json): ").strip()
            if not report_file:
                report_file = "performance_report.json"
            
            report = await dashboard.generate_performance_report(report_file)
            if report:
                print(f"✅ Performance report generated: {report_file}")
            
        elif choice == "4":
            print("\n🔍 Running quick performance check...")
            metrics = await dashboard.collect_comprehensive_metrics()
            
            dashboard.print_dashboard_header()
            dashboard.print_system_overview(metrics)
            dashboard.print_cache_performance(metrics)
            dashboard.print_alerts_and_recommendations(metrics)
            
            print("\n✅ Quick performance check complete")
        
        else:
            print("❌ Invalid choice")
    
    except KeyboardInterrupt:
        print("\n⚠️ Dashboard interrupted by user")
    except Exception as e:
        logger.error(f"Dashboard execution failed: {e}")
        raise
    finally:
        await dashboard.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
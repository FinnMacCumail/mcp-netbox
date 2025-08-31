"""
Intelligent Caching Layer for Real NetBox API Integration
Week 9-12: Real NetBox Integration & Advanced Conversation Management

This module implements Redis-backed caching with intelligent TTL strategies,
performance-driven optimization, and real NetBox API integration patterns.
"""

import asyncio
import json
import logging
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as aioredis
from .coordination import ToolRequest


class CacheStrategy(Enum):
    """Cache strategy types for different NetBox data patterns"""
    STATIC_INFRASTRUCTURE = "static_infrastructure"    # Sites, racks, device types (long TTL)
    SEMI_STATIC_CONFIG = "semi_static_config"          # Device configs, interfaces (medium TTL)
    DYNAMIC_STATUS = "dynamic_status"                  # Health checks, real-time data (short TTL)
    FREQUENTLY_ACCESSED = "frequently_accessed"        # High-usage data (optimized TTL)
    RARELY_ACCESSED = "rarely_accessed"               # Low-usage data (longer TTL)
    PERFORMANCE_SENSITIVE = "performance_sensitive"    # Critical path data (adaptive TTL)


class TTLAdjustmentReason(Enum):
    """Reasons for dynamic TTL adjustments"""
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    ERROR_RATE_INCREASE = "error_rate_increase"
    USAGE_PATTERN_CHANGE = "usage_pattern_change"
    API_LATENCY_HIGH = "api_latency_high"
    CACHE_HIT_RATE_LOW = "cache_hit_rate_low"
    MEMORY_PRESSURE = "memory_pressure"


@dataclass
class CachePerformanceMetrics:
    """Performance metrics for cache optimization"""
    tool_name: str
    avg_execution_time: float
    cache_hit_rate: float
    error_rate: float
    usage_frequency: int
    last_performance_check: datetime
    performance_trend: str = "stable"  # improving, degrading, stable


@dataclass
class DynamicTTLConfig:
    """Dynamic TTL configuration with performance integration"""
    base_ttl: int
    min_ttl: int
    max_ttl: int
    adjustment_factor: float = 1.0
    last_adjusted: Optional[datetime] = None
    adjustment_reason: Optional[TTLAdjustmentReason] = None


@dataclass
class CacheEntry:
    """Structured cache entry with metadata"""
    key: str
    data: Any
    ttl: int
    created_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None


class OrchestrationCache:
    """
    Advanced caching system for real NetBox API integration with intelligent
    TTL management, performance-driven optimization, and dynamic adaptation.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", namespace: str = "netbox_mcp"):
        self.redis_url = redis_url
        self.namespace = namespace
        self.redis_client: Optional[aioredis.Redis] = None
        self.logger = logging.getLogger(__name__)
        
        # Performance monitoring integration (lazy-loaded)
        self._performance_monitor = None
        self._tool_registry = None
        
        # Cache statistics with enhanced tracking
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "errors": 0,
            "dynamic_adjustments": 0,
            "performance_optimizations": 0,
            "memory_evictions": 0
        }
        
        # Dynamic TTL configurations with performance integration
        self.dynamic_ttl_configs: Dict[str, DynamicTTLConfig] = {}
        self.performance_metrics: Dict[str, CachePerformanceMetrics] = {}
        
        # Enhanced tool-specific TTL configuration with strategy classification
        self.tool_cache_strategies = {
            # STATIC_INFRASTRUCTURE - Very stable data, long TTL
            "netbox_list_all_sites": CacheStrategy.STATIC_INFRASTRUCTURE,
            "netbox_list_all_device_types": CacheStrategy.STATIC_INFRASTRUCTURE,
            "netbox_list_all_manufacturers": CacheStrategy.STATIC_INFRASTRUCTURE,
            "netbox_list_all_device_roles": CacheStrategy.STATIC_INFRASTRUCTURE,
            "netbox_list_all_tenant_groups": CacheStrategy.STATIC_INFRASTRUCTURE,
            "netbox_list_all_cluster_types": CacheStrategy.STATIC_INFRASTRUCTURE,
            "netbox_list_all_cluster_groups": CacheStrategy.STATIC_INFRASTRUCTURE,
            
            # SEMI_STATIC_CONFIG - Configuration data, medium TTL
            "netbox_list_all_racks": CacheStrategy.SEMI_STATIC_CONFIG,
            "netbox_list_all_devices": CacheStrategy.SEMI_STATIC_CONFIG,
            "netbox_get_device_info": CacheStrategy.SEMI_STATIC_CONFIG,
            "netbox_get_rack_inventory": CacheStrategy.SEMI_STATIC_CONFIG,
            "netbox_list_all_vlans": CacheStrategy.SEMI_STATIC_CONFIG,
            "netbox_list_all_prefixes": CacheStrategy.SEMI_STATIC_CONFIG,
            "netbox_list_all_tenants": CacheStrategy.SEMI_STATIC_CONFIG,
            "netbox_list_all_clusters": CacheStrategy.SEMI_STATIC_CONFIG,
            "netbox_list_all_virtual_machines": CacheStrategy.SEMI_STATIC_CONFIG,
            
            # DYNAMIC_STATUS - Real-time data, short TTL
            "netbox_health_check": CacheStrategy.DYNAMIC_STATUS,
            "netbox_get_device_interfaces": CacheStrategy.DYNAMIC_STATUS,
            "netbox_get_device_cables": CacheStrategy.DYNAMIC_STATUS,
            "netbox_get_cable_info": CacheStrategy.DYNAMIC_STATUS,
            "netbox_get_power_connection_info": CacheStrategy.DYNAMIC_STATUS,
            
            # PERFORMANCE_SENSITIVE - Critical path data requiring adaptive TTL
            "netbox_get_device_basic_info": CacheStrategy.PERFORMANCE_SENSITIVE,
            "netbox_get_site_info": CacheStrategy.PERFORMANCE_SENSITIVE,
            "netbox_get_rack_elevation": CacheStrategy.PERFORMANCE_SENSITIVE,
        }
        
        # Base TTL configurations by strategy with real API optimization
        self.strategy_ttl_config = {
            CacheStrategy.STATIC_INFRASTRUCTURE: DynamicTTLConfig(
                base_ttl=7200,    # 2 hours base
                min_ttl=1800,     # 30 minutes minimum  
                max_ttl=28800,    # 8 hours maximum
                adjustment_factor=1.0
            ),
            CacheStrategy.SEMI_STATIC_CONFIG: DynamicTTLConfig(
                base_ttl=1800,    # 30 minutes base
                min_ttl=300,      # 5 minutes minimum
                max_ttl=7200,     # 2 hours maximum
                adjustment_factor=1.0
            ),
            CacheStrategy.DYNAMIC_STATUS: DynamicTTLConfig(
                base_ttl=300,     # 5 minutes base
                min_ttl=60,       # 1 minute minimum
                max_ttl=1800,     # 30 minutes maximum
                adjustment_factor=1.0
            ),
            CacheStrategy.FREQUENTLY_ACCESSED: DynamicTTLConfig(
                base_ttl=900,     # 15 minutes base
                min_ttl=300,      # 5 minutes minimum
                max_ttl=3600,     # 1 hour maximum
                adjustment_factor=1.2  # Slightly longer for frequent access
            ),
            CacheStrategy.RARELY_ACCESSED: DynamicTTLConfig(
                base_ttl=3600,    # 1 hour base
                min_ttl=600,      # 10 minutes minimum
                max_ttl=14400,    # 4 hours maximum
                adjustment_factor=0.8  # Shorter for rare access
            ),
            CacheStrategy.PERFORMANCE_SENSITIVE: DynamicTTLConfig(
                base_ttl=600,     # 10 minutes base
                min_ttl=120,      # 2 minutes minimum
                max_ttl=1800,     # 30 minutes maximum
                adjustment_factor=1.0  # Dynamic based on performance
            )
        }
        
        # Performance thresholds for dynamic adjustment
        self.performance_thresholds = {
            "high_latency_ms": 2000,      # 2 seconds
            "low_cache_hit_rate": 0.6,    # 60%
            "high_error_rate": 0.1,       # 10%
            "frequent_access_threshold": 10  # accesses per hour
        }
    
    @property
    def performance_monitor(self):
        """Lazy-load the performance monitor to avoid circular imports"""
        if self._performance_monitor is None:
            try:
                from .performance_monitor import PerformanceMonitor
                self._performance_monitor = PerformanceMonitor()
            except ImportError:
                self.logger.warning("PerformanceMonitor not available for cache optimization")
        return self._performance_monitor
    
    @property 
    def tool_registry(self):
        """Lazy-load the tool registry to avoid circular imports"""
        if self._tool_registry is None:
            try:
                from .tool_registry import ReadOnlyToolRegistry
                self._tool_registry = ReadOnlyToolRegistry()
            except ImportError:
                self.logger.warning("ReadOnlyToolRegistry not available for cache optimization")
        return self._tool_registry
    
    async def initialize(self) -> bool:
        """Initialize Redis connection, verify connectivity, and setup performance integration"""
        try:
            self.redis_client = aioredis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # Initialize dynamic TTL configurations for known tools
            await self._initialize_dynamic_ttl_configs()
            
            # Start performance monitoring integration if available
            if self.performance_monitor:
                await self._setup_performance_integration()
            
            self.logger.info(f"Enhanced cache initialized with namespace '{self.namespace}' and performance integration")
            return True
            
        except Exception as e:
            self.logger.error(f"Cache initialization failed: {e}")
            self.redis_client = None
            return False
    
    async def get(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """Retrieve cached tool result with performance tracking and usage analysis"""
        if not self.redis_client:
            return None
            
        start_time = datetime.now()
        
        try:
            cache_key = self._generate_key(tool_name, params)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                self.stats["hits"] += 1
                
                # Enhanced access tracking with performance metrics
                await self._update_access_tracking(cache_key, tool_name)
                
                # Update usage patterns for dynamic TTL optimization
                await self._update_usage_patterns(tool_name, cache_hit=True)
                
                cache_data = json.loads(cached_data)
                
                # Check if we should consider TTL optimization based on access patterns
                await self._evaluate_ttl_optimization(tool_name, cache_hit=True)
                
                retrieval_time = (datetime.now() - start_time).total_seconds()
                self.logger.debug(f"Cache hit for {tool_name} in {retrieval_time:.3f}s: {cache_key}")
                
                # Return just the result data, not the metadata wrapper
                return cache_data.get("result", cache_data)
            else:
                self.stats["misses"] += 1
                
                # Track cache miss for performance analysis
                await self._update_usage_patterns(tool_name, cache_hit=False)
                await self._evaluate_ttl_optimization(tool_name, cache_hit=False)
                
                self.logger.debug(f"Cache miss for {tool_name}: {cache_key}")
                return None
                
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.warning(f"Cache retrieval error for {tool_name}: {e}")
            return None
    
    async def set(self, tool_name: str, params: Dict[str, Any], result: Any, custom_ttl: Optional[int] = None) -> bool:
        """Cache tool result with intelligent dynamic TTL and performance optimization"""
        if not self.redis_client:
            return False
            
        start_time = datetime.now()
        
        try:
            cache_key = self._generate_key(tool_name, params)
            
            # Calculate intelligent TTL using dynamic strategies
            ttl = custom_ttl or await self._calculate_intelligent_ttl(tool_name, result)
            
            # Prepare enhanced cache data with metadata and performance tracking
            cache_data = {
                "result": result,
                "tool_name": tool_name,
                "params": params,
                "cached_at": datetime.now().isoformat(),
                "ttl": ttl,
                "cache_strategy": self._get_cache_strategy(tool_name).value,
                "performance_metrics": await self._get_performance_snapshot(tool_name),
                "cache_version": "real_api_v1"  # Version for cache compatibility
            }
            
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data, default=str)
            )
            
            # Update performance tracking
            await self._record_cache_operation(tool_name, "set", start_time)
            
            # Store TTL decision for future optimization
            await self._record_ttl_decision(tool_name, ttl, "intelligent_calculation")
            
            self.stats["sets"] += 1
            storage_time = (datetime.now() - start_time).total_seconds()
            self.logger.debug(f"Cached {tool_name} result for {ttl}s in {storage_time:.3f}s: {cache_key}")
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.warning(f"Cache storage error for {tool_name}: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        if not self.redis_client:
            return 0
            
        try:
            full_pattern = f"{self.namespace}:{pattern}"
            keys = await self.redis_client.keys(full_pattern)
            
            if keys:
                deleted_count = await self.redis_client.delete(*keys)
                self.stats["invalidations"] += deleted_count
                self.logger.info(f"Invalidated {deleted_count} cache entries matching '{pattern}'")
                return deleted_count
            
            return 0
            
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.warning(f"Cache invalidation error for pattern '{pattern}': {e}")
            return 0
    
    async def invalidate_tool_cache(self, tool_name: str) -> int:
        """Invalidate all cache entries for specific tool"""
        return await self.invalidate_pattern(f"{tool_name}:*")
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get detailed cache performance statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        # Get Redis memory info if available
        redis_info = {}
        if self.redis_client:
            try:
                info = await self.redis_client.info("memory")
                redis_info = {
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "keyspace": await self._get_keyspace_info()
                }
            except Exception:
                pass
        
        return {
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "cache_hits": self.stats["hits"],
            "cache_misses": self.stats["misses"], 
            "cache_sets": self.stats["sets"],
            "invalidations": self.stats["invalidations"],
            "errors": self.stats["errors"],
            "redis_info": redis_info,
            "performance_impact": {
                "estimated_api_calls_saved": self.stats["hits"],
                "estimated_time_saved_seconds": self.stats["hits"] * 0.8,  # Avg 800ms per API call
                "cache_efficiency": "High" if hit_rate > 70 else "Medium" if hit_rate > 40 else "Low"
            }
        }
    
    def _generate_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Generate consistent cache key for tool and parameters"""
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:12]
        
        return f"{self.namespace}:{tool_name}:{params_hash}"
    
    def _get_tool_ttl(self, tool_name: str) -> int:
        """Get TTL for specific tool based on data volatility (legacy method)"""
        strategy = self._get_cache_strategy(tool_name)
        return self.strategy_ttl_config[strategy].base_ttl
    
    def _get_cache_strategy(self, tool_name: str) -> CacheStrategy:
        """Get cache strategy for tool with intelligent fallback"""
        # Direct lookup
        if tool_name in self.tool_cache_strategies:
            return self.tool_cache_strategies[tool_name]
        
        # Use tool registry for classification if available
        if self.tool_registry and self.tool_registry.is_read_only_tool(tool_name):
            tool_info = self.tool_registry._tool_registry.get(tool_name, {})
            complexity = tool_info.get("complexity", "MODERATE")
            category = tool_info.get("category", "DISCOVERY")
            
            # Map tool registry classification to cache strategy
            if complexity == "SIMPLE" and category in ["DISCOVERY", "STATUS"]:
                return CacheStrategy.DYNAMIC_STATUS
            elif complexity == "COMPLEX" or category == "ANALYSIS":
                return CacheStrategy.PERFORMANCE_SENSITIVE
            else:
                return CacheStrategy.SEMI_STATIC_CONFIG
        
        # Fallback based on tool name patterns
        if "health" in tool_name or "status" in tool_name:
            return CacheStrategy.DYNAMIC_STATUS
        elif "list_all" in tool_name and any(x in tool_name for x in ["sites", "device_types", "manufacturers"]):
            return CacheStrategy.STATIC_INFRASTRUCTURE
        elif "get_device" in tool_name or "get_rack" in tool_name:
            return CacheStrategy.PERFORMANCE_SENSITIVE
        else:
            return CacheStrategy.SEMI_STATIC_CONFIG
    
    async def _calculate_intelligent_ttl(self, tool_name: str, result: Any) -> int:
        """Calculate intelligent TTL based on performance data, usage patterns, and result content"""
        strategy = self._get_cache_strategy(tool_name)
        base_config = self.strategy_ttl_config[strategy]
        
        # Start with strategy base TTL
        calculated_ttl = base_config.base_ttl
        
        # Get current performance metrics if available
        if self.performance_monitor:
            performance_summary = self.performance_monitor.get_tool_performance_summary(tool_name)
            if performance_summary:
                # Adjust based on execution time
                avg_time = performance_summary["timing_stats"]["avg_execution_time"]
                if avg_time > self.performance_thresholds["high_latency_ms"] / 1000:
                    # High latency tools should cache longer
                    calculated_ttl = int(calculated_ttl * 1.5)
                elif avg_time < 0.5:
                    # Fast tools can cache shorter
                    calculated_ttl = int(calculated_ttl * 0.8)
                
                # Adjust based on success rate
                success_rate = performance_summary["execution_stats"]["success_rate"] / 100
                if success_rate < self.performance_thresholds["high_error_rate"]:
                    # Error-prone tools should cache longer when successful
                    calculated_ttl = int(calculated_ttl * 1.3)
        
        # Check usage patterns
        if tool_name in self.performance_metrics:
            metrics = self.performance_metrics[tool_name]
            
            # Frequently accessed tools
            if metrics.usage_frequency > self.performance_thresholds["frequent_access_threshold"]:
                calculated_ttl = int(calculated_ttl * self.strategy_ttl_config[CacheStrategy.FREQUENTLY_ACCESSED].adjustment_factor)
            
            # Cache hit rate optimization
            if metrics.cache_hit_rate < self.performance_thresholds["low_cache_hit_rate"]:
                # Low hit rate suggests TTL might be too short
                calculated_ttl = int(calculated_ttl * 1.2)
        
        # Analyze result content for additional TTL hints
        if isinstance(result, dict):
            # Check if result indicates stable/static data
            if result.get("success", False):
                result_data = result.get("result", {})
                
                # Large result sets might benefit from longer caching
                if isinstance(result_data, (list, dict)):
                    if len(str(result_data)) > 50000:  # Large payload
                        calculated_ttl = int(calculated_ttl * 1.1)
                
                # Check for change indicators in result
                if any(key in str(result_data).lower() for key in ["modified", "updated", "changed"]):
                    # Recent changes suggest shorter TTL
                    calculated_ttl = int(calculated_ttl * 0.9)
        
        # Apply min/max bounds
        calculated_ttl = max(base_config.min_ttl, min(calculated_ttl, base_config.max_ttl))
        
        return calculated_ttl
    
    async def _initialize_dynamic_ttl_configs(self):
        """Initialize dynamic TTL configurations for all known tools"""
        for tool_name, strategy in self.tool_cache_strategies.items():
            base_config = self.strategy_ttl_config[strategy]
            self.dynamic_ttl_configs[tool_name] = DynamicTTLConfig(
                base_ttl=base_config.base_ttl,
                min_ttl=base_config.min_ttl,
                max_ttl=base_config.max_ttl,
                adjustment_factor=base_config.adjustment_factor
            )
    
    async def _setup_performance_integration(self):
        """Setup integration with PerformanceMonitor for dynamic optimization"""
        try:
            if self.performance_monitor:
                # Start performance monitoring if not already active
                if not self.performance_monitor._monitoring_active:
                    await self.performance_monitor.start_monitoring()
                
                self.logger.info("Performance monitoring integration established for cache optimization")
        except Exception as e:
            self.logger.warning(f"Failed to setup performance integration: {e}")
    
    async def _update_access_tracking(self, cache_key: str, tool_name: str):
        """Enhanced access tracking with tool-specific metrics"""
        try:
            access_key = f"{cache_key}:access"
            await self.redis_client.incr(access_key)
            await self.redis_client.expire(access_key, 86400)  # Track for 24 hours
            
            # Update tool-specific usage frequency
            tool_usage_key = f"{self.namespace}:usage:{tool_name}"
            await self.redis_client.incr(tool_usage_key)
            await self.redis_client.expire(tool_usage_key, 3600)  # Hourly usage tracking
            
        except Exception:
            pass  # Non-critical tracking
    
    async def _update_usage_patterns(self, tool_name: str, cache_hit: bool):
        """Update usage patterns for dynamic TTL optimization"""
        try:
            if tool_name not in self.performance_metrics:
                self.performance_metrics[tool_name] = CachePerformanceMetrics(
                    tool_name=tool_name,
                    avg_execution_time=0.0,
                    cache_hit_rate=0.0,
                    error_rate=0.0,
                    usage_frequency=0,
                    last_performance_check=datetime.now()
                )
            
            metrics = self.performance_metrics[tool_name]
            metrics.usage_frequency += 1
            
            # Update cache hit rate (simple moving average)
            current_hit_rate = metrics.cache_hit_rate
            hit_value = 1.0 if cache_hit else 0.0
            alpha = 0.1  # Smoothing factor
            metrics.cache_hit_rate = (1 - alpha) * current_hit_rate + alpha * hit_value
            
        except Exception as e:
            self.logger.debug(f"Error updating usage patterns for {tool_name}: {e}")
    
    async def _evaluate_ttl_optimization(self, tool_name: str, cache_hit: bool):
        """Evaluate if TTL optimization is needed for this tool"""
        try:
            if tool_name not in self.performance_metrics:
                return
            
            metrics = self.performance_metrics[tool_name]
            
            # Check if we need to optimize TTL
            should_optimize = False
            optimization_reason = None
            
            if metrics.cache_hit_rate < self.performance_thresholds["low_cache_hit_rate"]:
                should_optimize = True
                optimization_reason = TTLAdjustmentReason.CACHE_HIT_RATE_LOW
            
            # Get performance data from monitor if available
            if self.performance_monitor and should_optimize:
                perf_summary = self.performance_monitor.get_tool_performance_summary(tool_name)
                if perf_summary:
                    avg_time = perf_summary["timing_stats"]["avg_execution_time"]
                    if avg_time > self.performance_thresholds["high_latency_ms"] / 1000:
                        optimization_reason = TTLAdjustmentReason.API_LATENCY_HIGH
            
            if should_optimize and optimization_reason:
                await self._optimize_tool_ttl(tool_name, optimization_reason)
                
        except Exception as e:
            self.logger.debug(f"Error evaluating TTL optimization for {tool_name}: {e}")
    
    async def _optimize_tool_ttl(self, tool_name: str, reason: TTLAdjustmentReason):
        """Optimize TTL for a specific tool based on performance data"""
        try:
            if tool_name not in self.dynamic_ttl_configs:
                return
            
            config = self.dynamic_ttl_configs[tool_name]
            old_factor = config.adjustment_factor
            
            # Adjust based on reason
            if reason == TTLAdjustmentReason.CACHE_HIT_RATE_LOW:
                config.adjustment_factor = min(2.0, config.adjustment_factor * 1.2)
            elif reason == TTLAdjustmentReason.API_LATENCY_HIGH:
                config.adjustment_factor = min(2.0, config.adjustment_factor * 1.3)
            elif reason == TTLAdjustmentReason.PERFORMANCE_OPTIMIZATION:
                config.adjustment_factor = min(2.0, config.adjustment_factor * 1.1)
            
            config.last_adjusted = datetime.now()
            config.adjustment_reason = reason
            
            if config.adjustment_factor != old_factor:
                self.stats["dynamic_adjustments"] += 1
                self.logger.info(
                    f"Optimized TTL for {tool_name}: factor {old_factor:.2f} -> {config.adjustment_factor:.2f} "
                    f"(reason: {reason.value})"
                )
                
        except Exception as e:
            self.logger.warning(f"Error optimizing TTL for {tool_name}: {e}")
    
    async def _get_performance_snapshot(self, tool_name: str) -> Dict[str, Any]:
        """Get current performance snapshot for cache metadata"""
        try:
            if self.performance_monitor:
                summary = self.performance_monitor.get_tool_performance_summary(tool_name)
                if summary:
                    return {
                        "avg_execution_time": summary["timing_stats"]["avg_execution_time"],
                        "success_rate": summary["execution_stats"]["success_rate"],
                        "cache_hit_rate": summary["cache_stats"]["cache_hit_rate"],
                        "performance_level": summary["performance_level"]
                    }
        except Exception:
            pass
        
        return {"snapshot_available": False}
    
    async def _record_cache_operation(self, tool_name: str, operation: str, start_time: datetime):
        """Record cache operation performance for monitoring"""
        try:
            duration = (datetime.now() - start_time).total_seconds()
            
            # Store operation metrics in Redis for analysis
            metrics_key = f"{self.namespace}:metrics:{tool_name}:{operation}"
            await self.redis_client.lpush(metrics_key, json.dumps({
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "operation": operation
            }))
            await self.redis_client.ltrim(metrics_key, 0, 99)  # Keep last 100 operations
            await self.redis_client.expire(metrics_key, 86400)  # 24 hour retention
            
        except Exception:
            pass  # Non-critical operation
    
    async def _record_ttl_decision(self, tool_name: str, ttl: int, method: str):
        """Record TTL decision for analysis and optimization"""
        try:
            decision_key = f"{self.namespace}:ttl_decisions:{tool_name}"
            await self.redis_client.lpush(decision_key, json.dumps({
                "timestamp": datetime.now().isoformat(),
                "ttl": ttl,
                "method": method,
                "strategy": self._get_cache_strategy(tool_name).value
            }))
            await self.redis_client.ltrim(decision_key, 0, 49)  # Keep last 50 decisions
            await self.redis_client.expire(decision_key, 86400)  # 24 hour retention
            
        except Exception:
            pass  # Non-critical operation
    
    async def _get_keyspace_info(self) -> Dict[str, Any]:
        """Get keyspace information for our namespace"""
        try:
            keys = await self.redis_client.keys(f"{self.namespace}:*")
            return {
                "total_keys": len(keys),
                "namespace": self.namespace
            }
        except Exception:
            return {"error": "Unable to retrieve keyspace info"}


class CacheWarmer:
    """
    Proactive cache warming for frequently accessed NetBox data
    """
    
    def __init__(self, cache: OrchestrationCache, coordinator: 'ToolCoordinator'):
        self.cache = cache
        self.coordinator = coordinator
        self.logger = logging.getLogger(__name__)
    
    async def warm_infrastructure_cache(self, site_names: Optional[List[str]] = None):
        """Warm cache with commonly accessed infrastructure data"""
        self.logger.info("Starting infrastructure cache warming...")
        
        # Core infrastructure queries to pre-cache
        warm_requests = [
            ToolRequest("netbox_list_all_sites", {}),
            ToolRequest("netbox_list_all_device_types", {}),
            ToolRequest("netbox_list_all_manufacturers", {}),
            ToolRequest("netbox_list_all_device_roles", {})
        ]
        
        # Site-specific warming if sites provided
        if site_names:
            for site in site_names:
                warm_requests.extend([
                    ToolRequest("netbox_list_all_racks", {"site_name": site}),
                    ToolRequest("netbox_list_all_devices", {"site_name": site}),
                    ToolRequest("netbox_list_all_vlans", {"site_name": site})
                ])
        
        # Execute warming requests
        results = await self.coordinator.coordinate_tools(warm_requests)
        
        success_count = len([r for r in results if r.success])
        self.logger.info(f"Cache warming completed: {success_count}/{len(warm_requests)} successful")
        
        return {
            "total_requests": len(warm_requests),
            "successful": success_count,
            "cache_entries_created": success_count,
            "estimated_performance_boost": f"{success_count * 0.8}s saved per subsequent query"
        }
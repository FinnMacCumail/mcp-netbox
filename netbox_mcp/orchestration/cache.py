"""
Intelligent Caching Layer for NetBox Tool Coordination

This module implements Redis-backed caching with tool-specific TTL strategies
and intelligent cache invalidation for optimal performance.
"""

import asyncio
import json
import logging
import hashlib
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass

import redis.asyncio as aioredis
from .coordination import ToolRequest


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
    Advanced caching system for NetBox tool coordination with intelligent
    TTL management and performance optimization
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", namespace: str = "netbox_mcp"):
        self.redis_url = redis_url
        self.namespace = namespace
        self.redis_client: Optional[aioredis.Redis] = None
        self.logger = logging.getLogger(__name__)
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "errors": 0
        }
        
        # Tool-specific TTL configuration
        self.tool_ttl_config = {
            # Infrastructure topology (very stable)
            "netbox_list_all_sites": 3600,           # 1 hour
            "netbox_list_all_racks": 1800,           # 30 minutes  
            "netbox_list_all_device_types": 7200,    # 2 hours
            "netbox_list_all_manufacturers": 14400,  # 4 hours
            
            # Device configuration (moderately stable)
            "netbox_get_device_info": 600,           # 10 minutes
            "netbox_list_all_devices": 900,          # 15 minutes
            "netbox_get_rack_inventory": 1200,       # 20 minutes
            
            # Network configuration (changes frequently)
            "netbox_get_device_interfaces": 300,     # 5 minutes
            "netbox_list_all_vlans": 600,            # 10 minutes
            "netbox_get_device_cables": 900,         # 15 minutes
            
            # Dynamic status (very dynamic)
            "netbox_health_check": 60,               # 1 minute
            "netbox_get_cable_info": 300,            # 5 minutes
            
            # IP/IPAM data (moderate frequency)
            "netbox_list_all_prefixes": 1800,        # 30 minutes
            "netbox_list_all_ip_addresses": 600,     # 10 minutes
            
            # Power/environmental (stable)
            "netbox_list_all_power_feeds": 1800,     # 30 minutes
            "netbox_list_all_power_panels": 3600,    # 1 hour
        }
    
    async def initialize(self) -> bool:
        """Initialize Redis connection and verify connectivity"""
        try:
            self.redis_client = aioredis.from_url(self.redis_url)
            await self.redis_client.ping()
            self.logger.info(f"Cache initialized with namespace '{self.namespace}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Cache initialization failed: {e}")
            self.redis_client = None
            return False
    
    async def get(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """Retrieve cached tool result"""
        if not self.redis_client:
            return None
            
        try:
            cache_key = self._generate_key(tool_name, params)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                self.stats["hits"] += 1
                
                # Update access tracking
                await self._update_access_tracking(cache_key)
                
                result = json.loads(cached_data)
                self.logger.debug(f"Cache hit for {tool_name}: {cache_key}")
                return result
            else:
                self.stats["misses"] += 1
                self.logger.debug(f"Cache miss for {tool_name}: {cache_key}")
                return None
                
        except Exception as e:
            self.stats["errors"] += 1
            self.logger.warning(f"Cache retrieval error for {tool_name}: {e}")
            return None
    
    async def set(self, tool_name: str, params: Dict[str, Any], result: Any, custom_ttl: Optional[int] = None) -> bool:
        """Cache tool result with intelligent TTL"""
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._generate_key(tool_name, params)
            ttl = custom_ttl or self._get_tool_ttl(tool_name)
            
            # Prepare cache data with metadata
            cache_data = {
                "result": result,
                "tool_name": tool_name,
                "params": params,
                "cached_at": datetime.now().isoformat(),
                "ttl": ttl
            }
            
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data, default=str)
            )
            
            self.stats["sets"] += 1
            self.logger.debug(f"Cached {tool_name} result for {ttl}s: {cache_key}")
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
        """Get TTL for specific tool based on data volatility"""
        return self.tool_ttl_config.get(tool_name, 600)  # 10 minute default
    
    async def _update_access_tracking(self, cache_key: str):
        """Update access tracking for cache optimization"""
        try:
            access_key = f"{cache_key}:access"
            await self.redis_client.incr(access_key)
            await self.redis_client.expire(access_key, 86400)  # Track for 24 hours
        except Exception:
            pass  # Non-critical tracking
    
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
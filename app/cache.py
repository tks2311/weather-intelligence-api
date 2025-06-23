import hashlib
import json
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

# Simple in-memory cache (in production, use Redis)
CACHE: Dict[str, Dict[str, Any]] = {}

class WeatherCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self.ttl_seconds = ttl_seconds
    
    def _generate_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key from endpoint and parameters"""
        # Sort params for consistent keys
        sorted_params = json.dumps(params, sort_keys=True)
        key_string = f"{endpoint}:{sorted_params}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached data if available and not expired"""
        key = self._generate_key(endpoint, params)
        
        if key in CACHE:
            cache_entry = CACHE[key]
            if time.time() - cache_entry["timestamp"] < self.ttl_seconds:
                cache_entry["hits"] += 1
                return cache_entry["data"]
            else:
                # Expired, remove from cache
                del CACHE[key]
        
        return None
    
    def set(self, endpoint: str, params: Dict[str, Any], data: Any) -> None:
        """Cache data with timestamp"""
        key = self._generate_key(endpoint, params)
        CACHE[key] = {
            "data": data,
            "timestamp": time.time(),
            "hits": 0,
            "endpoint": endpoint
        }
    
    def clear_expired(self) -> int:
        """Clear expired cache entries and return count cleared"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in CACHE.items()
            if current_time - entry["timestamp"] > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del CACHE[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(CACHE)
        total_hits = sum(entry.get("hits", 0) for entry in CACHE.values())
        
        endpoint_stats = {}
        for entry in CACHE.values():
            endpoint = entry.get("endpoint", "unknown")
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {"count": 0, "hits": 0}
            endpoint_stats[endpoint]["count"] += 1
            endpoint_stats[endpoint]["hits"] += entry.get("hits", 0)
        
        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "endpoint_breakdown": endpoint_stats,
            "cache_size_mb": sum(len(str(entry)) for entry in CACHE.values()) / 1024 / 1024
        }

# Global cache instance
weather_cache = WeatherCache(ttl_seconds=300)  # 5 minutes

def cache_key_for_weather(city: str, country: Optional[str] = None, 
                         lat: Optional[float] = None, lon: Optional[float] = None,
                         units: str = "metric") -> Dict[str, Any]:
    """Generate cache key parameters for weather requests"""
    if lat and lon:
        return {"lat": lat, "lon": lon, "units": units}
    else:
        return {"city": city, "country": country, "units": units}
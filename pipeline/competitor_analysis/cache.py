"""
Cache management for competitor analysis results.
Supports TTL-based caching and force refresh.
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from .models import CompetitorProfile


class CompetitorCache:
    """Cache manager for competitor profiles."""
    
    def __init__(self, cache_dir: str = None, ttl_days: int = None):
        self.cache_dir = Path(cache_dir or os.getenv("CACHE_DIR", "./cache/competitor_profiles"))
        self.ttl_days = ttl_days or int(os.getenv("CACHE_TTL_DAYS", "7"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, domain: str) -> Path:
        """Get cache file path for a domain."""
        # Sanitize domain for filename
        safe_domain = domain.replace(".", "_").replace("/", "_")
        return self.cache_dir / f"{safe_domain}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is within TTL."""
        if not cache_path.exists():
            return False
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            analyzed_at = data.get("analyzedAt")
            if not analyzed_at:
                return False
            
            cache_time = datetime.fromisoformat(analyzed_at)
            expiry_time = cache_time + timedelta(days=self.ttl_days)
            
            return datetime.now() < expiry_time
        except (json.JSONDecodeError, ValueError, KeyError):
            return False
    
    def get(self, domain: str, force_refresh: bool = False) -> Optional[CompetitorProfile]:
        """
        Get cached competitor profile.
        
        Args:
            domain: Competitor domain
            force_refresh: If True, ignore cache and return None
            
        Returns:
            Cached profile or None if not found/expired
        """
        if force_refresh:
            return None
        
        cache_path = self._get_cache_path(domain)
        
        if not self._is_cache_valid(cache_path):
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CompetitorProfile.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Cache read error for {domain}: {e}")
            return None
    
    def set(self, profile: CompetitorProfile) -> None:
        """Cache a competitor profile."""
        cache_path = self._get_cache_path(profile.domain)
        
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Cache write error for {profile.domain}: {e}")
    
    def clear(self, domain: Optional[str] = None) -> None:
        """
        Clear cache for a specific domain or all domains.
        
        Args:
            domain: Specific domain to clear, or None to clear all
        """
        if domain:
            cache_path = self._get_cache_path(domain)
            if cache_path.exists():
                cache_path.unlink()
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
    
    def list_cached(self) -> Dict[str, datetime]:
        """List all cached domains with their cache times."""
        cached = {}
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                domain = data.get("domain", cache_file.stem.replace("_", "."))
                analyzed_at = data.get("analyzedAt")
                if analyzed_at:
                    cached[domain] = datetime.fromisoformat(analyzed_at)
            except (json.JSONDecodeError, KeyError):
                continue
        return cached
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cached = self.list_cached()
        now = datetime.now()
        
        valid_count = sum(
            1 for cache_time in cached.values()
            if now < cache_time + timedelta(days=self.ttl_days)
        )
        expired_count = len(cached) - valid_count
        
        return {
            "total_cached": len(cached),
            "valid": valid_count,
            "expired": expired_count,
            "ttl_days": self.ttl_days,
            "cache_dir": str(self.cache_dir)
        }

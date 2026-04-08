"""
Competitor website fetcher with anti-detection measures.
Uses UA rotation and random delays to avoid being blocked.
"""
import random
import time
import os
from typing import Optional, Dict
from urllib.parse import urljoin, urlparse

# Try to import scrapling, fall back to requests if not available
try:
    from scrapling import Fetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    import requests


# User agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Accept-Language headers
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
]


class CompetitorFetcher:
    """Fetch competitor websites with anti-detection measures."""
    
    def __init__(self, delay_min: int = None, delay_max: int = None, timeout: int = None):
        self.delay_min = delay_min or int(os.getenv("FETCH_DELAY_MIN", "2"))
        self.delay_max = delay_max or int(os.getenv("FETCH_DELAY_MAX", "5"))
        self.timeout = timeout or int(os.getenv("FETCH_TIMEOUT", "30"))
        self.last_fetch_time = 0
        
        if SCRAPLING_AVAILABLE:
            self.fetcher = Fetcher()
        else:
            self.session = requests.Session()
    
    def _get_random_headers(self) -> Dict[str, str]:
        """Generate random headers for each request."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
    
    def _apply_delay(self):
        """Apply random delay between requests."""
        delay = random.uniform(self.delay_min, self.delay_max)
        time.sleep(delay)
    
    def _normalize_url(self, domain: str) -> str:
        """Normalize domain to full URL."""
        if not domain.startswith(("http://", "https://")):
            return f"https://{domain}"
        return domain
    
    def fetch(self, domain: str, path: str = "/") -> Optional[str]:
        """
        Fetch a competitor website.
        
        Args:
            domain: Domain name (e.g., "suno.ai")
            path: Path to fetch (default: "/")
            
        Returns:
            HTML content or None if failed
        """
        self._apply_delay()
        
        base_url = self._normalize_url(domain)
        url = urljoin(base_url, path)
        headers = self._get_random_headers()
        
        try:
            if SCRAPLING_AVAILABLE:
                # Use scrapling for better anti-detection
                response = self.fetcher.get(url, headers=headers, timeout=self.timeout)
                return response.text
            else:
                # Fallback to requests
                response = self.session.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                return response.text
                
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return None
    
    def fetch_pricing_page(self, domain: str) -> Optional[str]:
        """
        Try to fetch pricing page with common paths.
        
        Args:
            domain: Domain name
            
        Returns:
            HTML content or None if failed
        """
        pricing_paths = [
            "/pricing",
            "/price",
            "/plans",
            "/subscribe",
            "/subscription",
        ]
        
        for path in pricing_paths:
            content = self.fetch(domain, path)
            if content:
                return content
        
        return None
    
    def fetch_landing_page(self, domain: str) -> Optional[str]:
        """
        Fetch main landing page.
        
        Args:
            domain: Domain name
            
        Returns:
            HTML content or None if failed
        """
        return self.fetch(domain, "/")
    
    def fetch_all(self, domain: str) -> Dict[str, Optional[str]]:
        """
        Fetch both landing and pricing pages.
        
        Args:
            domain: Domain name
            
        Returns:
            Dict with 'landing' and 'pricing' keys
        """
        return {
            "landing": self.fetch_landing_page(domain),
            "pricing": self.fetch_pricing_page(domain),
        }

"""Base fetcher implementation."""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional, Union
from urllib.parse import urlparse

import requests

from transqa.core.interfaces import BaseAnalyzer, FetchError

logger = logging.getLogger(__name__)


class BaseFetcher(BaseAnalyzer, ABC):
    """Base class for web content fetchers."""
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize the fetcher with configuration."""
        super().__init__(config)
        self.config = config or {}
        
        # Common configuration
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        self.user_agent = self.config.get('user_agent', 'TransQA/1.0 (+https://github.com/transqa/transqa)')
        self.headers = self.config.get('headers', {})
        
        # Request session for connection pooling
        self.session: Optional[requests.Session] = None
    
    def initialize(self) -> None:
        """Initialize the fetcher."""
        self.session = requests.Session()
        
        # Set default headers
        default_headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        default_headers.update(self.headers)
        self.session.headers.update(default_headers)
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.session:
            self.session.close()
            self.session = None
    
    @abstractmethod
    def get(self, url: str, render: bool = False, **kwargs) -> str:
        """Fetch HTML content from a URL."""
        pass
    
    @abstractmethod
    def get_with_metadata(self, url: str, render: bool = False, **kwargs) -> Dict[str, Union[str, int, float]]:
        """Fetch content with additional metadata."""
        pass
    
    def _validate_url(self, url: str) -> None:
        """Validate URL format."""
        try:
            result = urlparse(url)
            if not result.scheme or not result.netloc:
                raise ValueError(f"Invalid URL format: {url}")
            
            if result.scheme not in ['http', 'https']:
                raise ValueError(f"Unsupported URL scheme: {result.scheme}")
        
        except Exception as e:
            raise FetchError(f"URL validation failed: {e}")
    
    def _retry_request(self, func, *args, **kwargs):
        """Execute a function with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            
            except (requests.RequestException, Exception) as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")
        
        # If we get here, all retries failed
        raise FetchError(f"Failed after {self.max_retries + 1} attempts: {last_exception}")
    
    def _calculate_content_metrics(self, content: str, response_time: float) -> Dict[str, Union[str, int, float]]:
        """Calculate basic metrics for fetched content."""
        return {
            'content_length': len(content),
            'response_time_ms': response_time * 1000,
            'word_count': len(content.split()) if content else 0,
            'line_count': content.count('\n') if content else 0,
        }

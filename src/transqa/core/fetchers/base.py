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
        """Execute a function with retry logic and absolute timeout."""
        last_exception = None
        start_time = time.time()
        max_total_time = getattr(self, 'max_total_time', 30)  # 30 seconds max total
        
        # Check for fail_fast mode
        fail_fast = getattr(self, 'fail_fast', False)
        
        # Limit retries to prevent infinite loops
        actual_retries = min(self.max_retries, 3) if not fail_fast else 0
        
        for attempt in range(actual_retries + 1):
            # Check absolute timeout
            elapsed = time.time() - start_time
            if elapsed > max_total_time:
                raise FetchError(f"Request timed out after {elapsed:.1f}s (absolute limit: {max_total_time}s)")
            
            try:
                return func(*args, **kwargs)
            
            except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout) as e:
                # Don't retry on timeout errors if fail_fast is enabled
                if fail_fast:
                    raise FetchError(f"Timeout error (fail fast mode): {e}")
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
            
            except requests.exceptions.ConnectionError as e:
                # Don't retry connection errors if fail_fast is enabled
                if fail_fast:
                    raise FetchError(f"Connection error (fail fast mode): {e}")
                last_exception = e
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
            
            except requests.exceptions.HTTPError as e:
                # Don't retry client errors (4xx) but retry server errors (5xx)
                if hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                    if 400 <= status_code < 500:
                        raise FetchError(f"Client error {status_code}: {e}")
                last_exception = e
                logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
            
            except (requests.RequestException, Exception) as e:
                last_exception = e
                logger.warning(f"Error on attempt {attempt + 1}: {e}")
            
            # If we have retries left and haven't raised an exception, wait and retry
            if attempt < actual_retries:
                wait_time = min(2 ** attempt, 3)  # Shorter backoff: max 3s
                logger.warning(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {actual_retries + 1} attempts failed")
        
        # If we get here, all retries failed
        raise FetchError(f"Failed after {actual_retries + 1} attempts: {last_exception}")
    
    def _calculate_content_metrics(self, content: str, response_time: float) -> Dict[str, Union[str, int, float]]:
        """Calculate basic metrics for fetched content."""
        return {
            'content_length': len(content),
            'response_time_ms': response_time * 1000,
            'word_count': len(content.split()) if content else 0,
            'line_count': content.count('\n') if content else 0,
        }

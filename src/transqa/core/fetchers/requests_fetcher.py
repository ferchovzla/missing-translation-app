"""HTTP requests-based fetcher for static content."""

import logging
import time
from typing import Dict, Optional, Union

import requests

from transqa.core.fetchers.base import BaseFetcher
from transqa.core.interfaces import FetchError

logger = logging.getLogger(__name__)


class RequestsFetcher(BaseFetcher):
    """Fetcher using requests library for static HTML content."""
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize requests fetcher."""
        super().__init__(config)
        
        # Additional requests-specific config
        self.allow_redirects = self.config.get('allow_redirects', True)
        self.max_redirects = self.config.get('max_redirects', 10)
        self.verify_ssl = self.config.get('verify_ssl', True)
        self.stream = self.config.get('stream', False)
    
    def get(self, url: str, render: bool = False, **kwargs) -> str:
        """Fetch HTML content from a URL.
        
        Args:
            url: The URL to fetch
            render: Ignored for requests fetcher (no JS rendering)
            **kwargs: Additional request parameters
            
        Returns:
            HTML content as string
            
        Raises:
            FetchError: If fetching fails
        """
        self.ensure_initialized()
        self._validate_url(url)
        
        if render:
            logger.warning("JavaScript rendering requested but not supported by RequestsFetcher. "
                          "Consider using PlaywrightFetcher instead.")
        
        def _fetch():
            start_time = time.time()
            
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=self.allow_redirects,
                verify=self.verify_ssl,
                stream=self.stream,
                **kwargs
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Get content with proper encoding
            content = response.text
            
            # Log basic info
            elapsed_time = time.time() - start_time
            logger.info(f"Fetched {len(content)} chars from {url} in {elapsed_time:.2f}s "
                       f"(status: {response.status_code})")
            
            return content
        
        try:
            return self._retry_request(_fetch)
        except requests.RequestException as e:
            raise FetchError(f"HTTP request failed for {url}: {e}")
        except Exception as e:
            raise FetchError(f"Unexpected error fetching {url}: {e}")
    
    def get_with_metadata(self, url: str, render: bool = False, **kwargs) -> Dict[str, Union[str, int, float]]:
        """Fetch content with detailed metadata.
        
        Args:
            url: The URL to fetch
            render: Ignored for requests fetcher
            **kwargs: Additional request parameters
            
        Returns:
            Dictionary with content and metadata
        """
        self.ensure_initialized()
        self._validate_url(url)
        
        if render:
            logger.warning("JavaScript rendering requested but not supported by RequestsFetcher")
        
        def _fetch_with_metadata():
            start_time = time.time()
            
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=self.allow_redirects,
                verify=self.verify_ssl,
                stream=self.stream,
                **kwargs
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Get content and timing
            content = response.text
            elapsed_time = time.time() - start_time
            
            # Prepare metadata
            metadata = {
                'content': content,
                'status_code': response.status_code,
                'response_time_seconds': elapsed_time,
                'content_type': response.headers.get('content-type', ''),
                'content_encoding': response.encoding or 'unknown',
                'content_length': len(content),
                'url': url,
                'final_url': response.url,  # After redirects
                'redirect_count': len(response.history),
                'server': response.headers.get('server', ''),
                'last_modified': response.headers.get('last-modified', ''),
                'etag': response.headers.get('etag', ''),
            }
            
            # Add basic content metrics
            content_metrics = self._calculate_content_metrics(content, elapsed_time)
            metadata.update(content_metrics)
            
            logger.info(f"Fetched {metadata['content_length']} chars from {url} "
                       f"in {elapsed_time:.2f}s (status: {metadata['status_code']}, "
                       f"redirects: {metadata['redirect_count']})")
            
            return metadata
        
        try:
            return self._retry_request(_fetch_with_metadata)
        except requests.RequestException as e:
            raise FetchError(f"HTTP request failed for {url}: {e}")
        except Exception as e:
            raise FetchError(f"Unexpected error fetching {url}: {e}")
    
    def get_head(self, url: str) -> Dict[str, Union[str, int]]:
        """Perform HEAD request to get headers without downloading content.
        
        Args:
            url: The URL to check
            
        Returns:
            Dictionary with response headers and metadata
        """
        self.ensure_initialized()
        self._validate_url(url)
        
        def _head_request():
            start_time = time.time()
            
            response = self.session.head(
                url,
                timeout=self.timeout,
                allow_redirects=self.allow_redirects,
                verify=self.verify_ssl
            )
            
            response.raise_for_status()
            elapsed_time = time.time() - start_time
            
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'response_time_seconds': elapsed_time,
                'url': url,
                'final_url': response.url,
                'redirect_count': len(response.history),
                'content_type': response.headers.get('content-type', ''),
                'content_length': response.headers.get('content-length', ''),
                'server': response.headers.get('server', ''),
                'last_modified': response.headers.get('last-modified', ''),
            }
        
        try:
            return self._retry_request(_head_request)
        except requests.RequestException as e:
            raise FetchError(f"HEAD request failed for {url}: {e}")
        except Exception as e:
            raise FetchError(f"Unexpected error in HEAD request for {url}: {e}")
    
    def check_availability(self, url: str, method: str = 'HEAD') -> bool:
        """Check if a URL is available without downloading content.
        
        Args:
            url: The URL to check
            method: HTTP method to use ('HEAD' or 'GET')
            
        Returns:
            True if URL is accessible, False otherwise
        """
        try:
            if method.upper() == 'HEAD':
                result = self.get_head(url)
                return 200 <= result['status_code'] < 400
            else:
                content = self.get(url)
                return bool(content)
        except Exception as e:
            logger.debug(f"URL availability check failed for {url}: {e}")
            return False

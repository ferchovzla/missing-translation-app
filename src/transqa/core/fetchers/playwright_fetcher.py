"""Playwright-based fetcher for JavaScript-rendered content."""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Union

from transqa.core.fetchers.base import BaseFetcher
from transqa.core.interfaces import FetchError

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    Browser = None
    BrowserContext = None
    Page = None


class PlaywrightFetcher(BaseFetcher):
    """Fetcher using Playwright for JavaScript-rendered content."""
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize Playwright fetcher."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Install with: pip install playwright && playwright install chromium"
            )
        
        super().__init__(config)
        
        # Playwright-specific configuration
        self.browser_type = self.config.get('browser_type', 'chromium')
        self.headless = self.config.get('headless', True)
        self.viewport_width = self.config.get('viewport_width', 1280)
        self.viewport_height = self.config.get('viewport_height', 720)
        self.page_load_timeout = self.config.get('page_load_timeout', 30000)
        self.network_idle_timeout = self.config.get('network_idle_timeout', 2000)
        self.wait_for_selector = self.config.get('wait_for_selector', None)
        self.block_resources = self.config.get('block_resources', ['image', 'font', 'media'])
        
        # Browser instances (initialized in initialize())
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
    
    def initialize(self) -> None:
        """Initialize Playwright browser."""
        if not PLAYWRIGHT_AVAILABLE:
            raise FetchError("Playwright is not available")
        
        # Run async initialization in sync context
        asyncio.run(self._async_initialize())
    
    async def _async_initialize(self) -> None:
        """Async initialization of Playwright browser."""
        self.playwright = await async_playwright().start()
        
        # Launch browser based on type
        browser_args = {
            'headless': self.headless,
            'args': [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-first-run',
            ]
        }
        
        if self.browser_type == 'chromium':
            self.browser = await self.playwright.chromium.launch(**browser_args)
        elif self.browser_type == 'firefox':
            self.browser = await self.playwright.firefox.launch(**browser_args)
        elif self.browser_type == 'webkit':
            self.browser = await self.playwright.webkit.launch(**browser_args)
        else:
            raise FetchError(f"Unsupported browser type: {self.browser_type}")
        
        # Create browser context
        context_options = {
            'viewport': {
                'width': self.viewport_width,
                'height': self.viewport_height
            },
            'user_agent': self.user_agent,
            'extra_http_headers': self.headers,
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Set up resource blocking if configured
        if self.block_resources:
            await self.context.route("**/*", self._handle_route)
        
        logger.info(f"Playwright browser initialized: {self.browser_type}")
    
    async def _handle_route(self, route, request):
        """Handle resource routing to block unnecessary resources."""
        if request.resource_type in self.block_resources:
            await route.abort()
        else:
            await route.continue_()
    
    def cleanup(self) -> None:
        """Cleanup Playwright resources."""
        if self.playwright:
            asyncio.run(self._async_cleanup())
    
    async def _async_cleanup(self) -> None:
        """Async cleanup of Playwright resources."""
        if self.context:
            await self.context.close()
            self.context = None
        
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        logger.info("Playwright browser cleaned up")
    
    def get(self, url: str, render: bool = True, **kwargs) -> str:
        """Fetch HTML content from a URL with JavaScript rendering.
        
        Args:
            url: The URL to fetch
            render: Whether to render JavaScript (always True for PlaywrightFetcher)
            **kwargs: Additional options
            
        Returns:
            HTML content as string
            
        Raises:
            FetchError: If fetching fails
        """
        self.ensure_initialized()
        self._validate_url(url)
        
        return asyncio.run(self._async_get(url, **kwargs))
    
    async def _async_get(self, url: str, **kwargs) -> str:
        """Async implementation of get method."""
        if not self.context:
            raise FetchError("Playwright not initialized")
        
        page = None
        try:
            start_time = time.time()
            
            # Create new page
            page = await self.context.new_page()
            
            # Set page timeout
            page.set_default_timeout(self.page_load_timeout)
            
            # Navigate to page
            await page.goto(url, wait_until='networkidle', timeout=self.page_load_timeout)
            
            # Wait for specific selector if configured
            if self.wait_for_selector:
                await page.wait_for_selector(self.wait_for_selector, timeout=self.network_idle_timeout)
            
            # Additional wait for network idle
            await page.wait_for_load_state('networkidle', timeout=self.network_idle_timeout)
            
            # Get page content
            content = await page.content()
            
            elapsed_time = time.time() - start_time
            logger.info(f"Playwright fetched {len(content)} chars from {url} in {elapsed_time:.2f}s")
            
            return content
        
        except Exception as e:
            raise FetchError(f"Playwright fetch failed for {url}: {e}")
        
        finally:
            if page:
                await page.close()
    
    def get_with_metadata(self, url: str, render: bool = True, **kwargs) -> Dict[str, Union[str, int, float]]:
        """Fetch content with detailed metadata using Playwright.
        
        Args:
            url: The URL to fetch
            render: Whether to render JavaScript (always True for PlaywrightFetcher)
            **kwargs: Additional options
            
        Returns:
            Dictionary with content and metadata
        """
        self.ensure_initialized()
        self._validate_url(url)
        
        return asyncio.run(self._async_get_with_metadata(url, **kwargs))
    
    async def _async_get_with_metadata(self, url: str, **kwargs) -> Dict[str, Union[str, int, float]]:
        """Async implementation of get_with_metadata method."""
        if not self.context:
            raise FetchError("Playwright not initialized")
        
        page = None
        try:
            start_time = time.time()
            
            # Create new page
            page = await self.context.new_page()
            page.set_default_timeout(self.page_load_timeout)
            
            # Track network requests
            requests_count = 0
            failed_requests = 0
            
            def track_request(request):
                nonlocal requests_count
                requests_count += 1
            
            def track_response(response):
                nonlocal failed_requests
                if response.status >= 400:
                    failed_requests += 1
            
            page.on('request', track_request)
            page.on('response', track_response)
            
            # Navigate and wait
            response = await page.goto(url, wait_until='networkidle', timeout=self.page_load_timeout)
            
            if self.wait_for_selector:
                await page.wait_for_selector(self.wait_for_selector, timeout=self.network_idle_timeout)
            
            await page.wait_for_load_state('networkidle', timeout=self.network_idle_timeout)
            
            # Get content and metadata
            content = await page.content()
            title = await page.title()
            final_url = page.url
            
            elapsed_time = time.time() - start_time
            
            # Prepare metadata
            metadata = {
                'content': content,
                'status_code': response.status if response else 0,
                'response_time_seconds': elapsed_time,
                'content_type': 'text/html',
                'content_encoding': 'utf-8',
                'content_length': len(content),
                'url': url,
                'final_url': final_url,
                'title': title,
                'requests_count': requests_count,
                'failed_requests': failed_requests,
                'browser_type': self.browser_type,
                'viewport_size': f"{self.viewport_width}x{self.viewport_height}",
                'javascript_rendered': True,
            }
            
            # Add content metrics
            content_metrics = self._calculate_content_metrics(content, elapsed_time)
            metadata.update(content_metrics)
            
            logger.info(f"Playwright fetched {metadata['content_length']} chars from {url} "
                       f"in {elapsed_time:.2f}s (status: {metadata['status_code']}, "
                       f"requests: {requests_count}, failed: {failed_requests})")
            
            return metadata
        
        except Exception as e:
            raise FetchError(f"Playwright fetch with metadata failed for {url}: {e}")
        
        finally:
            if page:
                await page.close()
    
    def get_screenshot(self, url: str, output_path: str, **kwargs) -> str:
        """Take a screenshot of the page.
        
        Args:
            url: The URL to screenshot
            output_path: Path to save the screenshot
            **kwargs: Additional screenshot options
            
        Returns:
            Path to the saved screenshot
        """
        self.ensure_initialized()
        self._validate_url(url)
        
        return asyncio.run(self._async_get_screenshot(url, output_path, **kwargs))
    
    async def _async_get_screenshot(self, url: str, output_path: str, **kwargs) -> str:
        """Async implementation of screenshot method."""
        if not self.context:
            raise FetchError("Playwright not initialized")
        
        page = None
        try:
            page = await self.context.new_page()
            page.set_default_timeout(self.page_load_timeout)
            
            await page.goto(url, wait_until='networkidle', timeout=self.page_load_timeout)
            
            if self.wait_for_selector:
                await page.wait_for_selector(self.wait_for_selector, timeout=self.network_idle_timeout)
            
            await page.wait_for_load_state('networkidle', timeout=self.network_idle_timeout)
            
            # Take screenshot
            screenshot_options = {
                'path': output_path,
                'full_page': True,
                **kwargs
            }
            
            await page.screenshot(**screenshot_options)
            logger.info(f"Screenshot saved: {output_path}")
            
            return output_path
        
        except Exception as e:
            raise FetchError(f"Screenshot failed for {url}: {e}")
        
        finally:
            if page:
                await page.close()

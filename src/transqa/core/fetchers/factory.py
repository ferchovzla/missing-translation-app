"""Factory for creating appropriate fetcher instances."""

import logging
from typing import Dict, Optional

from transqa.core.fetchers.base import BaseFetcher
from transqa.core.fetchers.requests_fetcher import RequestsFetcher
from transqa.core.interfaces import ConfigurationError

logger = logging.getLogger(__name__)

# Lazy import to avoid import errors when Playwright is not available
def _get_playwright_fetcher():
    """Lazy import of PlaywrightFetcher to handle optional dependency."""
    try:
        from transqa.core.fetchers.playwright_fetcher import PlaywrightFetcher
        return PlaywrightFetcher
    except ImportError:
        return None


class FetcherFactory:
    """Factory for creating appropriate fetcher instances based on requirements."""
    
    @staticmethod
    def create_fetcher(
        render_js: bool = False,
        fetcher_type: Optional[str] = None,
        config: Optional[dict] = None
    ) -> BaseFetcher:
        """Create appropriate fetcher instance.
        
        Args:
            render_js: Whether JavaScript rendering is required
            fetcher_type: Specific fetcher type ('requests' or 'playwright')
            config: Configuration dictionary
            
        Returns:
            Configured fetcher instance
            
        Raises:
            ConfigurationError: If requested fetcher is not available
        """
        config = config or {}
        
        # Determine fetcher type based on requirements
        if fetcher_type:
            # Explicit fetcher type requested
            if fetcher_type == 'requests':
                if render_js:
                    logger.warning("JavaScript rendering requested with requests fetcher - this will be ignored")
                return RequestsFetcher(config)
            
            elif fetcher_type == 'playwright':
                PlaywrightFetcher = _get_playwright_fetcher()
                if PlaywrightFetcher is None:
                    raise ConfigurationError(
                        "Playwright fetcher requested but not available. "
                        "Install with: pip install transqa[render]"
                    )
                return PlaywrightFetcher(config)
            
            else:
                raise ConfigurationError(f"Unknown fetcher type: {fetcher_type}")
        
        else:
            # Auto-select fetcher based on requirements
            if render_js:
                # JavaScript rendering required - try Playwright first
                PlaywrightFetcher = _get_playwright_fetcher()
                if PlaywrightFetcher is not None:
                    logger.info("Creating Playwright fetcher for JavaScript rendering")
                    return PlaywrightFetcher(config)
                else:
                    logger.warning(
                        "JavaScript rendering requested but Playwright not available. "
                        "Falling back to requests fetcher. "
                        "Install Playwright with: pip install transqa[render]"
                    )
                    return RequestsFetcher(config)
            else:
                # Static content - use requests fetcher
                logger.info("Creating requests fetcher for static content")
                return RequestsFetcher(config)
    
    @staticmethod
    def create_from_config(app_config) -> BaseFetcher:
        """Create fetcher from TransQA configuration object.
        
        Args:
            app_config: TransQAConfig instance
            
        Returns:
            Configured fetcher instance
        """
        fetcher_config = {
            'timeout': app_config.fetcher.timeout,
            'max_retries': app_config.fetcher.max_retries,
            'user_agent': app_config.fetcher.user_agent,
            'headers': app_config.fetcher.headers,
            'page_load_timeout': app_config.fetcher.page_load_timeout,
            'network_idle_timeout': app_config.fetcher.network_idle_timeout,
            'viewport_width': app_config.fetcher.viewport_width,
            'viewport_height': app_config.fetcher.viewport_height,
        }
        
        return FetcherFactory.create_fetcher(
            render_js=app_config.target.render_js,
            config=fetcher_config
        )
    
    @staticmethod
    def get_available_fetchers() -> Dict[str, bool]:
        """Get information about available fetchers.
        
        Returns:
            Dictionary mapping fetcher names to availability status
        """
        PlaywrightFetcher = _get_playwright_fetcher()
        
        return {
            'requests': True,  # Always available
            'playwright': PlaywrightFetcher is not None,
        }
    
    @staticmethod
    def check_dependencies(verbose: bool = False) -> Dict[str, Dict[str, any]]:
        """Check fetcher dependencies and capabilities.
        
        Args:
            verbose: Whether to include detailed information
            
        Returns:
            Dictionary with dependency information
        """
        results = {}
        
        # Check requests fetcher
        try:
            import requests
            results['requests'] = {
                'available': True,
                'version': requests.__version__,
                'capabilities': ['static_html', 'http_headers', 'redirects', 'ssl'],
                'limitations': ['no_javascript', 'no_dynamic_content']
            }
        except ImportError as e:
            results['requests'] = {
                'available': False,
                'error': str(e),
                'install_command': 'pip install requests'
            }
        
        # Check Playwright fetcher
        try:
            from playwright.async_api import __version__ as playwright_version
            results['playwright'] = {
                'available': True,
                'version': playwright_version,
                'capabilities': [
                    'javascript_rendering', 
                    'dynamic_content', 
                    'screenshots', 
                    'network_interception',
                    'multiple_browsers'
                ],
                'limitations': ['higher_resource_usage', 'slower_startup']
            }
            
            # Check browser installations if verbose
            if verbose:
                try:
                    import subprocess
                    result = subprocess.run(['playwright', 'list'], 
                                          capture_output=True, text=True, timeout=10)
                    results['playwright']['browsers'] = result.stdout
                except Exception as e:
                    results['playwright']['browsers_check_error'] = str(e)
            
        except ImportError as e:
            results['playwright'] = {
                'available': False,
                'error': str(e),
                'install_command': 'pip install playwright && playwright install chromium'
            }
        
        return results
    
    @staticmethod
    def recommend_fetcher(url: str, requirements: Optional[Dict[str, any]] = None) -> str:
        """Recommend appropriate fetcher for a given URL and requirements.
        
        Args:
            url: The URL to analyze
            requirements: Dictionary of requirements (render_js, take_screenshot, etc.)
            
        Returns:
            Recommended fetcher name
        """
        requirements = requirements or {}
        
        # Check explicit JavaScript requirement
        if requirements.get('render_js', False):
            return 'playwright'
        
        # Check for screenshot requirement
        if requirements.get('take_screenshot', False):
            return 'playwright'
        
        # Check URL patterns that typically require JavaScript
        js_indicators = [
            'spa.', 'app.', 'dashboard.', 'admin.',
            'react', 'vue', 'angular', 'ember',
            '.js', 'client-side', 'frontend'
        ]
        
        url_lower = url.lower()
        if any(indicator in url_lower for indicator in js_indicators):
            logger.info(f"URL {url} appears to be a JavaScript application - recommending Playwright")
            return 'playwright'
        
        # Default to requests for static content
        return 'requests'

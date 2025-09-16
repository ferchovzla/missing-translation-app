"""Factory for creating appropriate extractor instances."""

import logging
from typing import Dict, Optional

from transqa.core.extractors.base import BaseExtractor
from transqa.core.extractors.html_extractor import HTMLExtractor
from transqa.core.interfaces import ConfigurationError

logger = logging.getLogger(__name__)


class ExtractorFactory:
    """Factory for creating appropriate extractor instances."""
    
    @staticmethod
    def create_extractor(
        extractor_type: str = "html",
        config: Optional[dict] = None
    ) -> BaseExtractor:
        """Create appropriate extractor instance.
        
        Args:
            extractor_type: Type of extractor ('html' is the only option currently)
            config: Configuration dictionary
            
        Returns:
            Configured extractor instance
            
        Raises:
            ConfigurationError: If requested extractor is not available
        """
        config = config or {}
        
        if extractor_type == 'html':
            return HTMLExtractor(config)
        else:
            raise ConfigurationError(f"Unknown extractor type: {extractor_type}")
    
    @staticmethod
    def create_from_config(app_config) -> BaseExtractor:
        """Create extractor from TransQA configuration object.
        
        Args:
            app_config: TransQAConfig instance
            
        Returns:
            Configured extractor instance
        """
        # Convert rules config to dictionary and add extractor-specific settings  
        rules_dict = app_config.rules.model_dump()
        extractor_config = {
            'ignore_selectors': rules_dict.get('ignore_selectors', []),
            'min_text_length': rules_dict.get('min_text_length', 10),
            'extract_metadata': True,
            'extract_links': False,
            'preserve_formatting': False,
            'generate_xpath': True,
            'include_attributes': True,
            'use_trafilatura': True,
            'trafilatura_favor_precision': True,
            'trafilatura_include_comments': False,
            'trafilatura_include_tables': True,
            'parser': 'html.parser'
        }
        
        return ExtractorFactory.create_extractor('html', extractor_config)
    
    @staticmethod
    def get_available_extractors() -> Dict[str, bool]:
        """Get information about available extractors.
        
        Returns:
            Dictionary mapping extractor names to availability status
        """
        try:
            import trafilatura
            trafilatura_available = True
        except ImportError:
            trafilatura_available = False
        
        return {
            'html': True,  # Always available (uses BeautifulSoup)
            'html_with_trafilatura': trafilatura_available,
        }
    
    @staticmethod
    def check_dependencies(verbose: bool = False) -> Dict[str, Dict[str, any]]:
        """Check extractor dependencies and capabilities.
        
        Args:
            verbose: Whether to include detailed information
            
        Returns:
            Dictionary with dependency information
        """
        results = {}
        
        # Check BeautifulSoup (required for HTML extractor)
        try:
            from bs4 import BeautifulSoup
            import bs4
            results['beautifulsoup4'] = {
                'available': True,
                'version': bs4.__version__,
                'capabilities': ['html_parsing', 'css_selectors', 'xpath_generation'],
                'parsers': ExtractorFactory._get_available_parsers()
            }
        except ImportError as e:
            results['beautifulsoup4'] = {
                'available': False,
                'error': str(e),
                'install_command': 'pip install beautifulsoup4'
            }
        
        # Check Trafilatura (optional for better content extraction)
        try:
            import trafilatura
            results['trafilatura'] = {
                'available': True,
                'version': trafilatura.__version__,
                'capabilities': [
                    'main_content_extraction',
                    'boilerplate_removal', 
                    'precision_extraction',
                    'table_extraction',
                    'comment_extraction'
                ],
                'limitations': ['requires_network_for_some_features']
            }
        except ImportError as e:
            results['trafilatura'] = {
                'available': False,
                'error': str(e),
                'install_command': 'pip install trafilatura'
            }
        
        # Check lxml (optional parser, faster than html.parser)
        try:
            import lxml
            results['lxml'] = {
                'available': True,
                'version': lxml.__version__ if hasattr(lxml, '__version__') else 'unknown',
                'capabilities': ['fast_parsing', 'xml_support', 'xpath_support']
            }
        except ImportError as e:
            results['lxml'] = {
                'available': False,
                'error': str(e),
                'install_command': 'pip install lxml'
            }
        
        return results
    
    @staticmethod
    def _get_available_parsers() -> list:
        """Get list of available BeautifulSoup parsers."""
        parsers = ['html.parser']  # Always available
        
        try:
            import lxml
            parsers.extend(['lxml', 'lxml-xml'])
        except ImportError:
            pass
        
        try:
            import html5lib
            parsers.append('html5lib')
        except ImportError:
            pass
        
        return parsers
    
    @staticmethod
    def recommend_config(html_size: int, performance_priority: bool = False) -> dict:
        """Recommend extractor configuration based on content size and requirements.
        
        Args:
            html_size: Size of HTML content in bytes
            performance_priority: Whether to prioritize performance over precision
            
        Returns:
            Recommended configuration dictionary
        """
        config = {
            'extract_metadata': True,
            'extract_links': False,
            'preserve_formatting': False,
            'generate_xpath': True,
            'include_attributes': True,
            'min_text_length': 10,
        }
        
        # Large content - optimize for performance
        if html_size > 1_000_000 or performance_priority:  # 1MB
            config.update({
                'use_trafilatura': False,  # BeautifulSoup only for speed
                'parser': 'lxml' if 'lxml' in ExtractorFactory._get_available_parsers() else 'html.parser',
                'generate_xpath': False,  # Skip XPath generation for speed
                'include_attributes': False,
                'min_text_length': 20,  # Higher threshold to reduce blocks
            })
            logger.info("Large content detected - using performance-optimized configuration")
        
        # Medium content - balanced approach  
        elif html_size > 100_000:  # 100KB
            config.update({
                'use_trafilatura': True,
                'trafilatura_favor_precision': False,  # Favor recall for medium content
                'parser': 'lxml' if 'lxml' in ExtractorFactory._get_available_parsers() else 'html.parser',
                'min_text_length': 15,
            })
            logger.info("Medium content detected - using balanced configuration")
        
        # Small content - precision-focused
        else:
            config.update({
                'use_trafilatura': True,
                'trafilatura_favor_precision': True,
                'trafilatura_include_comments': False,
                'trafilatura_include_tables': True,
                'parser': 'html.parser',  # Most compatible
                'min_text_length': 10,
            })
            logger.info("Small content detected - using precision-focused configuration")
        
        return config

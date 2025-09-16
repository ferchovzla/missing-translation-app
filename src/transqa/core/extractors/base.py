"""Base extractor implementation."""

import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from transqa.core.interfaces import BaseAnalyzer, ExtractionError, ExtractionResult, TextBlock

logger = logging.getLogger(__name__)


class BaseExtractor(BaseAnalyzer, ABC):
    """Base class for text extractors."""
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize the extractor with configuration."""
        super().__init__(config)
        self.config = config or {}
        
        # Common configuration
        self.ignore_selectors = self.config.get('ignore_selectors', [
            'script', 'style', 'noscript', 'meta', 'link', 'head',
            '.visually-hidden', '.sr-only', '[aria-hidden="true"]',
            '[style*="display: none"]', '[style*="visibility: hidden"]'
        ])
        
        self.extract_metadata = self.config.get('extract_metadata', True)
        self.extract_links = self.config.get('extract_links', False)
        self.preserve_formatting = self.config.get('preserve_formatting', False)
        self.min_text_length = self.config.get('min_text_length', 10)
        
        # XPath generation settings
        self.generate_xpath = self.config.get('generate_xpath', True)
        self.include_attributes = self.config.get('include_attributes', True)
    
    def initialize(self) -> None:
        """Initialize the extractor."""
        # Compile selector patterns for better performance
        self._compiled_selectors = []
        for selector in self.ignore_selectors:
            try:
                # Convert CSS selector to regex for basic patterns
                if selector.startswith('.'):
                    # Class selector
                    class_pattern = re.compile(rf'\b{re.escape(selector[1:])}\b')
                    self._compiled_selectors.append(('class', class_pattern))
                elif selector.startswith('#'):
                    # ID selector
                    id_pattern = re.compile(rf'^{re.escape(selector[1:])}$')
                    self._compiled_selectors.append(('id', id_pattern))
                elif selector.startswith('[') and selector.endswith(']'):
                    # Attribute selector - store as is for BeautifulSoup
                    self._compiled_selectors.append(('attr', selector))
                else:
                    # Tag selector
                    self._compiled_selectors.append(('tag', selector))
            except re.error as e:
                logger.warning(f"Invalid selector pattern '{selector}': {e}")
        
        logger.info(f"Extractor initialized with {len(self._compiled_selectors)} ignore selectors")
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self._compiled_selectors = []
    
    @abstractmethod
    def extract_blocks(self, html: str, **kwargs) -> ExtractionResult:
        """Extract text blocks from HTML."""
        pass
    
    @abstractmethod
    def extract_raw_text(self, html: str, **kwargs) -> str:
        """Extract raw text without structure."""
        pass
    
    def _should_ignore_element(self, element: Tag) -> bool:
        """Check if an element should be ignored based on selectors."""
        if not isinstance(element, Tag):
            return False
        
        # Check tag name
        tag_name = element.name.lower()
        
        # Check against compiled selectors
        for selector_type, pattern in self._compiled_selectors:
            if selector_type == 'tag':
                if tag_name == pattern.lower():
                    return True
            
            elif selector_type == 'class':
                classes = element.get('class', [])
                if isinstance(classes, str):
                    classes = classes.split()
                for cls in classes:
                    if pattern.search(cls):
                        return True
            
            elif selector_type == 'id':
                element_id = element.get('id', '')
                if pattern.search(element_id):
                    return True
            
            elif selector_type == 'attr':
                # Use BeautifulSoup's CSS selector for attribute patterns
                try:
                    if element.select_one(pattern):
                        return True
                except Exception:
                    # Invalid selector, skip
                    pass
        
        # Check style attribute for visibility
        style = element.get('style', '')
        if style:
            if 'display:none' in style.replace(' ', '') or \
               'display: none' in style or \
               'visibility:hidden' in style.replace(' ', '') or \
               'visibility: hidden' in style:
                return True
        
        # Check aria-hidden
        if element.get('aria-hidden') == 'true':
            return True
        
        return False
    
    def _extract_metadata_from_html(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract metadata from HTML document."""
        metadata = {
            'title': None,
            'meta_description': None,
            'declared_language': None,
        }
        
        if not self.extract_metadata:
            return metadata
        
        try:
            # Title
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text().strip()
            
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                metadata['meta_description'] = meta_desc.get('content', '').strip()
            
            # Language from html tag
            html_tag = soup.find('html')
            if html_tag:
                metadata['declared_language'] = html_tag.get('lang', '').strip()
            
        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")
        
        return metadata
    
    def _generate_xpath(self, element: Tag) -> str:
        """Generate XPath for an element."""
        if not self.generate_xpath or not isinstance(element, Tag):
            return "/"
        
        try:
            path_parts = []
            current = element
            
            while current and current.parent:
                tag_name = current.name
                
                # Get position among siblings of the same tag
                siblings = [s for s in current.parent.children 
                           if isinstance(s, Tag) and s.name == tag_name]
                
                if len(siblings) > 1:
                    try:
                        position = siblings.index(current) + 1
                        path_part = f"{tag_name}[{position}]"
                    except ValueError:
                        path_part = tag_name
                else:
                    path_part = tag_name
                
                # Add class or id information if configured
                if self.include_attributes:
                    if current.get('id'):
                        path_part = f"{tag_name}[@id='{current.get('id')}']"
                    elif current.get('class'):
                        classes = ' '.join(current.get('class'))
                        path_part = f"{tag_name}[@class='{classes}']"
                
                path_parts.append(path_part)
                current = current.parent
            
            # Build XPath from root
            if path_parts:
                xpath = "/html/" + "/".join(reversed(path_parts))
            else:
                xpath = "/html"
            
            return xpath
        
        except Exception as e:
            logger.debug(f"Error generating XPath: {e}")
            return "/"
    
    def _get_element_attributes(self, element: Tag) -> Dict[str, str]:
        """Extract relevant attributes from an element."""
        if not isinstance(element, Tag) or not self.include_attributes:
            return {}
        
        # Only include certain attributes that might be relevant for analysis
        relevant_attrs = ['id', 'class', 'role', 'lang', 'data-*']
        attributes = {}
        
        for attr, value in element.attrs.items():
            if attr in ['id', 'class', 'role', 'lang'] or attr.startswith('data-'):
                if isinstance(value, list):
                    attributes[attr] = ' '.join(value)
                else:
                    attributes[attr] = str(value)
        
        return attributes
    
    def _is_visible_text(self, text: str) -> bool:
        """Check if text content is meaningful and visible."""
        if not text:
            return False
        
        # Remove whitespace and check length
        cleaned = text.strip()
        if len(cleaned) < self.min_text_length:
            return False
        
        # Skip if it's all whitespace or special characters
        if not re.search(r'[a-zA-Z0-9\u00C0-\u017F\u0100-\u024F]', cleaned):
            return False
        
        return True
    
    def _normalize_text(self, text: str) -> str:
        """Normalize extracted text."""
        if not text:
            return ""
        
        # Replace multiple whitespace with single space
        normalized = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        normalized = normalized.strip()
        
        return normalized
    
    def _calculate_text_position(self, text: str, full_text: str, start_offset: int = 0) -> tuple:
        """Calculate text position within the full extracted text."""
        try:
            start_pos = full_text.find(text, start_offset)
            if start_pos == -1:
                # Text not found, use provided offset
                return start_offset, start_offset + len(text)
            
            end_pos = start_pos + len(text)
            return start_pos, end_pos
        
        except Exception:
            return start_offset, start_offset + len(text)

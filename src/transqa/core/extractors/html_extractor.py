"""HTML extractor using trafilatura and BeautifulSoup."""

import logging
import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from transqa.core.extractors.base import BaseExtractor
from transqa.core.interfaces import ExtractionError, ExtractionResult, TextBlock

logger = logging.getLogger(__name__)

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    trafilatura = None


class HTMLExtractor(BaseExtractor):
    """HTML extractor using trafilatura for main content and BeautifulSoup for detailed parsing."""
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize HTML extractor."""
        super().__init__(config)
        
        # Trafilatura configuration
        self.use_trafilatura = self.config.get('use_trafilatura', True) and TRAFILATURA_AVAILABLE
        self.trafilatura_favor_precision = self.config.get('trafilatura_favor_precision', True)
        self.trafilatura_include_comments = self.config.get('trafilatura_include_comments', False)
        self.trafilatura_include_tables = self.config.get('trafilatura_include_tables', True)
        
        # BeautifulSoup configuration
        self.parser = self.config.get('parser', 'html.parser')  # lxml is faster but requires installation
        
        # Block extraction configuration
        self.content_tags = self.config.get('content_tags', [
            'p', 'div', 'span', 'article', 'section', 'main',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'li', 'td', 'th', 'blockquote', 'figcaption',
            'label', 'legend', 'option', 'button'
        ])
        
        self.heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        self.list_item_tags = ['li', 'dt', 'dd']
        self.table_tags = ['td', 'th', 'caption']
        
        if not self.use_trafilatura:
            logger.warning("Trafilatura not available. Install with: pip install trafilatura")
    
    def extract_blocks(self, html: str, **kwargs) -> ExtractionResult:
        """Extract structured text blocks from HTML.
        
        Args:
            html: HTML content to extract from
            **kwargs: Additional options
            
        Returns:
            ExtractionResult with text blocks and metadata
        """
        self.ensure_initialized()
        
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html, self.parser)
            
            # Extract metadata
            metadata = self._extract_metadata_from_html(soup)
            
            # Get main content using trafilatura if available
            main_content = None
            if self.use_trafilatura:
                try:
                    main_content = trafilatura.extract(
                        html,
                        favor_precision=self.trafilatura_favor_precision,
                        include_comments=self.trafilatura_include_comments,
                        include_tables=self.trafilatura_include_tables,
                    )
                except Exception as e:
                    logger.warning(f"Trafilatura extraction failed: {e}")
                    main_content = None
            
            # Extract text blocks using BeautifulSoup
            blocks = self._extract_text_blocks(soup, main_content)
            
            # Generate full raw text
            raw_text = "\n\n".join(block.text for block in blocks if block.text.strip())
            
            # Update offset positions based on raw text
            current_offset = 0
            for block in blocks:
                if block.text.strip():
                    # Find this block's text in the raw text
                    start_pos = raw_text.find(block.text, current_offset)
                    if start_pos != -1:
                        block.offset_start = start_pos
                        block.offset_end = start_pos + len(block.text)
                        current_offset = block.offset_end + 2  # Account for \n\n
                    else:
                        block.offset_start = current_offset
                        block.offset_end = current_offset + len(block.text)
                        current_offset = block.offset_end
            
            return ExtractionResult(
                blocks=blocks,
                raw_text=raw_text,
                title=metadata['title'],
                meta_description=metadata['meta_description'],
                declared_language=metadata['declared_language'],
                extraction_method='html_extractor',
                success=True
            )
        
        except Exception as e:
            logger.error(f"HTML extraction failed: {e}")
            return ExtractionResult(
                blocks=[],
                raw_text="",
                extraction_method='html_extractor',
                success=False,
                error_message=str(e)
            )
    
    def extract_raw_text(self, html: str, **kwargs) -> str:
        """Extract raw text without structure.
        
        Args:
            html: HTML content to extract from
            **kwargs: Additional options
            
        Returns:
            Plain text content
        """
        if self.use_trafilatura:
            try:
                text = trafilatura.extract(
                    html,
                    favor_precision=self.trafilatura_favor_precision,
                    include_comments=self.trafilatura_include_comments,
                    include_tables=self.trafilatura_include_tables,
                )
                if text:
                    return text
            except Exception as e:
                logger.warning(f"Trafilatura raw text extraction failed: {e}")
        
        # Fallback to BeautifulSoup
        soup = BeautifulSoup(html, self.parser)
        
        # Remove ignored elements
        for element in soup.find_all():
            if self._should_ignore_element(element):
                element.decompose()
        
        # Get text content
        text = soup.get_text(separator=' ', strip=True)
        return self._normalize_text(text)
    
    def _extract_text_blocks(self, soup: BeautifulSoup, main_content: Optional[str] = None) -> List[TextBlock]:
        """Extract structured text blocks from parsed HTML."""
        blocks = []
        processed_elements = set()
        
        # Focus on main content area if available
        content_root = soup
        if main_content:
            # Try to find elements that contain the main content
            main_text_parts = main_content.split('\n\n')[:3]  # First few paragraphs
            for part in main_text_parts:
                if len(part.strip()) > 50:  # Substantial text
                    elements = soup.find_all(string=lambda text: 
                        text and part[:50] in text.get_text() if hasattr(text, 'get_text') 
                        else part[:50] in str(text))
                    if elements:
                        # Found main content area
                        for element in elements:
                            parent = element.parent
                            while parent and parent.name not in ['article', 'main', 'div', 'section']:
                                parent = parent.parent
                            if parent:
                                content_root = parent
                                break
                        break
        
        # Extract text blocks from content elements
        for element in content_root.find_all(self.content_tags):
            if id(element) in processed_elements:
                continue
                
            if self._should_ignore_element(element):
                continue
            
            # Get direct text content (not from children)
            direct_text = self._get_direct_text_content(element)
            
            if not self._is_visible_text(direct_text):
                continue
            
            # Determine block type
            block_type = self._classify_block_type(element)
            
            # Create text block
            block = TextBlock(
                text=self._normalize_text(direct_text),
                xpath=self._generate_xpath(element),
                tag_name=element.name,
                attributes=self._get_element_attributes(element),
                is_visible=True,
                block_type=block_type,
                offset_start=0,  # Will be updated later
                offset_end=0     # Will be updated later
            )
            
            blocks.append(block)
            processed_elements.add(id(element))
            
            # Mark children as processed to avoid duplication
            for child in element.find_all():
                processed_elements.add(id(child))
        
        return blocks
    
    def _get_direct_text_content(self, element: Tag) -> str:
        """Get direct text content from element, handling nested structure carefully."""
        if not isinstance(element, Tag):
            return ""
        
        texts = []
        
        def extract_text_recursive(el, depth=0):
            """Recursively extract text while respecting structure."""
            if depth > 10:  # Prevent deep recursion
                return
            
            for child in el.children:
                if isinstance(child, NavigableString):
                    text = str(child).strip()
                    if text:
                        texts.append(text)
                elif isinstance(child, Tag):
                    if self._should_ignore_element(child):
                        continue
                    
                    # For inline elements, continue extracting
                    if child.name in ['span', 'a', 'strong', 'em', 'b', 'i', 'u', 'small', 'sup', 'sub']:
                        extract_text_recursive(child, depth + 1)
                    # For block elements, get their text but don't go deeper
                    # (they will be processed separately)
                    elif child.name in self.content_tags:
                        child_text = child.get_text(strip=True)
                        if child_text and len(child_text) > self.min_text_length:
                            texts.append(child_text)
                    else:
                        # Other elements, extract text normally
                        extract_text_recursive(child, depth + 1)
        
        extract_text_recursive(element)
        
        # Join texts and clean up
        result = ' '.join(texts)
        return self._normalize_text(result)
    
    def _classify_block_type(self, element: Tag) -> str:
        """Classify the type of text block based on HTML element."""
        if not isinstance(element, Tag):
            return "text"
        
        tag_name = element.name.lower()
        
        if tag_name in self.heading_tags:
            return "heading"
        elif tag_name in self.list_item_tags:
            return "list_item"
        elif tag_name in self.table_tags:
            return "table_cell"
        elif tag_name in ['blockquote', 'q']:
            return "quote"
        elif tag_name in ['figcaption', 'caption']:
            return "caption"
        elif tag_name in ['label', 'legend']:
            return "label"
        elif tag_name in ['button', 'input']:
            return "interactive"
        elif tag_name == 'p':
            return "paragraph"
        elif tag_name in ['article', 'section', 'main']:
            return "section"
        else:
            return "text"
    
    def get_links(self, html: str) -> List[Dict[str, str]]:
        """Extract all links from HTML.
        
        Args:
            html: HTML content to extract links from
            
        Returns:
            List of dictionaries with link information
        """
        soup = BeautifulSoup(html, self.parser)
        links = []
        
        for link in soup.find_all('a', href=True):
            if self._should_ignore_element(link):
                continue
            
            link_text = link.get_text(strip=True)
            if not link_text:
                continue
            
            link_info = {
                'url': link['href'],
                'text': self._normalize_text(link_text),
                'title': link.get('title', ''),
                'xpath': self._generate_xpath(link),
                'attributes': self._get_element_attributes(link)
            }
            
            links.append(link_info)
        
        return links
    
    def get_images(self, html: str) -> List[Dict[str, str]]:
        """Extract image information from HTML.
        
        Args:
            html: HTML content to extract images from
            
        Returns:
            List of dictionaries with image information
        """
        soup = BeautifulSoup(html, self.parser)
        images = []
        
        for img in soup.find_all('img'):
            if self._should_ignore_element(img):
                continue
            
            alt_text = img.get('alt', '').strip()
            if not alt_text:
                continue
            
            img_info = {
                'src': img.get('src', ''),
                'alt': self._normalize_text(alt_text),
                'title': img.get('title', ''),
                'xpath': self._generate_xpath(img),
                'attributes': self._get_element_attributes(img)
            }
            
            images.append(img_info)
        
        return images

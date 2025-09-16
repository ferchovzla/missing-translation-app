"""Core interfaces and protocols for TransQA components."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Protocol, Tuple, Union

from pydantic import BaseModel

from transqa.models.issue import Issue


class TextBlock(BaseModel):
    """Represents a block of text with metadata."""
    
    text: str
    xpath: str
    tag_name: Optional[str] = None
    attributes: Dict[str, str] = {}
    is_visible: bool = True
    block_type: str = "text"  # text, heading, list_item, etc.
    offset_start: int = 0
    offset_end: int = 0


class LanguageDetectionResult(BaseModel):
    """Result of language detection on text."""
    
    detected_language: str
    confidence: float
    alternative_languages: List[Tuple[str, float]] = []
    method: str = "unknown"  # fasttext, langid, spacy, etc.


class ExtractionResult(BaseModel):
    """Result of text extraction from HTML."""
    
    blocks: List[TextBlock]
    raw_text: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    declared_language: Optional[str] = None  # from HTML lang attribute
    extraction_method: str = "trafilatura"
    success: bool = True
    error_message: Optional[str] = None


class Fetcher(Protocol):
    """Protocol for fetching web content."""
    
    def get(self, url: str, render: bool = False, **kwargs) -> str:
        """Fetch HTML content from a URL.
        
        Args:
            url: The URL to fetch
            render: Whether to render JavaScript
            **kwargs: Additional options (headers, timeout, etc.)
            
        Returns:
            HTML content as string
            
        Raises:
            FetchError: If fetching fails
        """
        ...
    
    def get_with_metadata(self, url: str, render: bool = False, **kwargs) -> Dict[str, Union[str, int, float]]:
        """Fetch content with additional metadata.
        
        Returns:
            Dictionary with 'content', 'status_code', 'headers', 'load_time', etc.
        """
        ...


class Extractor(Protocol):
    """Protocol for extracting text from HTML."""
    
    def extract_blocks(self, html: str, **kwargs) -> ExtractionResult:
        """Extract text blocks from HTML.
        
        Args:
            html: HTML content to extract from
            **kwargs: Additional options (ignore_selectors, etc.)
            
        Returns:
            ExtractionResult with text blocks and metadata
        """
        ...
    
    def extract_raw_text(self, html: str, **kwargs) -> str:
        """Extract raw text without structure.
        
        Args:
            html: HTML content to extract from
            **kwargs: Additional options
            
        Returns:
            Plain text content
        """
        ...


class LanguageDetector(Protocol):
    """Protocol for detecting text language."""
    
    def detect_block(self, text: str) -> LanguageDetectionResult:
        """Detect language of a text block.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language detection result
        """
        ...
    
    def detect_tokens(self, text: str, sample_size: Optional[int] = None) -> List[Tuple[str, LanguageDetectionResult]]:
        """Detect language of individual tokens.
        
        Args:
            text: Text to analyze
            sample_size: Maximum number of tokens to sample (None for all)
            
        Returns:
            List of (token, detection_result) tuples
        """
        ...
    
    def get_language_distribution(self, text: str) -> Dict[str, float]:
        """Get distribution of languages in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary mapping language codes to confidence percentages
        """
        ...


class Verifier(Protocol):
    """Protocol for verifying text quality and detecting issues."""
    
    def check(self, text: str, target_lang: str, context: Optional[TextBlock] = None) -> List[Issue]:
        """Check text for quality issues.
        
        Args:
            text: Text to check
            target_lang: Expected target language (es, en, nl)
            context: Optional context information
            
        Returns:
            List of detected issues
        """
        ...
    
    def check_grammar(self, text: str, target_lang: str) -> List[Issue]:
        """Check grammar issues specifically."""
        ...
    
    def check_spelling(self, text: str, target_lang: str) -> List[Issue]:
        """Check spelling issues specifically."""
        ...
    
    def check_style(self, text: str, target_lang: str) -> List[Issue]:
        """Check style issues specifically."""
        ...


class LanguageLeakDetector(Protocol):
    """Protocol for detecting language leakage."""
    
    def detect_leakage(
        self, 
        text: str, 
        target_lang: str, 
        threshold: float = 0.08,
        context: Optional[TextBlock] = None
    ) -> List[Issue]:
        """Detect language leakage in text.
        
        Args:
            text: Text to analyze
            target_lang: Expected target language
            threshold: Leakage threshold (0.0-1.0)
            context: Optional context information
            
        Returns:
            List of language leakage issues
        """
        ...


class PlaceholderValidator(Protocol):
    """Protocol for validating placeholders and special tokens."""
    
    def validate_placeholders(self, text: str, context: Optional[TextBlock] = None) -> List[Issue]:
        """Validate placeholders in text.
        
        Common placeholder patterns:
        - {variable}
        - {{handlebars}}
        - %s, %d, %f (printf style)
        - ${variable}
        - :parameter
        
        Args:
            text: Text to validate
            context: Optional context information
            
        Returns:
            List of placeholder-related issues
        """
        ...
    
    def validate_numbers_and_formats(self, text: str, target_lang: str) -> List[Issue]:
        """Validate number formats and currency symbols."""
        ...
    
    def validate_punctuation_spacing(self, text: str, target_lang: str) -> List[Issue]:
        """Validate punctuation and spacing rules."""
        ...


class WhitelistManager(Protocol):
    """Protocol for managing whitelisted terms."""
    
    def is_whitelisted(self, term: str, language: str) -> bool:
        """Check if a term is whitelisted for a language."""
        ...
    
    def load_whitelist(self, file_path: str) -> None:
        """Load whitelist from file."""
        ...
    
    def add_term(self, term: str, language: str) -> None:
        """Add a term to the whitelist."""
        ...
    
    def remove_term(self, term: str, language: str) -> None:
        """Remove a term from the whitelist."""
        ...


# Abstract base classes for common functionality

class BaseComponent(ABC):
    """Base class for TransQA components."""
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize component with configuration."""
        self.config = config or {}
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the component (load models, start services, etc.)."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup resources (close connections, stop services, etc.)."""
        pass


class BaseAnalyzer(BaseComponent):
    """Base class for text analyzers."""
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.is_initialized = False
    
    def ensure_initialized(self) -> None:
        """Ensure the analyzer is initialized."""
        if not self.is_initialized:
            self.initialize()
            self.is_initialized = True
    
    def __enter__(self):
        """Context manager entry."""
        self.ensure_initialized()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


# Exception classes

class TransQAError(Exception):
    """Base exception for TransQA."""
    pass


class FetchError(TransQAError):
    """Exception raised when fetching content fails."""
    pass


class ExtractionError(TransQAError):
    """Exception raised when text extraction fails."""
    pass


class LanguageDetectionError(TransQAError):
    """Exception raised when language detection fails."""
    pass


class VerificationError(TransQAError):
    """Exception raised when text verification fails."""
    pass


class ConfigurationError(TransQAError):
    """Exception raised when configuration is invalid."""
    pass

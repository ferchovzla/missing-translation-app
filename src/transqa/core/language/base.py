"""Base language detector implementation."""

import logging
import re
import statistics
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple

from transqa.core.interfaces import BaseAnalyzer, LanguageDetectionResult, LanguageDetectionError

logger = logging.getLogger(__name__)


class BaseLanguageDetector(BaseAnalyzer, ABC):
    """Base class for language detectors."""
    
    # Supported languages by TransQA
    SUPPORTED_LANGUAGES = {'es', 'en', 'nl'}
    
    # Common stopwords for quick language hints
    STOPWORDS = {
        'es': {'el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'una', 'las', 'los', 'del', 'al'},
        'en': {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from'},
        'nl': {'de', 'het', 'een', 'en', 'van', 'te', 'dat', 'die', 'in', 'is', 'hij', 'niet', 'zijn', 'op', 'aan', 'met', 'als', 'voor', 'had', 'er', 'maar', 'om', 'hem', 'dan', 'zou'}
    }
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize the language detector with configuration."""
        super().__init__(config)
        self.config = config or {}
        
        # Configuration
        self.min_confidence = self.config.get('min_confidence', 0.5)
        self.min_text_length = self.config.get('min_text_length', 20)
        self.max_text_length = self.config.get('max_text_length', 10000)
        self.sample_size = self.config.get('sample_size', 200)
        
        # Preprocessing settings
        self.normalize_text = self.config.get('normalize_text', True)
        self.remove_urls = self.config.get('remove_urls', True)
        self.remove_emails = self.config.get('remove_emails', True)
        self.remove_numbers = self.config.get('remove_numbers', False)
        
        # Language filtering
        self.restrict_to_supported = self.config.get('restrict_to_supported', True)
    
    @abstractmethod
    def _detect_language_impl(self, text: str) -> Tuple[str, float, List[Tuple[str, float]]]:
        """Implementation-specific language detection.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (detected_language, confidence, alternatives)
        """
        pass
    
    def detect_block(self, text: str) -> LanguageDetectionResult:
        """Detect language of a text block.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language detection result
        """
        if not text or len(text.strip()) < self.min_text_length:
            return LanguageDetectionResult(
                detected_language='unknown',
                confidence=0.0,
                method=self.__class__.__name__
            )
        
        try:
            # Preprocess text
            processed_text = self._preprocess_text(text)
            
            if not processed_text:
                return LanguageDetectionResult(
                    detected_language='unknown',
                    confidence=0.0,
                    method=self.__class__.__name__
                )
            
            # Detect language using implementation
            detected_lang, confidence, alternatives = self._detect_language_impl(processed_text)
            
            # Filter alternatives to supported languages if configured
            if self.restrict_to_supported:
                alternatives = [(lang, conf) for lang, conf in alternatives 
                               if lang in self.SUPPORTED_LANGUAGES]
                
                if detected_lang not in self.SUPPORTED_LANGUAGES and alternatives:
                    # Use best supported language
                    detected_lang, confidence = alternatives[0]
            
            # Apply confidence threshold
            if confidence < self.min_confidence:
                detected_lang = 'unknown'
                confidence = 0.0
            
            return LanguageDetectionResult(
                detected_language=detected_lang,
                confidence=confidence,
                alternative_languages=alternatives[:3],  # Top 3 alternatives
                method=self.__class__.__name__
            )
        
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return LanguageDetectionResult(
                detected_language='unknown',
                confidence=0.0,
                method=self.__class__.__name__
            )
    
    def detect_tokens(self, text: str, sample_size: Optional[int] = None) -> List[Tuple[str, LanguageDetectionResult]]:
        """Detect language of individual tokens.
        
        Args:
            text: Text to analyze
            sample_size: Maximum number of tokens to sample (None for all)
            
        Returns:
            List of (token, detection_result) tuples
        """
        sample_size = sample_size or self.sample_size
        
        # Extract alphabetic tokens
        tokens = self._extract_tokens(text)
        
        # Sample tokens if needed
        if len(tokens) > sample_size:
            import random
            tokens = random.sample(tokens, sample_size)
        
        results = []
        
        for token in tokens:
            # Skip very short tokens
            if len(token) < 3:
                continue
            
            # Detect language for this token
            detection_result = self.detect_block(token)
            results.append((token, detection_result))
        
        return results
    
    def get_language_distribution(self, text: str) -> Dict[str, float]:
        """Get distribution of languages in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary mapping language codes to confidence percentages
        """
        token_results = self.detect_tokens(text)
        
        if not token_results:
            return {'unknown': 100.0}
        
        # Count language occurrences weighted by confidence
        language_scores = {}
        total_weight = 0
        
        for token, result in token_results:
            lang = result.detected_language
            confidence = result.confidence
            
            if lang != 'unknown':
                language_scores[lang] = language_scores.get(lang, 0) + confidence
                total_weight += confidence
        
        if total_weight == 0:
            return {'unknown': 100.0}
        
        # Convert to percentages
        distribution = {}
        for lang, score in language_scores.items():
            distribution[lang] = (score / total_weight) * 100
        
        # Add unknown percentage if needed
        total_percentage = sum(distribution.values())
        if total_percentage < 100:
            distribution['unknown'] = 100 - total_percentage
        
        return distribution
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for language detection."""
        if not text:
            return ""
        
        processed = text
        
        if self.normalize_text:
            # Normalize whitespace
            processed = re.sub(r'\s+', ' ', processed)
            processed = processed.strip()
        
        if self.remove_urls:
            # Remove URLs
            processed = re.sub(r'https?://\S+', '', processed)
            processed = re.sub(r'www\.\S+', '', processed)
        
        if self.remove_emails:
            # Remove email addresses
            processed = re.sub(r'\S+@\S+\.\S+', '', processed)
        
        if self.remove_numbers:
            # Remove standalone numbers
            processed = re.sub(r'\b\d+\b', '', processed)
        
        # Remove extra whitespace after cleaning
        processed = re.sub(r'\s+', ' ', processed).strip()
        
        # Limit text length if configured
        if self.max_text_length and len(processed) > self.max_text_length:
            processed = processed[:self.max_text_length]
        
        return processed
    
    def _extract_tokens(self, text: str) -> List[str]:
        """Extract alphabetic tokens from text."""
        # Simple tokenization - extract alphabetic sequences
        tokens = re.findall(r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+', text)
        
        # Filter tokens by length and exclude very common non-words
        filtered_tokens = []
        for token in tokens:
            if len(token) >= 2:
                # Exclude tokens that are all uppercase (likely acronyms)
                if not token.isupper() or len(token) <= 3:
                    filtered_tokens.append(token.lower())
        
        return filtered_tokens
    
    def _calculate_stopword_ratio(self, text: str, language: str) -> float:
        """Calculate ratio of stopwords for a given language."""
        if language not in self.STOPWORDS:
            return 0.0
        
        tokens = self._extract_tokens(text)
        if not tokens:
            return 0.0
        
        stopwords = self.STOPWORDS[language]
        stopword_count = sum(1 for token in tokens if token.lower() in stopwords)
        
        return stopword_count / len(tokens)
    
    def _get_language_hints(self, text: str) -> Dict[str, float]:
        """Get language hints based on stopwords and character patterns."""
        hints = {}
        
        # Stopword ratios
        for lang in self.SUPPORTED_LANGUAGES:
            ratio = self._calculate_stopword_ratio(text, lang)
            if ratio > 0:
                hints[f'{lang}_stopwords'] = ratio
        
        # Character pattern hints
        text_lower = text.lower()
        
        # Spanish hints
        if re.search(r'[ñáéíóúü]', text_lower):
            hints['es_chars'] = len(re.findall(r'[ñáéíóúü]', text_lower)) / len(text)
        
        # Dutch hints  
        if re.search(r'[ëïöüÿ]', text_lower) or 'ij' in text_lower:
            hints['nl_chars'] = (len(re.findall(r'[ëïöüÿ]', text_lower)) + text_lower.count('ij')) / len(text)
        
        # English hints (lack of special characters)
        if not re.search(r'[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', text_lower):
            hints['en_ascii'] = 0.1  # Weak hint
        
        return hints
    
    def is_supported_language(self, language_code: str) -> bool:
        """Check if a language is supported by TransQA."""
        return language_code in self.SUPPORTED_LANGUAGES

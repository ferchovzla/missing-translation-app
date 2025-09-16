"""LangID-based language detector as fallback."""

import logging
from typing import List, Optional, Tuple

from transqa.core.language.base import BaseLanguageDetector
from transqa.core.interfaces import LanguageDetectionError

logger = logging.getLogger(__name__)

try:
    import langid
    LANGID_AVAILABLE = True
except ImportError:
    LANGID_AVAILABLE = False
    langid = None


class LangIDDetector(BaseLanguageDetector):
    """Language detector using langid.py library."""
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize LangID detector."""
        if not LANGID_AVAILABLE:
            raise ImportError(
                "langid.py is not installed. Install with: pip install langid-py"
            )
        
        super().__init__(config)
        
        # LangID-specific configuration
        self.restrict_languages = self.config.get('restrict_languages', True)
        self.normalize_scores = self.config.get('normalize_scores', True)
        
        # LangID instance
        self._identifier = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the langid detector."""
        super().initialize()
        
        if not self._initialized:
            self._setup_langid()
            self._initialized = True
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        super().cleanup()
        self._identifier = None
        self._initialized = False
    
    def _detect_language_impl(self, text: str) -> Tuple[str, float, List[Tuple[str, float]]]:
        """Detect language using langid.py."""
        if not self._identifier:
            raise LanguageDetectionError("LangID not initialized")
        
        try:
            # Classify text
            lang_code, confidence = self._identifier.classify(text)
            
            # langid.py only returns the top prediction, so we'll create alternatives
            # based on confidence scores if available
            alternatives = []
            
            # For langid, we can't easily get multiple predictions, so we'll use
            # our language hints to provide alternatives
            if confidence < 0.8:  # If not very confident, provide alternatives
                hints = self._get_language_hints(text)
                
                # Sort other supported languages by hints
                other_langs = [lang for lang in self.SUPPORTED_LANGUAGES if lang != lang_code]
                for other_lang in other_langs:
                    # Simple scoring based on hints
                    hint_score = hints.get(f'{other_lang}_stopwords', 0) * 0.5
                    hint_score += hints.get(f'{other_lang}_chars', 0) * 0.3
                    
                    if hint_score > 0.1:  # Only include if there's some evidence
                        alternatives.append((other_lang, min(hint_score, confidence * 0.8)))
                
                # Sort alternatives by score
                alternatives.sort(key=lambda x: x[1], reverse=True)
            
            return lang_code, confidence, alternatives[:3]  # Top 3 alternatives
        
        except Exception as e:
            logger.error(f"LangID detection error: {e}")
            return 'unknown', 0.0, []
    
    def _setup_langid(self) -> None:
        """Setup langid with our configuration."""
        try:
            # Configure langid to only detect our supported languages if requested
            if self.restrict_languages:
                # Set language filter to only our supported languages
                supported_langs = list(self.SUPPORTED_LANGUAGES)
                langid.set_languages(supported_langs)
                logger.info(f"LangID configured for languages: {supported_langs}")
            
            # Use the global langid identifier
            self._identifier = langid
            
            logger.info("LangID detector initialized successfully")
        
        except Exception as e:
            raise LanguageDetectionError(f"Failed to setup langid: {e}")
    
    def get_confidence_distribution(self, text: str) -> dict:
        """Get confidence distribution for all supported languages.
        
        This is a custom method since langid doesn't provide this directly.
        We'll use multiple approaches to estimate confidence for each language.
        """
        if not text.strip():
            return {}
        
        distribution = {}
        
        # Get primary detection
        primary_lang, primary_conf, _ = self._detect_language_impl(text)
        distribution[primary_lang] = primary_conf
        
        # For other languages, use heuristics
        hints = self._get_language_hints(text)
        
        for lang in self.SUPPORTED_LANGUAGES:
            if lang != primary_lang:
                # Estimate confidence based on stopwords and character patterns
                stopword_score = hints.get(f'{lang}_stopwords', 0)
                char_score = hints.get(f'{lang}_chars', 0)
                
                # Combine scores
                estimated_conf = (stopword_score * 0.6) + (char_score * 0.4)
                
                # Cap at 80% of primary confidence to maintain ranking
                estimated_conf = min(estimated_conf, primary_conf * 0.8)
                
                if estimated_conf > 0.1:  # Only include meaningful scores
                    distribution[lang] = estimated_conf
        
        return distribution
    
    @staticmethod
    def check_availability() -> dict:
        """Check if langid.py is available."""
        result = {
            'available': LANGID_AVAILABLE,
        }
        
        if not LANGID_AVAILABLE:
            result['error'] = 'langid.py not installed'
            result['install_command'] = 'pip install langid-py'
            return result
        
        try:
            # Test basic functionality
            test_result = langid.classify("Hello world")
            result['test_successful'] = True
            result['test_result'] = test_result
        except Exception as e:
            result['test_successful'] = False
            result['test_error'] = str(e)
        
        return result
    
    def get_supported_languages(self) -> List[str]:
        """Get list of languages supported by langid."""
        try:
            # langid supports many languages, but we return our filtered set
            if self.restrict_languages:
                return list(self.SUPPORTED_LANGUAGES)
            else:
                # langid supports a fixed set of languages
                # These are some of the common ones, including our supported set
                return [
                    'af', 'ar', 'bg', 'bn', 'ca', 'cs', 'cy', 'da', 'de', 'el',
                    'en', 'es', 'et', 'fa', 'fi', 'fr', 'gu', 'he', 'hi', 'hr',
                    'hu', 'id', 'it', 'ja', 'kn', 'ko', 'lt', 'lv', 'mk', 'ml',
                    'mr', 'ne', 'nl', 'no', 'pa', 'pl', 'pt', 'ro', 'ru', 'sk',
                    'sl', 'so', 'sq', 'sv', 'sw', 'ta', 'te', 'th', 'tl', 'tr',
                    'uk', 'ur', 'vi', 'zh-cn', 'zh-tw'
                ]
        except Exception:
            return list(self.SUPPORTED_LANGUAGES)
    
    def get_model_info(self) -> dict:
        """Get information about langid."""
        info = {
            'detector_type': 'langid.py',
            'initialized': self._initialized,
            'supported_languages': len(self.get_supported_languages()),
            'restrict_languages': self.restrict_languages,
        }
        
        if self._initialized:
            info['config'] = {
                'min_confidence': self.min_confidence,
                'normalize_scores': self.normalize_scores,
            }
        
        return info
    
    def batch_detect(self, texts: List[str]) -> List[Tuple[str, float]]:
        """Detect language for multiple texts efficiently.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of (language, confidence) tuples
        """
        results = []
        
        for text in texts:
            try:
                detection = self.detect_block(text)
                results.append((detection.detected_language, detection.confidence))
            except Exception as e:
                logger.warning(f"Batch detection failed for text: {e}")
                results.append(('unknown', 0.0))
        
        return results

"""Factory for creating language detector instances."""

import logging
from typing import Dict, List, Optional

from transqa.core.language.base import BaseLanguageDetector
from transqa.core.language.composite_detector import CompositeLanguageDetector
from transqa.core.interfaces import ConfigurationError

logger = logging.getLogger(__name__)

# Lazy imports to handle optional dependencies
def _get_fasttext_detector():
    """Lazy import of FastTextDetector to handle optional dependency."""
    try:
        from transqa.core.language.fasttext_detector import FastTextDetector
        return FastTextDetector
    except ImportError:
        return None

def _get_langid_detector():
    """Lazy import of LangIDDetector to handle optional dependency."""
    try:
        from transqa.core.language.langid_detector import LangIDDetector
        return LangIDDetector
    except ImportError:
        return None


class LanguageDetectorFactory:
    """Factory for creating appropriate language detector instances."""
    
    @staticmethod
    def create_detector(
        detector_type: str = "auto",
        config: Optional[dict] = None
    ) -> BaseLanguageDetector:
        """Create appropriate language detector instance.
        
        Args:
            detector_type: Type of detector ('auto', 'fasttext', 'langid', 'composite')
            config: Configuration dictionary
            
        Returns:
            Configured language detector instance
            
        Raises:
            ConfigurationError: If requested detector is not available
        """
        config = config or {}
        
        if detector_type == "auto":
            return LanguageDetectorFactory._create_best_available(config)
        
        elif detector_type == "fasttext":
            FastTextDetector = _get_fasttext_detector()
            if FastTextDetector is None:
                raise ConfigurationError(
                    "FastText detector requested but not available. "
                    "Install with: pip install fasttext-wheel"
                )
            return FastTextDetector(config)
        
        elif detector_type == "langid":
            LangIDDetector = _get_langid_detector()
            if LangIDDetector is None:
                raise ConfigurationError(
                    "LangID detector requested but not available. "
                    "Install with: pip install langid-py"
                )
            return LangIDDetector(config)
        
        elif detector_type == "composite":
            return LanguageDetectorFactory._create_composite_detector(config)
        
        else:
            raise ConfigurationError(f"Unknown detector type: {detector_type}")
    
    @staticmethod
    def _create_best_available(config: dict) -> BaseLanguageDetector:
        """Create the best available detector automatically."""
        available_detectors = LanguageDetectorFactory.get_available_detectors()
        
        # Priority order: composite > fasttext > langid
        if available_detectors.get("composite", False):
            logger.info("Creating composite language detector (best accuracy)")
            return LanguageDetectorFactory._create_composite_detector(config)
        
        elif available_detectors.get("fasttext", False):
            logger.info("Creating FastText language detector")
            FastTextDetector = _get_fasttext_detector()
            return FastTextDetector(config)
        
        elif available_detectors.get("langid", False):
            logger.info("Creating LangID language detector")
            LangIDDetector = _get_langid_detector()
            return LangIDDetector(config)
        
        else:
            raise ConfigurationError(
                "No language detectors available. Install dependencies:\n"
                "pip install fasttext-wheel  # For FastText (recommended)\n"
                "pip install langid-py       # For LangID (fallback)"
            )
    
    @staticmethod
    def _create_composite_detector(config: dict) -> CompositeLanguageDetector:
        """Create composite detector with all available detectors."""
        detectors = []
        
        # Try to create each detector
        FastTextDetector = _get_fasttext_detector()
        if FastTextDetector:
            try:
                detectors.append(FastTextDetector(config.get('fasttext', {})))
                logger.info("Added FastText detector to composite")
            except Exception as e:
                logger.warning(f"Failed to create FastText detector: {e}")
        
        LangIDDetector = _get_langid_detector()
        if LangIDDetector:
            try:
                detectors.append(LangIDDetector(config.get('langid', {})))
                logger.info("Added LangID detector to composite")
            except Exception as e:
                logger.warning(f"Failed to create LangID detector: {e}")
        
        if not detectors:
            raise ConfigurationError("No detectors available for composite detector")
        
        # Configure composite detector
        composite_config = config.get('composite', {})
        
        # Set default weights favoring FastText if available
        if 'detector_weights' not in composite_config and len(detectors) > 1:
            weights = {}
            for detector in detectors:
                detector_name = detector.__class__.__name__
                if 'FastText' in detector_name:
                    weights[detector_name] = 1.5  # Prefer FastText
                else:
                    weights[detector_name] = 1.0
            composite_config['detector_weights'] = weights
        
        return CompositeLanguageDetector(detectors, composite_config)
    
    @staticmethod
    def create_from_config(app_config) -> BaseLanguageDetector:
        """Create language detector from TransQA configuration object.
        
        Args:
            app_config: TransQAConfig instance
            
        Returns:
            Configured language detector instance
        """
        # Extract language detection configuration
        detector_config = {
            'min_confidence': 0.5,
            'min_text_length': 20,
            'max_text_length': 10000,
            'sample_size': app_config.rules.max_sample_tokens,
            'normalize_text': True,
            'remove_urls': True,
            'remove_emails': True,
            'restrict_to_supported': True,
        }
        
        # FastText specific config
        fasttext_config = detector_config.copy()
        fasttext_config.update({
            'models_dir': str(app_config.get_models_dir()),
            'auto_download': True,
            'k': 5,
            'threshold': 0.0,
        })
        
        # LangID specific config
        langid_config = detector_config.copy()
        langid_config.update({
            'restrict_languages': True,
            'normalize_scores': True,
        })
        
        # Composite config combining both
        composite_config = {
            'fasttext': fasttext_config,
            'langid': langid_config,
            'composite': {
                'voting_method': 'weighted',
                'min_detectors': 1,
                'confidence_threshold': 0.3,
            }
        }
        
        return LanguageDetectorFactory.create_detector('auto', composite_config)
    
    @staticmethod
    def get_available_detectors() -> Dict[str, bool]:
        """Get information about available language detectors.
        
        Returns:
            Dictionary mapping detector names to availability status
        """
        FastTextDetector = _get_fasttext_detector()
        LangIDDetector = _get_langid_detector()
        
        available = {
            'fasttext': FastTextDetector is not None,
            'langid': LangIDDetector is not None,
        }
        
        # Composite is available if at least one detector is available
        available['composite'] = any(available.values())
        
        return available
    
    @staticmethod
    def check_dependencies(verbose: bool = False) -> Dict[str, Dict[str, any]]:
        """Check language detector dependencies and capabilities.
        
        Args:
            verbose: Whether to include detailed information
            
        Returns:
            Dictionary with dependency information
        """
        results = {}
        
        # Check FastText
        FastTextDetector = _get_fasttext_detector()
        if FastTextDetector:
            try:
                # Check model availability without initializing
                fasttext_status = FastTextDetector.check_availability()
                results['fasttext'] = {
                    'available': True,
                    'model_status': fasttext_status,
                    'capabilities': [
                        'high_accuracy',
                        '176_languages',
                        'fast_inference',
                        'pretrained_model'
                    ],
                    'limitations': [
                        'large_model_download',
                        'memory_usage'
                    ]
                }
            except Exception as e:
                results['fasttext'] = {
                    'available': False,
                    'error': str(e),
                    'install_command': 'pip install fasttext-wheel'
                }
        else:
            results['fasttext'] = {
                'available': False,
                'error': 'Module not found',
                'install_command': 'pip install fasttext-wheel'
            }
        
        # Check LangID
        LangIDDetector = _get_langid_detector()
        if LangIDDetector:
            try:
                langid_status = LangIDDetector.check_availability()
                results['langid'] = {
                    'available': True,
                    'test_status': langid_status,
                    'capabilities': [
                        'lightweight',
                        'no_model_download',
                        'fast_setup',
                        '97_languages'
                    ],
                    'limitations': [
                        'lower_accuracy',
                        'single_prediction'
                    ]
                }
            except Exception as e:
                results['langid'] = {
                    'available': False,
                    'error': str(e),
                    'install_command': 'pip install langid-py'
                }
        else:
            results['langid'] = {
                'available': False,
                'error': 'Module not found',
                'install_command': 'pip install langid-py'
            }
        
        # Summary
        available_count = sum(1 for detector, info in results.items() 
                             if info.get('available', False))
        
        results['summary'] = {
            'total_detectors': len(results),
            'available_detectors': available_count,
            'recommended_install': []
        }
        
        if not results.get('fasttext', {}).get('available', False):
            results['summary']['recommended_install'].append('pip install fasttext-wheel')
        
        if not results.get('langid', {}).get('available', False):
            results['summary']['recommended_install'].append('pip install langid-py')
        
        return results
    
    @staticmethod
    def recommend_detector(
        text_length: int,
        accuracy_priority: bool = True,
        speed_priority: bool = False
    ) -> str:
        """Recommend appropriate detector based on requirements.
        
        Args:
            text_length: Average text length to analyze
            accuracy_priority: Whether to prioritize accuracy
            speed_priority: Whether to prioritize speed
            
        Returns:
            Recommended detector name
        """
        available = LanguageDetectorFactory.get_available_detectors()
        
        # If only one type available, use it
        if available['fasttext'] and not available['langid']:
            return 'fasttext'
        elif available['langid'] and not available['fasttext']:
            return 'langid'
        elif not available['fasttext'] and not available['langid']:
            return 'auto'  # Will raise error, but let factory handle it
        
        # Both available - choose based on requirements
        if accuracy_priority and not speed_priority:
            # Accuracy is most important - use composite for best results
            return 'composite'
        
        elif speed_priority and text_length < 1000:
            # Speed important with short texts - langid is faster to setup
            return 'langid'
        
        elif text_length > 10000:
            # Very long texts - FastText handles better
            return 'fasttext'
        
        else:
            # Balanced approach - use composite for best of both
            return 'composite'
    
    @staticmethod
    def benchmark_detectors(test_texts: List[str], expected_languages: List[str]) -> Dict[str, dict]:
        """Benchmark available detectors against test data.
        
        Args:
            test_texts: List of test texts
            expected_languages: List of expected language codes
            
        Returns:
            Dictionary with benchmark results for each detector
        """
        if len(test_texts) != len(expected_languages):
            raise ValueError("test_texts and expected_languages must have same length")
        
        results = {}
        available = LanguageDetectorFactory.get_available_detectors()
        
        for detector_type in ['fasttext', 'langid']:
            if not available[detector_type]:
                continue
            
            try:
                detector = LanguageDetectorFactory.create_detector(detector_type)
                detector.initialize()
                
                correct_predictions = 0
                total_confidence = 0
                total_time = 0
                
                import time
                
                for text, expected_lang in zip(test_texts, expected_languages):
                    start_time = time.time()
                    result = detector.detect_block(text)
                    end_time = time.time()
                    
                    if result.detected_language == expected_lang:
                        correct_predictions += 1
                    
                    total_confidence += result.confidence
                    total_time += (end_time - start_time)
                
                detector.cleanup()
                
                accuracy = correct_predictions / len(test_texts)
                avg_confidence = total_confidence / len(test_texts)
                avg_time = total_time / len(test_texts)
                
                results[detector_type] = {
                    'accuracy': accuracy,
                    'avg_confidence': avg_confidence,
                    'avg_time_seconds': avg_time,
                    'total_tests': len(test_texts),
                    'correct_predictions': correct_predictions,
                }
                
                logger.info(f"{detector_type}: {accuracy:.2%} accuracy, {avg_time:.3f}s avg time")
            
            except Exception as e:
                results[detector_type] = {
                    'error': str(e),
                    'accuracy': 0.0,
                }
                logger.error(f"Benchmark failed for {detector_type}: {e}")
        
        return results

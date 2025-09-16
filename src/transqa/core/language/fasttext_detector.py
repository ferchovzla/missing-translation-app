"""FastText-based language detector."""

import logging
import os
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

from transqa.core.language.base import BaseLanguageDetector
from transqa.core.interfaces import LanguageDetectionError

logger = logging.getLogger(__name__)

try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False
    fasttext = None


class FastTextDetector(BaseLanguageDetector):
    """Language detector using FastText LID (Language Identification)."""
    
    # Official FastText LID model URL
    LID_MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
    LID_MODEL_FILENAME = "lid.176.bin"
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize FastText detector."""
        if not FASTTEXT_AVAILABLE:
            raise ImportError(
                "FastText is not installed. Install with: pip install fasttext-wheel"
            )
        
        super().__init__(config)
        
        # FastText-specific configuration
        self.model_path = self.config.get('model_path', None)
        self.models_dir = self.config.get('models_dir', None)
        self.auto_download = self.config.get('auto_download', True)
        self.k = self.config.get('k', 5)  # Number of predictions to return
        self.threshold = self.config.get('threshold', 0.0)  # Minimum threshold for predictions
        
        # Model instance
        self._model = None
        self._model_loaded = False
    
    def initialize(self) -> None:
        """Initialize the FastText model."""
        super().initialize()
        
        if not self._model_loaded:
            self._load_model()
            self._model_loaded = True
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        super().cleanup()
        if self._model:
            # FastText models don't need explicit cleanup
            self._model = None
        self._model_loaded = False
    
    def _detect_language_impl(self, text: str) -> Tuple[str, float, List[Tuple[str, float]]]:
        """Detect language using FastText LID model."""
        if not self._model:
            raise LanguageDetectionError("FastText model not loaded")
        
        try:
            # FastText expects single line input without newlines
            text_clean = text.replace('\n', ' ').strip()
            
            if not text_clean:
                return 'unknown', 0.0, []
            
            # Predict language
            predictions = self._model.predict(text_clean, k=self.k, threshold=self.threshold)
            
            if not predictions[0]:  # No predictions
                return 'unknown', 0.0, []
            
            # Parse results
            languages = predictions[0]  # List of language labels
            confidences = predictions[1]  # List of confidence scores
            
            # Convert FastText labels (e.g., '__label__en') to language codes
            results = []
            for lang_label, confidence in zip(languages, confidences):
                lang_code = self._parse_fasttext_label(lang_label)
                if lang_code:
                    results.append((lang_code, float(confidence)))
            
            if not results:
                return 'unknown', 0.0, []
            
            # Primary result
            primary_lang, primary_confidence = results[0]
            
            # Alternatives (excluding the primary)
            alternatives = results[1:] if len(results) > 1 else []
            
            return primary_lang, primary_confidence, alternatives
        
        except Exception as e:
            logger.error(f"FastText detection error: {e}")
            return 'unknown', 0.0, []
    
    def _parse_fasttext_label(self, label: str) -> Optional[str]:
        """Parse FastText language label to language code."""
        if not label.startswith('__label__'):
            return None
        
        # Extract language code (e.g., '__label__en' -> 'en')
        lang_code = label[9:]  # Remove '__label__' prefix
        
        # Map some common variations to our supported languages
        lang_mapping = {
            'es': 'es',
            'spa': 'es',  # Spanish ISO 639-2
            'en': 'en', 
            'eng': 'en',  # English ISO 639-2
            'nl': 'nl',
            'nld': 'nl',  # Dutch ISO 639-2
            'dut': 'nl',  # Dutch alternative code
        }
        
        return lang_mapping.get(lang_code.lower(), lang_code.lower())
    
    def _load_model(self) -> None:
        """Load the FastText LID model."""
        try:
            # Determine model path
            model_path = self._get_model_path()
            
            # Download model if needed and auto_download is enabled
            if not model_path.exists() and self.auto_download:
                logger.info(f"FastText LID model not found. Downloading to {model_path}...")
                self._download_model(model_path)
            
            if not model_path.exists():
                raise LanguageDetectionError(
                    f"FastText LID model not found at {model_path}. "
                    f"Set auto_download=True or download manually from {self.LID_MODEL_URL}"
                )
            
            # Load model
            logger.info(f"Loading FastText LID model from {model_path}...")
            self._model = fasttext.load_model(str(model_path))
            logger.info("FastText LID model loaded successfully")
        
        except Exception as e:
            raise LanguageDetectionError(f"Failed to load FastText model: {e}")
    
    def _get_model_path(self) -> Path:
        """Get the path to the FastText LID model."""
        if self.model_path:
            return Path(self.model_path)
        
        # Use models directory or default location
        if self.models_dir:
            models_dir = Path(self.models_dir)
        else:
            # Default to platform-appropriate data directory
            try:
                import platformdirs
                models_dir = Path(platformdirs.user_data_dir("transqa", "transqa")) / "models"
            except ImportError:
                # Fallback to current directory
                models_dir = Path("models")
        
        models_dir.mkdir(parents=True, exist_ok=True)
        return models_dir / self.LID_MODEL_FILENAME
    
    def _download_model(self, target_path: Path) -> None:
        """Download the FastText LID model."""
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading FastText LID model from {self.LID_MODEL_URL}...")
            
            # Download with progress (simple version)
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    downloaded = block_num * block_size
                    percent = min(100, (downloaded * 100) // total_size)
                    if block_num % 1000 == 0:  # Log every ~1000 blocks to avoid spam
                        logger.info(f"Download progress: {percent}% ({downloaded}/{total_size} bytes)")
            
            urllib.request.urlretrieve(
                self.LID_MODEL_URL, 
                str(target_path),
                reporthook=progress_hook
            )
            
            logger.info(f"FastText LID model downloaded successfully: {target_path}")
            
            # Verify file size (LID model should be around 126MB)
            file_size = target_path.stat().st_size
            if file_size < 1_000_000:  # Less than 1MB suggests incomplete download
                target_path.unlink()  # Delete incomplete file
                raise LanguageDetectionError(
                    f"Downloaded file appears incomplete (size: {file_size} bytes)"
                )
            
            logger.info(f"Model file size: {file_size / 1_000_000:.1f} MB")
        
        except Exception as e:
            if target_path.exists():
                target_path.unlink()  # Clean up incomplete download
            raise LanguageDetectionError(f"Failed to download FastText model: {e}")
    
    @staticmethod
    def check_availability() -> dict:
        """Check if FastText is available and model status."""
        result = {
            'available': FASTTEXT_AVAILABLE,
            'model_downloaded': False,
            'model_path': None,
            'model_size': None,
        }
        
        if not FASTTEXT_AVAILABLE:
            result['error'] = 'FastText not installed'
            result['install_command'] = 'pip install fasttext-wheel'
            return result
        
        # Check for model
        detector = FastTextDetector({'auto_download': False})
        model_path = detector._get_model_path()
        
        if model_path.exists():
            result['model_downloaded'] = True
            result['model_path'] = str(model_path)
            result['model_size'] = model_path.stat().st_size
        else:
            result['download_url'] = FastTextDetector.LID_MODEL_URL
            result['expected_path'] = str(model_path)
        
        return result
    
    def get_supported_languages(self) -> List[str]:
        """Get list of languages supported by the loaded model."""
        if not self._model:
            return []
        
        try:
            # FastText LID supports 176 languages, but we filter to our supported ones
            # This is a simplified implementation - the actual model supports many more
            return list(self.SUPPORTED_LANGUAGES)
        except Exception as e:
            logger.error(f"Error getting supported languages: {e}")
            return []
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        info = {
            'model_loaded': self._model is not None,
            'model_type': 'FastText LID',
            'supported_languages': len(self.SUPPORTED_LANGUAGES),
        }
        
        if self._model:
            try:
                # Get model path
                model_path = self._get_model_path()
                if model_path.exists():
                    info['model_path'] = str(model_path)
                    info['model_size'] = model_path.stat().st_size
                
                # Add configuration info
                info['config'] = {
                    'k': self.k,
                    'threshold': self.threshold,
                    'min_confidence': self.min_confidence,
                }
            except Exception as e:
                info['error'] = str(e)
        
        return info

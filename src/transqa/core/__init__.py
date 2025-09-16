"""Core components and interfaces for TransQA."""

from transqa.core.interfaces import (
    Extractor,
    Fetcher, 
    LanguageDetector,
    Verifier,
    TextBlock,
    LanguageDetectionResult,
    ExtractionResult
)

from transqa.core.fetchers import (
    BaseFetcher,
    RequestsFetcher,
    FetcherFactory,
)

from transqa.core.extractors import (
    BaseExtractor,
    HTMLExtractor,
    ExtractorFactory,
)

from transqa.core.language import (
    BaseLanguageDetector,
    CompositeLanguageDetector,
    LanguageDetectorFactory,
)

from transqa.core.verification import (
    BaseVerifier,
    PlaceholderValidator,
    HeuristicVerifier,
    CompositeVerifier,
    VerifierFactory,
)

# Conditional imports for optional dependencies
try:
    from transqa.core.fetchers import PlaywrightFetcher
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PlaywrightFetcher = None
    PLAYWRIGHT_AVAILABLE = False

try:
    from transqa.core.language import FastTextDetector
    FASTTEXT_AVAILABLE = True
except ImportError:
    FastTextDetector = None
    FASTTEXT_AVAILABLE = False

try:
    from transqa.core.language import LangIDDetector
    LANGID_AVAILABLE = True
except ImportError:
    LangIDDetector = None
    LANGID_AVAILABLE = False

try:
    from transqa.core.verification import LanguageToolVerifier
    LANGUAGETOOL_AVAILABLE = True
except ImportError:
    LanguageToolVerifier = None
    LANGUAGETOOL_AVAILABLE = False

__all__ = [
    "Fetcher",
    "Extractor",
    "LanguageDetector",
    "Verifier",
    "TextBlock",
    "LanguageDetectionResult",
    "ExtractionResult",
    "BaseFetcher",
    "RequestsFetcher",
    "FetcherFactory",
    "BaseExtractor",
    "HTMLExtractor", 
    "ExtractorFactory",
    "BaseLanguageDetector",
    "CompositeLanguageDetector",
    "LanguageDetectorFactory",
    "BaseVerifier",
    "PlaceholderValidator",
    "HeuristicVerifier",
    "CompositeVerifier",
    "VerifierFactory",
]

if PLAYWRIGHT_AVAILABLE:
    __all__.append("PlaywrightFetcher")

if FASTTEXT_AVAILABLE:
    __all__.append("FastTextDetector")

if LANGID_AVAILABLE:
    __all__.append("LangIDDetector")

if LANGUAGETOOL_AVAILABLE:
    __all__.append("LanguageToolVerifier")

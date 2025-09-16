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

__all__ = [
    "Fetcher",
    "Extractor",
    "LanguageDetector",
    "Verifier",
    "TextBlock",
    "LanguageDetectionResult",
    "ExtractionResult",
]

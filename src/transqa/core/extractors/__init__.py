"""Text extractors for TransQA."""

from transqa.core.extractors.base import BaseExtractor
from transqa.core.extractors.html_extractor import HTMLExtractor
from transqa.core.extractors.factory import ExtractorFactory

__all__ = [
    "BaseExtractor",
    "HTMLExtractor",
    "ExtractorFactory",
]

"""Language detection components for TransQA."""

from transqa.core.language.base import BaseLanguageDetector
from transqa.core.language.fasttext_detector import FastTextDetector
from transqa.core.language.langid_detector import LangIDDetector
from transqa.core.language.composite_detector import CompositeLanguageDetector
from transqa.core.language.factory import LanguageDetectorFactory

__all__ = [
    "BaseLanguageDetector",
    "FastTextDetector", 
    "LangIDDetector",
    "CompositeLanguageDetector",
    "LanguageDetectorFactory",
]

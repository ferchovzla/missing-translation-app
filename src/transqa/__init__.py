"""TransQA - Web Translation Quality Assurance Tool.

A comprehensive tool for detecting translation errors, language leakage,
and quality issues in multilingual web content.
"""

__version__ = "0.1.0"
__author__ = "Translation QA Team"
__email__ = "dev@transqa.com"

from transqa.models.issue import Issue, IssueType, Severity
from transqa.models.result import PageResult, AnalysisStats

__all__ = [
    "Issue",
    "IssueType", 
    "Severity",
    "PageResult",
    "AnalysisStats",
]

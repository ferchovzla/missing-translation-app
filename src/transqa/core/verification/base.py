"""Base verifier implementation."""

import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Set

from transqa.core.interfaces import BaseAnalyzer, TextBlock
from transqa.models.issue import Issue, IssueType, Severity

logger = logging.getLogger(__name__)


class BaseVerifier(BaseAnalyzer, ABC):
    """Base class for text verifiers."""
    
    # Common patterns for various validation rules
    PLACEHOLDER_PATTERNS = {
        'curly_braces': re.compile(r'\{[^}]*\}'),           # {variable}
        'double_curly': re.compile(r'\{\{[^}]*\}\}'),       # {{handlebars}}
        'printf_style': re.compile(r'%[sdifgeEGc%]'),       # %s, %d, etc.
        'dollar_braces': re.compile(r'\$\{[^}]*\}'),        # ${variable}
        'colon_params': re.compile(r':[a-zA-Z_][a-zA-Z0-9_]*'), # :parameter
        'square_brackets': re.compile(r'\[[^\]]*\]'),       # [placeholder]
        'angle_brackets': re.compile(r'<[^>]*>'),           # <placeholder>
    }
    
    URL_PATTERN = re.compile(r'https?://[^\s]+')
    EMAIL_PATTERN = re.compile(r'\S+@\S+\.\S+')
    NUMBER_PATTERNS = {
        'es': re.compile(r'\d{1,3}(?:\.\d{3})*(?:,\d+)?'),  # 1.234.567,89
        'en': re.compile(r'\d{1,3}(?:,\d{3})*(?:\.\d+)?'),  # 1,234,567.89
        'nl': re.compile(r'\d{1,3}(?:\.\d{3})*(?:,\d+)?'),  # 1.234.567,89 (like Spanish)
    }
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize the verifier with configuration."""
        super().__init__(config)
        self.config = config or {}
        
        # Common configuration
        self.severity_mapping = self.config.get('severity_mapping', {
            'grammar': Severity.WARNING,
            'spelling': Severity.ERROR,
            'style': Severity.INFO,
            'placeholder': Severity.ERROR,
            'language_leak': Severity.ERROR,
            'punctuation': Severity.WARNING,
            'capitalization': Severity.WARNING,
        })
        
        self.min_text_length = self.config.get('min_text_length', 3)
        self.skip_urls = self.config.get('skip_urls', True)
        self.skip_emails = self.config.get('skip_emails', True)
        self.skip_numbers = self.config.get('skip_numbers', False)
        
        # Issue filtering
        self.ignore_rules = set(self.config.get('ignore_rules', []))
        self.enable_rules = set(self.config.get('enable_rules', []))
        
        # Severity overrides
        self.severity_overrides = self.config.get('severity_overrides', {})
    
    def initialize(self) -> None:
        """Initialize the verifier."""
        super().initialize()
        logger.info(f"Base verifier initialized with {len(self.ignore_rules)} ignore rules")
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        super().cleanup()
    
    def check(self, text: str, target_lang: str, context: Optional[TextBlock] = None) -> List[Issue]:
        """Check text for quality issues.
        
        Args:
            text: Text to check
            target_lang: Expected target language (es, en, nl)
            context: Optional context information
            
        Returns:
            List of detected issues
        """
        if not text or len(text.strip()) < self.min_text_length:
            return []
        
        # Preprocess text if needed
        processed_text = self._preprocess_text(text)
        if not processed_text:
            return []
        
        # Run implementation-specific checks
        issues = self._check_impl(processed_text, target_lang, context)
        
        # Post-process issues
        filtered_issues = []
        for issue in issues:
            # Apply rule filtering
            if self._should_include_issue(issue):
                # Apply severity overrides
                issue.severity = self._get_effective_severity(issue)
                # Update context if available
                if context:
                    issue.xpath = context.xpath
                    if not issue.context:
                        issue.context = self._extract_context(text, issue.offset_start, issue.offset_end)
                
                filtered_issues.append(issue)
        
        return filtered_issues
    
    @abstractmethod
    def _check_impl(self, text: str, target_lang: str, context: Optional[TextBlock] = None) -> List[Issue]:
        """Implementation-specific text checking."""
        pass
    
    def check_grammar(self, text: str, target_lang: str) -> List[Issue]:
        """Check grammar issues specifically."""
        # Base implementation returns empty - override in subclasses
        return []
    
    def check_spelling(self, text: str, target_lang: str) -> List[Issue]:
        """Check spelling issues specifically."""
        # Base implementation returns empty - override in subclasses
        return []
    
    def check_style(self, text: str, target_lang: str) -> List[Issue]:
        """Check style issues specifically."""
        # Base implementation returns empty - override in subclasses
        return []
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for checking."""
        processed = text.strip()
        
        if not processed:
            return ""
        
        # Skip very short text
        if len(processed) < self.min_text_length:
            return ""
        
        # Skip URLs if configured
        if self.skip_urls and self.URL_PATTERN.search(processed):
            if len(self.URL_PATTERN.sub('', processed).strip()) < self.min_text_length:
                return ""
        
        # Skip emails if configured
        if self.skip_emails and self.EMAIL_PATTERN.search(processed):
            if len(self.EMAIL_PATTERN.sub('', processed).strip()) < self.min_text_length:
                return ""
        
        return processed
    
    def _should_include_issue(self, issue: Issue) -> bool:
        """Check if an issue should be included based on filters."""
        # Check ignore rules
        if issue.rule_id and issue.rule_id in self.ignore_rules:
            return False
        
        # Check enable rules (if specified, only include enabled rules)
        if self.enable_rules and issue.rule_id and issue.rule_id not in self.enable_rules:
            return False
        
        return True
    
    def _get_effective_severity(self, issue: Issue) -> Severity:
        """Get effective severity for an issue, applying overrides."""
        # Check specific rule overrides first
        if issue.rule_id and issue.rule_id in self.severity_overrides:
            return Severity(self.severity_overrides[issue.rule_id])
        
        # Check issue type overrides
        issue_type_str = str(issue.type)
        if issue_type_str in self.severity_overrides:
            return Severity(self.severity_overrides[issue_type_str])
        
        # Return original severity
        return issue.severity
    
    def _extract_context(self, full_text: str, start: int, end: int, context_chars: int = 50) -> str:
        """Extract context around an issue."""
        try:
            # Calculate context window
            context_start = max(0, start - context_chars)
            context_end = min(len(full_text), end + context_chars)
            
            # Extract context
            context = full_text[context_start:context_end]
            
            # Add ellipsis if truncated
            if context_start > 0:
                context = "..." + context
            if context_end < len(full_text):
                context = context + "..."
            
            return context
        except Exception:
            return full_text[start:end]  # Fallback to just the issue text
    
    def _create_issue(
        self,
        issue_type: IssueType,
        message: str,
        text: str,
        start: int,
        end: int,
        target_lang: str,
        suggestion: Optional[str] = None,
        rule_id: Optional[str] = None,
        confidence: float = 1.0,
        context: Optional[TextBlock] = None
    ) -> Issue:
        """Create a standardized issue."""
        # Determine severity
        severity = self.severity_mapping.get(str(issue_type), Severity.WARNING)
        
        # Extract snippet
        snippet = text[start:end] if start < len(text) and end <= len(text) else text
        
        # Create issue
        issue = Issue(
            type=issue_type,
            severity=severity,
            message=message,
            suggestion=suggestion,
            target_lang=target_lang,
            snippet=snippet,
            xpath=context.xpath if context else "/",
            offset_start=start,
            offset_end=end,
            rule_id=rule_id,
            confidence=confidence
        )
        
        return issue
    
    def _find_placeholders(self, text: str) -> List[tuple]:
        """Find all placeholders in text.
        
        Returns:
            List of (pattern_name, match_object, start, end) tuples
        """
        placeholders = []
        
        for pattern_name, pattern in self.PLACEHOLDER_PATTERNS.items():
            for match in pattern.finditer(text):
                placeholders.append((pattern_name, match, match.start(), match.end()))
        
        # Sort by position
        placeholders.sort(key=lambda x: x[2])
        return placeholders
    
    def _validate_placeholder_consistency(self, text: str, target_lang: str) -> List[Issue]:
        """Validate placeholder consistency and format."""
        issues = []
        placeholders = self._find_placeholders(text)
        
        if not placeholders:
            return issues
        
        # Group placeholders by type
        placeholder_groups = {}
        for pattern_name, match, start, end in placeholders:
            if pattern_name not in placeholder_groups:
                placeholder_groups[pattern_name] = []
            placeholder_groups[pattern_name].append((match, start, end))
        
        # Check for mixed placeholder styles (potential inconsistency)
        if len(placeholder_groups) > 2:  # Allow some mixing, but flag excessive mixing
            issue = self._create_issue(
                IssueType.PLACEHOLDER,
                f"Multiple placeholder styles detected: {', '.join(placeholder_groups.keys())}",
                text, 0, len(text), target_lang,
                suggestion="Consider using consistent placeholder style throughout",
                rule_id="MIXED_PLACEHOLDER_STYLES"
            )
            issues.append(issue)
        
        # Check individual placeholders for common issues
        for pattern_name, group in placeholder_groups.items():
            for match, start, end in group:
                placeholder_text = match.group()
                
                # Check for nested placeholders
                if pattern_name == 'curly_braces' and '{{' in placeholder_text:
                    issue = self._create_issue(
                        IssueType.PLACEHOLDER,
                        f"Potentially nested placeholder: {placeholder_text}",
                        text, start, end, target_lang,
                        suggestion="Check if this should use {{}} syntax instead",
                        rule_id="NESTED_PLACEHOLDER"
                    )
                    issues.append(issue)
                
                # Check for empty placeholders
                if pattern_name in ['curly_braces', 'square_brackets'] and len(placeholder_text) <= 2:
                    issue = self._create_issue(
                        IssueType.PLACEHOLDER,
                        f"Empty placeholder: {placeholder_text}",
                        text, start, end, target_lang,
                        suggestion="Remove empty placeholder or add variable name",
                        rule_id="EMPTY_PLACEHOLDER"
                    )
                    issues.append(issue)
        
        return issues
    
    def _check_number_format_consistency(self, text: str, target_lang: str) -> List[Issue]:
        """Check number format consistency for target language."""
        issues = []
        
        if target_lang not in self.NUMBER_PATTERNS:
            return issues
        
        pattern = self.NUMBER_PATTERNS[target_lang]
        numbers = list(pattern.finditer(text))
        
        if not numbers:
            return issues
        
        # For languages with specific formatting rules
        if target_lang == 'en':
            # Check for incorrect European formatting in English text
            european_pattern = re.compile(r'\d{1,3}(?:\.\d{3})+,\d+')  # 1.234,56
            for match in european_pattern.finditer(text):
                issue = self._create_issue(
                    IssueType.CONSISTENCY,
                    f"European number format in English text: {match.group()}",
                    text, match.start(), match.end(), target_lang,
                    suggestion="Use US format with commas as thousands separator and period as decimal: 1,234.56",
                    rule_id="INCORRECT_NUMBER_FORMAT_EN"
                )
                issues.append(issue)
        
        elif target_lang in ['es', 'nl']:
            # Check for US formatting in European text
            us_pattern = re.compile(r'\d{1,3}(?:,\d{3})+\.\d+')  # 1,234.56
            for match in us_pattern.finditer(text):
                issue = self._create_issue(
                    IssueType.CONSISTENCY,
                    f"US number format in {target_lang.upper()} text: {match.group()}",
                    text, match.start(), match.end(), target_lang,
                    suggestion="Use European format with periods as thousands separator and comma as decimal: 1.234,56",
                    rule_id=f"INCORRECT_NUMBER_FORMAT_{target_lang.upper()}"
                )
                issues.append(issue)
        
        return issues
    
    def _check_punctuation_spacing(self, text: str, target_lang: str) -> List[Issue]:
        """Check punctuation and spacing rules."""
        issues = []
        
        # Check for double spaces
        double_space_pattern = re.compile(r'  +')
        for match in double_space_pattern.finditer(text):
            issue = self._create_issue(
                IssueType.PUNCTUATION,
                f"Multiple consecutive spaces: {len(match.group())} spaces",
                text, match.start(), match.end(), target_lang,
                suggestion="Use single space",
                rule_id="MULTIPLE_SPACES"
            )
            issues.append(issue)
        
        # Check spacing around punctuation (language-specific rules)
        if target_lang == 'es':
            # Spanish: No space before question/exclamation marks
            bad_spacing = re.compile(r' +[¿¡]')
            for match in bad_spacing.finditer(text):
                issue = self._create_issue(
                    IssueType.PUNCTUATION,
                    f"Incorrect spacing before Spanish punctuation: {match.group()}",
                    text, match.start(), match.end(), target_lang,
                    suggestion="No space before ¿ or ¡",
                    rule_id="SPANISH_PUNCTUATION_SPACING"
                )
                issues.append(issue)
        
        # Check trailing punctuation spaces (common to all languages)
        trailing_punct_space = re.compile(r'[.!?] +$')
        if trailing_punct_space.search(text):
            match = trailing_punct_space.search(text)
            issue = self._create_issue(
                IssueType.PUNCTUATION,
                "Trailing spaces after final punctuation",
                text, match.start(), match.end(), target_lang,
                suggestion="Remove trailing spaces",
                rule_id="TRAILING_PUNCTUATION_SPACE"
            )
            issues.append(issue)
        
        return issues

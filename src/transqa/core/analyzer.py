"""Main analyzer orchestrating all TransQA components."""

import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

from transqa.core.interfaces import (
    BaseAnalyzer,
    Extractor,
    Fetcher,
    LanguageDetector,
    LanguageLeakDetector,
    PlaceholderValidator,
    Verifier,
    WhitelistManager,
)
from transqa.models.config import TransQAConfig
from transqa.models.issue import Issue
from transqa.models.result import AnalysisStats, PageResult


class TransQAAnalyzer(BaseAnalyzer):
    """Main analyzer for web page translation quality."""
    
    def __init__(
        self,
        config: TransQAConfig,
        fetcher: Fetcher,
        extractor: Extractor,
        language_detector: LanguageDetector,
        leak_detector: LanguageLeakDetector,
        verifier: Verifier,
        placeholder_validator: PlaceholderValidator,
        whitelist_manager: Optional[WhitelistManager] = None,
    ):
        """Initialize the analyzer with all components."""
        super().__init__(config.dict())
        self.config = config
        self.fetcher = fetcher
        self.extractor = extractor
        self.language_detector = language_detector
        self.leak_detector = leak_detector
        self.verifier = verifier
        self.placeholder_validator = placeholder_validator
        self.whitelist_manager = whitelist_manager
    
    def initialize(self) -> None:
        """Initialize all components."""
        # Initialize components that need setup
        for component in [
            self.fetcher,
            self.extractor, 
            self.language_detector,
            self.leak_detector,
            self.verifier,
            self.placeholder_validator,
        ]:
            if hasattr(component, 'initialize'):
                component.initialize()
        
        if self.whitelist_manager and hasattr(self.whitelist_manager, 'initialize'):
            self.whitelist_manager.initialize()
    
    def cleanup(self) -> None:
        """Cleanup all components."""
        for component in [
            self.fetcher,
            self.extractor,
            self.language_detector, 
            self.leak_detector,
            self.verifier,
            self.placeholder_validator,
        ]:
            if hasattr(component, 'cleanup'):
                component.cleanup()
        
        if self.whitelist_manager and hasattr(self.whitelist_manager, 'cleanup'):
            self.whitelist_manager.cleanup()
    
    def analyze_url(
        self, 
        url: str, 
        target_lang: str,
        render_js: Optional[bool] = None
    ) -> PageResult:
        """Analyze a web page for translation quality issues.
        
        Args:
            url: URL to analyze
            target_lang: Target language (es, en, nl)
            render_js: Whether to render JavaScript (None uses config default)
            
        Returns:
            PageResult with detected issues and statistics
        """
        self.ensure_initialized()
        
        if render_js is None:
            render_js = self.config.target.render_js
        
        start_time = time.time()
        
        # Initialize result
        result = PageResult(
            url=url,
            target_lang=target_lang,
            render_js=render_js,
            user_agent=self.config.fetcher.user_agent,
        )
        
        try:
            # 1. Fetch content
            fetch_start = time.time()
            html_content = self.fetcher.get(url, render=render_js)
            fetch_duration = time.time() - fetch_start
            
            # 2. Extract text
            extract_start = time.time()
            extraction_result = self.extractor.extract_blocks(
                html_content,
                ignore_selectors=self.config.rules.ignore_selectors
            )
            extract_duration = time.time() - extract_start
            
            # Update result with extracted data
            result.page_title = extraction_result.title
            result.page_lang = extraction_result.declared_language
            result.meta_description = extraction_result.meta_description
            result.extracted_text = extraction_result.raw_text
            
            # 3. Analyze each text block
            all_issues: List[Issue] = []
            language_distribution: Dict[str, int] = {}
            total_tokens = 0
            
            for block in extraction_result.blocks:
                if not block.text.strip():
                    continue
                
                # Language detection for the block
                lang_result = self.language_detector.detect_block(block.text)
                lang_code = lang_result.detected_language
                language_distribution[lang_code] = language_distribution.get(lang_code, 0) + len(block.text.split())
                total_tokens += len(block.text.split())
                
                # Detect language leakage
                leak_issues = self.leak_detector.detect_leakage(
                    block.text,
                    target_lang,
                    threshold=self.config.rules.leak_threshold,
                    context=block
                )
                all_issues.extend(leak_issues)
                
                # Grammar, spelling, style verification
                if lang_code == target_lang or len(leak_issues) == 0:
                    # Only verify if it's the target language or no leakage detected
                    verify_issues = self.verifier.check(block.text, target_lang, context=block)
                    all_issues.extend(verify_issues)
                
                # Placeholder validation
                placeholder_issues = self.placeholder_validator.validate_placeholders(
                    block.text, context=block
                )
                all_issues.extend(placeholder_issues)
                
                # Number and punctuation validation
                format_issues = self.placeholder_validator.validate_numbers_and_formats(
                    block.text, target_lang
                )
                all_issues.extend(format_issues)
                
                punctuation_issues = self.placeholder_validator.validate_punctuation_spacing(
                    block.text, target_lang
                )
                all_issues.extend(punctuation_issues)
            
            # 4. Filter whitelisted terms if whitelist manager available
            if self.whitelist_manager:
                all_issues = self._filter_whitelisted_issues(all_issues, target_lang)
            
            # 5. Add source URL to all issues
            for issue in all_issues:
                issue.source_url = url
            
            # 6. Calculate statistics
            analysis_duration = time.time() - start_time
            
            stats = self._calculate_stats(
                extraction_result,
                all_issues,
                language_distribution,
                total_tokens,
                analysis_duration,
                fetch_duration,
                extract_duration,
                len(html_content),
                target_lang
            )
            
            result.issues = all_issues
            result.stats = stats
            
        except Exception as e:
            # Create error issue
            error_issue = Issue(
                type="system_error",
                severity="critical",
                message=f"Analysis failed: {str(e)}",
                target_lang=target_lang,
                snippet="",
                xpath="/",
                offset_start=0,
                offset_end=0,
                source_url=url
            )
            result.issues = [error_issue]
        
        return result
    
    def _filter_whitelisted_issues(self, issues: List[Issue], target_lang: str) -> List[Issue]:
        """Filter out issues for whitelisted terms."""
        if not self.whitelist_manager:
            return issues
        
        filtered_issues = []
        for issue in issues:
            # Extract potential terms from the issue snippet
            # This is a simple implementation - could be enhanced
            terms = issue.snippet.split()
            is_whitelisted = False
            
            for term in terms:
                cleaned_term = term.strip('.,;:!?"\'()[]{}')
                if self.whitelist_manager.is_whitelisted(cleaned_term, target_lang):
                    is_whitelisted = True
                    break
            
            if not is_whitelisted:
                filtered_issues.append(issue)
        
        return filtered_issues
    
    def _calculate_stats(
        self,
        extraction_result,
        issues: List[Issue],
        language_distribution: Dict[str, int],
        total_tokens: int,
        analysis_duration: float,
        fetch_duration: float,
        extract_duration: float,
        html_size: int,
        target_lang: str,
    ) -> AnalysisStats:
        """Calculate analysis statistics."""
        # Convert language distribution to percentages
        lang_percentages = {}
        if total_tokens > 0:
            for lang, count in language_distribution.items():
                lang_percentages[lang] = (count / total_tokens) * 100
        
        # Count issues by type and severity
        issues_by_type = {}
        issues_by_severity = {}
        
        for issue in issues:
            issues_by_type[issue.type] = issues_by_type.get(issue.type, 0) + 1
            issues_by_severity[issue.severity] = issues_by_severity.get(issue.severity, 0) + 1
        
        # Calculate quality scores
        critical_count = issues_by_severity.get("critical", 0)
        error_count = issues_by_severity.get("error", 0)
        warning_count = issues_by_severity.get("warning", 0)
        
        # Overall score: penalize critical errors heavily, errors moderately, warnings lightly
        penalty = (critical_count * 0.5) + (error_count * 0.2) + (warning_count * 0.05)
        overall_score = max(0.0, 1.0 - min(penalty, 1.0))
        
        # Language purity score
        target_lang_percentage = lang_percentages.get(target_lang, 0.0)
        language_purity_score = target_lang_percentage / 100.0 if target_lang_percentage > 0 else 0.0
        
        return AnalysisStats(
            total_tokens=total_tokens,
            total_blocks=len(extraction_result.blocks),
            total_chars=len(extraction_result.raw_text),
            language_distribution=lang_percentages,
            issues_by_type=issues_by_type,
            issues_by_severity=issues_by_severity,
            analysis_duration_seconds=analysis_duration,
            fetch_duration_seconds=fetch_duration,
            extraction_duration_seconds=extract_duration,
            html_size_bytes=html_size,
            extracted_text_size=len(extraction_result.raw_text),
            overall_score=overall_score,
            language_purity_score=language_purity_score,
        )

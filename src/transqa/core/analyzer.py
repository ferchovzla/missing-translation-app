"""Main analyzer orchestrating all TransQA components."""

import logging
import signal
import time
from contextlib import contextmanager
from typing import Dict, List, Optional
from urllib.parse import urlparse

from transqa.core.interfaces import BaseAnalyzer, FetchError, ExtractionError, LanguageDetectionError, VerificationError
from transqa.core.fetchers import FetcherFactory
from transqa.core.extractors import ExtractorFactory
from transqa.core.language import LanguageDetectorFactory
from transqa.core.verification import VerifierFactory
from transqa.models.config import TransQAConfig
from transqa.models.issue import Issue, IssueType, Severity
from transqa.models.result import AnalysisStats, PageResult

logger = logging.getLogger(__name__)


class TransQAAnalyzer(BaseAnalyzer):
    """Main analyzer for web page translation quality."""
    
    def __init__(self, config: TransQAConfig):
        """Initialize the analyzer with configuration."""
        super().__init__(config.dict())
        self.config = config
        
        # Component instances (will be created in initialize())
        self.fetcher = None
        self.extractor = None
        self.language_detector = None
        self.verifier = None
        
        # Timeouts and error handling
        self.analysis_timeout = config.fetcher.timeout * 3  # 3x fetch timeout
        self.max_analysis_time = getattr(config.fetcher, 'max_analysis_time', 60)  # Max 60s per URL
        
        # State tracking
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize all components using factories."""
        if self._initialized:
            return
            
        logger.info("Initializing TransQA analyzer components...")
        init_start = time.time()
        
        try:
            # Create and initialize fetcher with timeout
            logger.info("Creating fetcher...")
            self.fetcher = FetcherFactory.create_from_config(self.config)
            if hasattr(self.fetcher, 'initialize'):
                self.fetcher.initialize()
            logger.info(f"✓ Fetcher ready: {self.fetcher.__class__.__name__}")
            
            # Check initialization timeout (max 10s for all components)
            if time.time() - init_start > 10:
                raise TimeoutError("Component initialization taking too long")
            
            # Create extractor (should be fast)
            logger.info("Creating extractor...")
            self.extractor = ExtractorFactory.create_from_config(self.config)
            if hasattr(self.extractor, 'initialize'):
                self.extractor.initialize()
            logger.info(f"✓ Extractor ready: {self.extractor.__class__.__name__}")
            
            # Create language detector (may download models)
            logger.info("Creating language detector...")
            self.language_detector = LanguageDetectorFactory.create_from_config(self.config)
            if hasattr(self.language_detector, 'initialize'):
                self.language_detector.initialize()
            logger.info(f"✓ Language detector ready: {self.language_detector.__class__.__name__}")
            
            # Create verifier (may be slow for LanguageTool)
            logger.info("Creating verifier...")
            self.verifier = VerifierFactory.create_from_config(self.config)
            if hasattr(self.verifier, 'initialize'):
                self.verifier.initialize()
            logger.info(f"✓ Verifier ready: {self.verifier.__class__.__name__}")
            
            self._initialized = True
            init_duration = time.time() - init_start
            logger.info(f"✅ All components initialized in {init_duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize TransQA analyzer: {e}")
            raise
    
    def _check_timeout(self, start_time: float, max_time: int, operation: str):
        """Simple timeout checker without signals."""
        elapsed = time.time() - start_time
        if elapsed > max_time:
            raise TimeoutError(f"{operation} timed out after {elapsed:.1f}s (limit: {max_time}s)")
    
    def cleanup(self) -> None:
        """Cleanup all components."""
        for component_name, component in [
            ("fetcher", self.fetcher),
            ("extractor", self.extractor),
            ("language_detector", self.language_detector),
            ("verifier", self.verifier),
        ]:
            try:
                if component and hasattr(component, 'cleanup'):
                    component.cleanup()
                logger.debug(f"Cleaned up {component_name}")
            except Exception as e:
                logger.warning(f"Error cleaning up {component_name}: {e}")
        
        self._initialized = False
        logger.info("TransQA analyzer cleanup completed")
    
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
        logger.info(f"🚀 Starting analysis of {url} (target: {target_lang}, render_js: {render_js})")
        
        # Initialize result
        result = PageResult(
            url=url,
            target_lang=target_lang,
            render_js=render_js,
            user_agent=self.config.fetcher.user_agent,
        )
        
        logger.debug(f"📋 Analysis parameters: timeout={self.max_analysis_time}s, target_lang={target_lang}")
        
        try:
            # 1. Fetch content
            fetch_start = time.time()
            logger.info(f"🌐 [STEP 1/4] Starting fetch for {url}...")
            logger.debug(f"📡 Fetcher type: {type(self.fetcher).__name__}")
            self._check_timeout(start_time, self.max_analysis_time, f"analysis of {url}")
            
            if hasattr(self.fetcher, 'get_with_metadata'):
                logger.debug("📊 Using fetcher with metadata support")
                fetch_result = self.fetcher.get_with_metadata(url, render=render_js)
                html_content = fetch_result['content']
                result.page_title = fetch_result.get('title', '')
                logger.debug(f"📄 Content type: {fetch_result.get('content_type', 'unknown')}")
            else:
                logger.debug("📄 Using basic fetcher")
                html_content = self.fetcher.get(url, render=render_js)
            
            fetch_duration = time.time() - fetch_start
            logger.info(f"✅ [STEP 1/4] Fetched {len(html_content)} characters in {fetch_duration:.2f}s")
            
            # 2. Extract text blocks
            extract_start = time.time()
            logger.info(f"📝 [STEP 2/4] Starting text extraction...")
            logger.debug(f"🔧 Extractor type: {type(self.extractor).__name__}")
            self._check_timeout(start_time, self.max_analysis_time, f"analysis of {url}")
            
            extraction_result = self.extractor.extract_blocks(html_content)
            extract_duration = time.time() - extract_start
            
            if not extraction_result.success:
                logger.error(f"❌ Text extraction failed: {extraction_result.error_message}")
                raise ExtractionError(extraction_result.error_message or "Text extraction failed")
            
            logger.info(f"✅ [STEP 2/4] Extracted {len(extraction_result.blocks)} blocks in {extract_duration:.2f}s")
            logger.debug(f"📊 Raw text length: {len(extraction_result.raw_text)} chars")
            
            # Update result with extracted data
            result.page_title = result.page_title or extraction_result.title
            result.page_lang = extraction_result.declared_language
            result.meta_description = extraction_result.meta_description
            result.extracted_text = extraction_result.raw_text
            
            logger.debug(f"📋 Page info - Title: {result.page_title[:50] if result.page_title else 'N/A'}...")
            logger.debug(f"🌐 Declared language: {result.page_lang or 'None'}")
            
            # 3. Analyze each text block
            all_issues: List[Issue] = []
            language_distribution: Dict[str, int] = {}
            total_tokens = 0
            
            logger.info(f"🔍 [STEP 3/4] Starting analysis of {len(extraction_result.blocks)} text blocks...")
            logger.debug(f"🎯 Language detector: {type(self.language_detector).__name__}")
            logger.debug(f"✏️  Verifier: {type(self.verifier).__name__}")
            self._check_timeout(start_time, self.max_analysis_time, f"analysis of {url}")
            
            for i, block in enumerate(extraction_result.blocks):
                # Check timeout periodically during block analysis
                if i % 10 == 0:  # Check every 10 blocks
                    self._check_timeout(start_time, self.max_analysis_time, f"analysis of {url}")
                    if i > 0:
                        logger.debug(f"📊 Progress: analyzed {i}/{len(extraction_result.blocks)} blocks")
                
                if not block.text.strip():
                    continue
                
                block_tokens = len(block.text.split())
                total_tokens += block_tokens
                
                try:
                    # Language detection for the block
                    if i < 5:  # Log first few blocks in detail
                        logger.debug(f"🔍 Analyzing block {i+1}: '{block.text[:50]}...' ({block_tokens} tokens)")
                    
                    lang_result = self.language_detector.detect_block(block.text)
                    lang_code = lang_result.detected_language
                    language_distribution[lang_code] = language_distribution.get(lang_code, 0) + block_tokens
                    
                    # Skip further analysis if language detection failed
                    if lang_code == 'unknown':
                        if i < 5:
                            logger.debug(f"⚠️  Unknown language detected for block {i+1}")
                        continue
                    
                    # Check for language leakage using the verifier (which includes heuristic checks)
                    if lang_code != target_lang:
                        # Create language leakage issue
                        leak_issue = Issue(
                            type=IssueType.LANGUAGE_LEAK,
                            severity=Severity.ERROR,
                            message=f"Text appears to be in {lang_code.upper()} instead of {target_lang.upper()}",
                            target_lang=target_lang,
                            snippet=block.text[:100] + "..." if len(block.text) > 100 else block.text,
                            xpath=block.xpath,
                            offset_start=block.offset_start,
                            offset_end=block.offset_end,
                            confidence=lang_result.confidence,
                            detected_lang=lang_code,
                            detected_lang_confidence=lang_result.confidence,
                            source_url=url
                        )
                        all_issues.append(leak_issue)
                    
                    # Grammar, spelling, style verification for target language content
                    if lang_code == target_lang or lang_result.confidence < 0.7:  # Check if uncertain
                        # Limit verification to avoid hanging on large blocks
                        if len(block.text) < 1000:  # Only verify smaller blocks
                            if i < 3:
                                logger.debug(f"✏️  Running verification for block {i+1} in {lang_code}")
                            
                            verify_issues = self.verifier.check(block.text, target_lang, context=block)
                            
                            if verify_issues and i < 3:
                                logger.debug(f"🚨 Found {len(verify_issues)} issues in block {i+1}")
                            
                            for issue in verify_issues:
                                issue.source_url = url
                                issue.xpath = block.xpath
                            all_issues.extend(verify_issues)
                        else:
                            logger.debug(f"⏭️  Skipping verification for large block {i+1} ({len(block.text)} chars)")
                    
                except Exception as e:
                    logger.warning(f"❌ Error analyzing block {i+1}: {e}")
                    continue
            
            # 4. Calculate statistics
            logger.info(f"📊 [STEP 4/4] Calculating final statistics...")
            logger.debug(f"📈 Found {len(all_issues)} total issues across {len(extraction_result.blocks)} blocks")
            logger.debug(f"🌍 Language distribution: {dict(list(language_distribution.items())[:5])}")
            
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
            
            logger.info(f"✅ [COMPLETE] Analysis finished: {len(all_issues)} issues found in {analysis_duration:.2f}s")
        
        except TimeoutError as e:
            elapsed = time.time() - start_time
            logger.error(f"⏱️  TIMEOUT: Analysis timed out for {url} after {elapsed:.1f}s: {e}")
            error_issue = Issue(
                type=IssueType.GRAMMAR,  # Use existing enum value
                severity=Severity.CRITICAL,
                message=f"Analysis timed out after {elapsed:.1f}s: {str(e)}",
                target_lang=target_lang,
                snippet="",
                xpath="/",
                offset_start=0,
                offset_end=0,
                source_url=url
            )
            result.issues = [error_issue]
            
        except FetchError as e:
            elapsed = time.time() - start_time
            logger.error(f"🌐 FETCH ERROR for {url} after {elapsed:.1f}s: {e}")
            error_issue = Issue(
                type=IssueType.GRAMMAR,  # Use existing enum value
                severity=Severity.CRITICAL,
                message=f"Failed to fetch content: {str(e)}",
                target_lang=target_lang,
                snippet="",
                xpath="/",
                offset_start=0,
                offset_end=0,
                source_url=url
            )
            result.issues = [error_issue]
            
        except (ExtractionError, LanguageDetectionError, VerificationError) as e:
            logger.error(f"Analysis error for {url}: {e}")
            error_issue = Issue(
                type=IssueType.GRAMMAR,  # Use existing enum value
                severity=Severity.CRITICAL,
                message=f"Analysis failed: {str(e)}",
                target_lang=target_lang,
                snippet="",
                xpath="/",
                offset_start=0,
                offset_end=0,
                source_url=url
            )
            result.issues = [error_issue]
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.exception(f"💥 UNEXPECTED ERROR analyzing {url} after {elapsed:.1f}s: {e}")
            error_issue = Issue(
                type=IssueType.GRAMMAR,  # Use existing enum value
                severity=Severity.CRITICAL,
                message=f"Unexpected error after {elapsed:.1f}s: {str(e)}",
                target_lang=target_lang,
                snippet="",
                xpath="/",
                offset_start=0,
                offset_end=0,
                source_url=url
            )
            result.issues = [error_issue]
        
        final_duration = time.time() - start_time
        logger.debug(f"🏁 Analysis result for {url}: {len(result.issues)} issues, {final_duration:.2f}s total")
        return result
    
    def ensure_initialized(self) -> None:
        """Ensure analyzer is initialized."""
        if not self._initialized:
            self.initialize()
    
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
            issues_by_type[str(issue.type)] = issues_by_type.get(str(issue.type), 0) + 1
            issues_by_severity[str(issue.severity)] = issues_by_severity.get(str(issue.severity), 0) + 1
        
        # Calculate quality scores
        critical_count = issues_by_severity.get("critical", 0)
        error_count = issues_by_severity.get("error", 0)
        warning_count = issues_by_severity.get("warning", 0)
        
        # Overall score: penalize critical errors heavily, errors moderately, warnings lightly
        penalty = (critical_count * 0.5) + (error_count * 0.2) + (warning_count * 0.05)
        overall_score = max(0.0, 1.0 - min(penalty / max(1, len(extraction_result.blocks)), 1.0))
        
        # Language purity score
        target_lang_percentage = lang_percentages.get(target_lang, 0.0)
        language_purity_score = target_lang_percentage / 100.0 if target_lang_percentage > 0 else 0.0
        
        return AnalysisStats(
            total_tokens=total_tokens,
            total_blocks=len(extraction_result.blocks),
            total_chars=len(extraction_result.raw_text or ""),
            language_distribution=lang_percentages,
            issues_by_type=issues_by_type,
            issues_by_severity=issues_by_severity,
            analysis_duration_seconds=analysis_duration,
            fetch_duration_seconds=fetch_duration,
            extraction_duration_seconds=extract_duration,
            html_size_bytes=html_size,
            extracted_text_size=len(extraction_result.raw_text or ""),
            overall_score=overall_score,
            language_purity_score=language_purity_score,
        )

"""LanguageTool-based verifier for grammar, spelling, and style."""

import logging
import time
from typing import Dict, List, Optional

from transqa.core.verification.base import BaseVerifier
from transqa.core.interfaces import Issue, IssueType, Severity, TextBlock, VerificationError

logger = logging.getLogger(__name__)

try:
    import language_tool_python as ltp
    LANGUAGETOOL_AVAILABLE = True
except ImportError:
    LANGUAGETOOL_AVAILABLE = False
    ltp = None


class LanguageToolVerifier(BaseVerifier):
    """Verifier using LanguageTool for grammar, spelling, and style checking."""
    
    # LanguageTool language codes mapping
    LANGUAGE_CODES = {
        'es': 'es',
        'en': 'en-US', 
        'nl': 'nl'
    }
    
    # Category mapping to our issue types
    CATEGORY_MAPPING = {
        'GRAMMAR': IssueType.GRAMMAR,
        'TYPOS': IssueType.SPELLING,
        'STYLE': IssueType.STYLE,
        'PUNCTUATION': IssueType.PUNCTUATION,
        'TYPOGRAPHY': IssueType.STYLE,
        'CASING': IssueType.CAPITALIZATION,
        'REPETITION': IssueType.STYLE,
        'REDUNDANCY': IssueType.STYLE,
        'MISC': IssueType.GRAMMAR,
    }
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize LanguageTool verifier."""
        if not LANGUAGETOOL_AVAILABLE:
            raise ImportError(
                "LanguageTool is not installed. Install with: pip install language-tool-python"
            )
        
        super().__init__(config)
        
        # LanguageTool-specific configuration
        self.server_url = self.config.get('server_url', 'http://localhost:8081')
        self.local_server = self.config.get('local_server', True)
        self.timeout = self.config.get('timeout', 30)
        self.max_text_length = self.config.get('max_text_length', 20000)
        
        # Rule configuration
        self.disabled_rules = set(self.config.get('disabled_rules', []))
        self.enabled_rules = set(self.config.get('enabled_rules', []))
        self.disabled_categories = set(self.config.get('disabled_categories', []))
        
        # Performance settings
        self.cache_enabled = self.config.get('cache_enabled', True)
        self.batch_size = self.config.get('batch_size', 10)
        
        # Language tool instances (per language)
        self._tools: Dict[str, any] = {}
        self._initialization_errors: Dict[str, str] = {}
    
    def initialize(self) -> None:
        """Initialize LanguageTool instances for supported languages."""
        super().initialize()
        
        for transqa_lang, lt_lang in self.LANGUAGE_CODES.items():
            try:
                logger.info(f"Initializing LanguageTool for {transqa_lang} ({lt_lang})...")
                
                # Configure LanguageTool
                config_options = {}
                if self.local_server:
                    # Use local server if configured
                    tool = ltp.LanguageToolPublicAPI(lt_lang)
                else:
                    # Use remote server
                    tool = ltp.LanguageToolPublicAPI(lt_lang, host=self.server_url)
                
                # Apply rule configurations
                if self.disabled_rules:
                    tool.disabled_rules = list(self.disabled_rules)
                
                if self.enabled_rules:
                    tool.enabled_rules = list(self.enabled_rules)
                
                if self.disabled_categories:
                    tool.disabled_categories = list(self.disabled_categories)
                
                # Test the connection
                test_result = tool.check("Test.")
                logger.info(f"LanguageTool {transqa_lang} initialized successfully")
                
                self._tools[transqa_lang] = tool
            
            except Exception as e:
                error_msg = f"Failed to initialize LanguageTool for {transqa_lang}: {e}"
                logger.error(error_msg)
                self._initialization_errors[transqa_lang] = error_msg
        
        if not self._tools:
            raise VerificationError(
                f"No LanguageTool instances could be initialized. Errors: {self._initialization_errors}"
            )
        
        logger.info(f"LanguageTool verifier initialized for languages: {list(self._tools.keys())}")
    
    def cleanup(self) -> None:
        """Cleanup LanguageTool resources."""
        super().cleanup()
        
        for lang, tool in self._tools.items():
            try:
                if hasattr(tool, 'close'):
                    tool.close()
                logger.debug(f"Closed LanguageTool for {lang}")
            except Exception as e:
                logger.warning(f"Error closing LanguageTool for {lang}: {e}")
        
        self._tools.clear()
        self._initialization_errors.clear()
    
    def _check_impl(self, text: str, target_lang: str, context: Optional[TextBlock] = None) -> List[Issue]:
        """Check text using LanguageTool."""
        if target_lang not in self._tools:
            logger.warning(f"LanguageTool not available for language: {target_lang}")
            return []
        
        # Split long text if needed
        if len(text) > self.max_text_length:
            return self._check_long_text(text, target_lang, context)
        
        try:
            tool = self._tools[target_lang]
            
            # Perform check
            start_time = time.time()
            matches = tool.check(text)
            check_time = time.time() - start_time
            
            logger.debug(f"LanguageTool check completed in {check_time:.2f}s, found {len(matches)} matches")
            
            # Convert matches to issues
            issues = []
            for match in matches:
                issue = self._convert_match_to_issue(match, text, target_lang)
                if issue:
                    issues.append(issue)
            
            return issues
        
        except Exception as e:
            logger.error(f"LanguageTool check failed for {target_lang}: {e}")
            return []
    
    def _check_long_text(self, text: str, target_lang: str, context: Optional[TextBlock] = None) -> List[Issue]:
        """Check long text by splitting into chunks."""
        issues = []
        
        # Split text into sentences approximately
        sentences = self._split_into_sentences(text)
        
        current_chunk = ""
        current_offset = 0
        
        for sentence in sentences:
            # Add sentence to current chunk
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(test_chunk) <= self.max_text_length:
                current_chunk = test_chunk
            else:
                # Process current chunk
                if current_chunk:
                    chunk_issues = self._check_impl(current_chunk, target_lang, context)
                    # Adjust offsets for chunk issues
                    for issue in chunk_issues:
                        issue.offset_start += current_offset
                        issue.offset_end += current_offset
                    issues.extend(chunk_issues)
                
                # Start new chunk with current sentence
                current_offset += len(current_chunk) + (1 if current_chunk else 0)
                current_chunk = sentence
        
        # Process final chunk
        if current_chunk:
            chunk_issues = self._check_impl(current_chunk, target_lang, context)
            for issue in chunk_issues:
                issue.offset_start += current_offset
                issue.offset_end += current_offset
            issues.extend(chunk_issues)
        
        return issues
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for chunking."""
        # Simple sentence splitting - could be enhanced with proper sentence tokenization
        import re
        
        # Split on sentence endings, but preserve the punctuation
        sentences = re.split(r'([.!?]+\s*)', text)
        
        # Recombine sentence parts
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            if sentence.strip():
                result.append(sentence.strip())
        
        # Handle case where text doesn't end with punctuation
        if sentences and not sentences[-1].strip().endswith(('.', '!', '?')):
            result.append(sentences[-1].strip())
        
        return [s for s in result if s]
    
    def _convert_match_to_issue(self, match, text: str, target_lang: str) -> Optional[Issue]:
        """Convert LanguageTool match to TransQA Issue."""
        try:
            # Determine issue type from category
            category = getattr(match, 'category', 'MISC')
            issue_type = self.CATEGORY_MAPPING.get(category, IssueType.GRAMMAR)
            
            # Get message and suggestion
            message = getattr(match, 'message', 'LanguageTool issue')
            suggestions = getattr(match, 'replacements', [])
            suggestion = suggestions[0] if suggestions else None
            
            # Get position information
            offset = getattr(match, 'offset', 0)
            length = getattr(match, 'length', 1)
            
            # Get rule information
            rule_id = getattr(match, 'ruleId', 'UNKNOWN_RULE')
            
            # Determine severity based on rule category and specific rules
            severity = self._determine_severity(match, category, rule_id)
            
            # Create issue
            issue = Issue(
                type=issue_type,
                severity=severity,
                message=message,
                suggestion=suggestion,
                target_lang=target_lang,
                snippet=text[offset:offset + length],
                xpath="/",  # Will be updated by caller if context available
                offset_start=offset,
                offset_end=offset + length,
                rule_id=rule_id,
                confidence=self._calculate_confidence(match)
            )
            
            return issue
        
        except Exception as e:
            logger.warning(f"Error converting LanguageTool match: {e}")
            return None
    
    def _determine_severity(self, match, category: str, rule_id: str) -> Severity:
        """Determine severity for a LanguageTool match."""
        # Check for critical spelling errors
        if category == 'TYPOS':
            return Severity.ERROR
        
        # Grammar errors are generally warnings
        if category == 'GRAMMAR':
            return Severity.WARNING
        
        # Style issues are info
        if category in ['STYLE', 'TYPOGRAPHY', 'REPETITION', 'REDUNDANCY']:
            return Severity.INFO
        
        # Punctuation is warning
        if category == 'PUNCTUATION':
            return Severity.WARNING
        
        # Capitalization is warning
        if category == 'CASING':
            return Severity.WARNING
        
        # Default based on LanguageTool's internal priority if available
        priority = getattr(match, 'priority', 0)
        if priority >= 100:
            return Severity.ERROR
        elif priority >= 50:
            return Severity.WARNING
        else:
            return Severity.INFO
    
    def _calculate_confidence(self, match) -> float:
        """Calculate confidence score for a match."""
        # Base confidence
        confidence = 0.8
        
        # Adjust based on category
        category = getattr(match, 'category', 'MISC')
        if category == 'TYPOS':
            confidence = 0.9  # High confidence for spelling
        elif category == 'GRAMMAR':
            confidence = 0.8  # Good confidence for grammar
        elif category in ['STYLE', 'TYPOGRAPHY']:
            confidence = 0.6  # Lower confidence for style suggestions
        
        # Adjust based on rule confidence if available
        rule_confidence = getattr(match, 'confidence', None)
        if rule_confidence is not None:
            # LanguageTool confidence is 0-1, combine with our base
            confidence = (confidence + rule_confidence) / 2
        
        return min(1.0, confidence)
    
    def check_grammar(self, text: str, target_lang: str) -> List[Issue]:
        """Check grammar issues specifically."""
        if target_lang not in self._tools:
            return []
        
        try:
            # Temporarily disable non-grammar categories
            tool = self._tools[target_lang]
            original_disabled = getattr(tool, 'disabled_categories', set())
            
            # Disable all categories except grammar
            tool.disabled_categories = list(original_disabled | {
                'TYPOS', 'STYLE', 'TYPOGRAPHY', 'REPETITION', 'REDUNDANCY'
            })
            
            issues = self._check_impl(text, target_lang)
            
            # Restore original settings
            tool.disabled_categories = list(original_disabled)
            
            return [issue for issue in issues if issue.type == IssueType.GRAMMAR]
        
        except Exception as e:
            logger.error(f"Grammar check failed: {e}")
            return []
    
    def check_spelling(self, text: str, target_lang: str) -> List[Issue]:
        """Check spelling issues specifically."""
        if target_lang not in self._tools:
            return []
        
        try:
            # Temporarily enable only spelling
            tool = self._tools[target_lang]
            original_disabled = getattr(tool, 'disabled_categories', set())
            
            # Disable all categories except spelling
            tool.disabled_categories = list(original_disabled | {
                'GRAMMAR', 'STYLE', 'TYPOGRAPHY', 'PUNCTUATION', 'REPETITION', 'REDUNDANCY', 'CASING'
            })
            
            issues = self._check_impl(text, target_lang)
            
            # Restore original settings
            tool.disabled_categories = list(original_disabled)
            
            return [issue for issue in issues if issue.type == IssueType.SPELLING]
        
        except Exception as e:
            logger.error(f"Spelling check failed: {e}")
            return []
    
    def check_style(self, text: str, target_lang: str) -> List[Issue]:
        """Check style issues specifically."""
        if target_lang not in self._tools:
            return []
        
        try:
            # Temporarily enable only style categories
            tool = self._tools[target_lang]
            original_disabled = getattr(tool, 'disabled_categories', set())
            
            # Disable all categories except style-related
            tool.disabled_categories = list(original_disabled | {
                'GRAMMAR', 'TYPOS', 'PUNCTUATION', 'CASING'
            })
            
            issues = self._check_impl(text, target_lang)
            
            # Restore original settings
            tool.disabled_categories = list(original_disabled)
            
            return [issue for issue in issues if issue.type == IssueType.STYLE]
        
        except Exception as e:
            logger.error(f"Style check failed: {e}")
            return []
    
    @staticmethod
    def check_availability() -> dict:
        """Check if LanguageTool is available and get status."""
        result = {
            'available': LANGUAGETOOL_AVAILABLE,
            'languages': {},
        }
        
        if not LANGUAGETOOL_AVAILABLE:
            result['error'] = 'language-tool-python not installed'
            result['install_command'] = 'pip install language-tool-python'
            return result
        
        # Test each language
        for transqa_lang, lt_lang in LanguageToolVerifier.LANGUAGE_CODES.items():
            try:
                # Quick test
                tool = ltp.LanguageToolPublicAPI(lt_lang)
                test_result = tool.check("Test.")
                
                result['languages'][transqa_lang] = {
                    'available': True,
                    'languagetool_code': lt_lang,
                    'test_successful': True,
                }
                
                if hasattr(tool, 'close'):
                    tool.close()
            
            except Exception as e:
                result['languages'][transqa_lang] = {
                    'available': False,
                    'languagetool_code': lt_lang,
                    'error': str(e),
                }
        
        return result
    
    def get_supported_languages(self) -> List[str]:
        """Get list of languages with working LanguageTool instances."""
        return list(self._tools.keys())
    
    def get_statistics(self) -> Dict[str, any]:
        """Get verifier statistics."""
        return {
            'verifier_type': 'LanguageTool',
            'supported_languages': self.get_supported_languages(),
            'initialization_errors': self._initialization_errors,
            'config': {
                'server_url': self.server_url,
                'local_server': self.local_server,
                'timeout': self.timeout,
                'max_text_length': self.max_text_length,
                'disabled_rules_count': len(self.disabled_rules),
                'enabled_rules_count': len(self.enabled_rules),
            }
        }

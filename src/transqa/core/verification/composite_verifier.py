"""Composite verifier that combines multiple verification methods."""

import logging
from typing import List, Optional

from transqa.core.verification.base import BaseVerifier
from transqa.core.interfaces import Issue, TextBlock

logger = logging.getLogger(__name__)


class CompositeVerifier(BaseVerifier):
    """Verifier that combines multiple verification methods for comprehensive checking."""
    
    def __init__(self, verifiers: List[BaseVerifier], config: Optional[dict] = None):
        """Initialize composite verifier with multiple verifiers.
        
        Args:
            verifiers: List of verifier instances
            config: Configuration dictionary
        """
        super().__init__(config)
        
        if not verifiers:
            raise ValueError("At least one verifier must be provided")
        
        self.verifiers = verifiers
        
        # Composite-specific configuration
        self.deduplicate_issues = self.config.get('deduplicate_issues', True)
        self.merge_overlapping = self.config.get('merge_overlapping', True)
        self.parallel_processing = self.config.get('parallel_processing', False)
        
        # Performance tracking
        self.verifier_stats = {}
    
    def initialize(self) -> None:
        """Initialize all component verifiers."""
        super().initialize()
        
        initialized_count = 0
        for i, verifier in enumerate(self.verifiers):
            try:
                verifier.initialize()
                initialized_count += 1
                logger.info(f"Initialized verifier {i}: {verifier.__class__.__name__}")
            except Exception as e:
                logger.warning(f"Failed to initialize verifier {i} ({verifier.__class__.__name__}): {e}")
        
        logger.info(f"Composite verifier initialized with {initialized_count} active verifiers")
    
    def cleanup(self) -> None:
        """Cleanup all component verifiers."""
        super().cleanup()
        
        for verifier in self.verifiers:
            try:
                verifier.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up verifier {verifier.__class__.__name__}: {e}")
    
    def _check_impl(self, text: str, target_lang: str, context: Optional[TextBlock] = None) -> List[Issue]:
        """Run all verifiers and combine results."""
        all_issues = []
        
        # Run each verifier
        for verifier in self.verifiers:
            try:
                verifier_name = verifier.__class__.__name__
                
                # Run verifier
                import time
                start_time = time.time()
                
                issues = verifier.check(text, target_lang, context)
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Track performance
                if verifier_name not in self.verifier_stats:
                    self.verifier_stats[verifier_name] = {
                        'total_checks': 0,
                        'total_issues': 0,
                        'total_time': 0,
                        'avg_time': 0
                    }
                
                stats = self.verifier_stats[verifier_name]
                stats['total_checks'] += 1
                stats['total_issues'] += len(issues)
                stats['total_time'] += duration
                stats['avg_time'] = stats['total_time'] / stats['total_checks']
                
                # Tag issues with source verifier
                for issue in issues:
                    if not hasattr(issue, '_source_verifier'):
                        issue._source_verifier = verifier_name
                
                all_issues.extend(issues)
                
                logger.debug(f"{verifier_name}: {len(issues)} issues in {duration:.3f}s")
            
            except Exception as e:
                logger.error(f"Verifier {verifier.__class__.__name__} failed: {e}")
        
        # Post-process issues
        if self.deduplicate_issues:
            all_issues = self._deduplicate_issues(all_issues)
        
        if self.merge_overlapping:
            all_issues = self._merge_overlapping_issues(all_issues)
        
        return all_issues
    
    def _deduplicate_issues(self, issues: List[Issue]) -> List[Issue]:
        """Remove duplicate issues based on position and type."""
        if not issues:
            return issues
        
        # Group issues by position and type for deduplication
        issue_groups = {}
        
        for issue in issues:
            # Create key based on position and type
            key = (issue.offset_start, issue.offset_end, issue.type, issue.message.lower())
            
            if key not in issue_groups:
                issue_groups[key] = []
            issue_groups[key].append(issue)
        
        # Keep best issue from each group
        deduplicated = []
        for group in issue_groups.values():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Choose best issue based on confidence and source
                best_issue = max(group, key=lambda x: (x.confidence, self._get_verifier_priority(x)))
                
                # Merge information from other issues if useful
                other_issues = [i for i in group if i != best_issue]
                if other_issues:
                    # Combine suggestions if different
                    suggestions = set()
                    if best_issue.suggestion:
                        suggestions.add(best_issue.suggestion)
                    
                    for other in other_issues:
                        if other.suggestion and other.suggestion != best_issue.suggestion:
                            suggestions.add(other.suggestion)
                    
                    if len(suggestions) > 1:
                        best_issue.suggestion = "; ".join(suggestions)
                
                deduplicated.append(best_issue)
        
        logger.debug(f"Deduplicated {len(issues)} -> {len(deduplicated)} issues")
        return deduplicated
    
    def _merge_overlapping_issues(self, issues: List[Issue]) -> List[Issue]:
        """Merge overlapping issues of the same type."""
        if not issues:
            return issues
        
        # Sort issues by position
        issues.sort(key=lambda x: (x.offset_start, x.offset_end))
        
        merged = []
        current_group = []
        
        for issue in issues:
            if not current_group:
                current_group = [issue]
                continue
            
            last_issue = current_group[-1]
            
            # Check if issues overlap and are similar type
            if (issue.offset_start <= last_issue.offset_end and 
                issue.type == last_issue.type and
                abs(issue.offset_start - last_issue.offset_start) < 50):  # Close proximity
                
                current_group.append(issue)
            else:
                # Process current group
                if len(current_group) == 1:
                    merged.append(current_group[0])
                else:
                    merged_issue = self._merge_issue_group(current_group)
                    merged.append(merged_issue)
                
                current_group = [issue]
        
        # Process final group
        if current_group:
            if len(current_group) == 1:
                merged.append(current_group[0])
            else:
                merged_issue = self._merge_issue_group(current_group)
                merged.append(merged_issue)
        
        if len(merged) != len(issues):
            logger.debug(f"Merged {len(issues)} -> {len(merged)} overlapping issues")
        
        return merged
    
    def _merge_issue_group(self, group: List[Issue]) -> Issue:
        """Merge a group of overlapping issues into one."""
        if not group:
            return None
        
        if len(group) == 1:
            return group[0]
        
        # Use the highest confidence issue as base
        base_issue = max(group, key=lambda x: x.confidence)
        
        # Expand position to cover all issues
        min_start = min(issue.offset_start for issue in group)
        max_end = max(issue.offset_end for issue in group)
        
        base_issue.offset_start = min_start
        base_issue.offset_end = max_end
        
        # Combine messages if different
        messages = set(issue.message for issue in group)
        if len(messages) > 1:
            base_issue.message = f"Multiple issues: {'; '.join(messages)}"
        
        # Combine suggestions
        suggestions = set()
        for issue in group:
            if issue.suggestion:
                suggestions.add(issue.suggestion)
        
        if suggestions:
            base_issue.suggestion = "; ".join(suggestions)
        
        # Update snippet to cover merged area
        # Note: This would need access to original text, which we don't have here
        # In practice, the analyzer should handle this
        
        return base_issue
    
    def _get_verifier_priority(self, issue: Issue) -> int:
        """Get priority score for verifier (higher is better)."""
        verifier_priorities = {
            'LanguageToolVerifier': 100,  # Highest priority - most accurate
            'PlaceholderValidator': 90,   # High priority - specific domain
            'HeuristicVerifier': 80,      # Medium priority - broader rules
        }
        
        source_verifier = getattr(issue, '_source_verifier', 'Unknown')
        return verifier_priorities.get(source_verifier, 50)  # Default priority
    
    def check_grammar(self, text: str, target_lang: str) -> List[Issue]:
        """Check grammar using all capable verifiers."""
        issues = []
        
        for verifier in self.verifiers:
            if hasattr(verifier, 'check_grammar'):
                try:
                    verifier_issues = verifier.check_grammar(text, target_lang)
                    issues.extend(verifier_issues)
                except Exception as e:
                    logger.warning(f"Grammar check failed for {verifier.__class__.__name__}: {e}")
        
        return self._deduplicate_issues(issues) if self.deduplicate_issues else issues
    
    def check_spelling(self, text: str, target_lang: str) -> List[Issue]:
        """Check spelling using all capable verifiers."""
        issues = []
        
        for verifier in self.verifiers:
            if hasattr(verifier, 'check_spelling'):
                try:
                    verifier_issues = verifier.check_spelling(text, target_lang)
                    issues.extend(verifier_issues)
                except Exception as e:
                    logger.warning(f"Spelling check failed for {verifier.__class__.__name__}: {e}")
        
        return self._deduplicate_issues(issues) if self.deduplicate_issues else issues
    
    def check_style(self, text: str, target_lang: str) -> List[Issue]:
        """Check style using all capable verifiers."""
        issues = []
        
        for verifier in self.verifiers:
            if hasattr(verifier, 'check_style'):
                try:
                    verifier_issues = verifier.check_style(text, target_lang)
                    issues.extend(verifier_issues)
                except Exception as e:
                    logger.warning(f"Style check failed for {verifier.__class__.__name__}: {e}")
        
        return self._deduplicate_issues(issues) if self.deduplicate_issues else issues
    
    def get_verifier_stats(self) -> dict:
        """Get performance statistics for each verifier."""
        return {
            'verifier_stats': self.verifier_stats,
            'total_verifiers': len(self.verifiers),
            'active_verifiers': len([v for v in self.verifiers if getattr(v, 'is_initialized', True)]),
            'config': {
                'deduplicate_issues': self.deduplicate_issues,
                'merge_overlapping': self.merge_overlapping,
                'parallel_processing': self.parallel_processing,
            }
        }
    
    def get_verifier_info(self) -> List[dict]:
        """Get information about each verifier."""
        info = []
        
        for verifier in self.verifiers:
            verifier_info = {
                'name': verifier.__class__.__name__,
                'initialized': getattr(verifier, 'is_initialized', True),
                'stats': self.verifier_stats.get(verifier.__class__.__name__, {}),
            }
            
            # Add verifier-specific info if available
            if hasattr(verifier, 'get_statistics'):
                try:
                    verifier_info['details'] = verifier.get_statistics()
                except Exception as e:
                    verifier_info['details_error'] = str(e)
            
            info.append(verifier_info)
        
        return info

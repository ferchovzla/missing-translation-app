"""Heuristic-based verifier for language leakage and basic rules."""

import logging
import re
from typing import Dict, List, Optional, Set

from transqa.core.verification.base import BaseVerifier
from transqa.core.interfaces import Issue, IssueType, Severity, TextBlock

logger = logging.getLogger(__name__)


class HeuristicVerifier(BaseVerifier):
    """Heuristic verifier for language leakage detection and basic quality rules."""
    
    # Language-specific character patterns
    LANGUAGE_PATTERNS = {
        'es': {
            'chars': re.compile(r'[ñáéíóúüÑÁÉÍÓÚÜ¿¡]'),
            'words': {'el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'con', 'para', 'una', 'del', 'todo', 'le', 'da', 'su', 'por', 'son', 'pero', 'esto', 'ya', 'muy', 'hacer', 'como', 'fue', 'ser', 'han', 'cuando', 'hasta', 'más', 'desde'},
            'patterns': [
                re.compile(r'\b(?:el|la|los|las)\s+\w+'),  # Articles
                re.compile(r'\b\w+(?:ión|ado|ida|mente)\b'),  # Common endings
            ]
        },
        'en': {
            'chars': re.compile(r'[a-zA-Z]'),  # No specific chars for English
            'words': {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their'},
            'patterns': [
                re.compile(r'\b(?:the|a|an)\s+\w+'),  # Articles
                re.compile(r'\b\w+(?:ing|ed|ly|tion)\b'),  # Common endings
            ]
        },
        'nl': {
            'chars': re.compile(r'[ëïöüÿ]|ij'),
            'words': {'de', 'het', 'een', 'en', 'van', 'te', 'dat', 'die', 'in', 'is', 'hij', 'niet', 'zijn', 'op', 'aan', 'met', 'als', 'voor', 'had', 'er', 'maar', 'om', 'hem', 'dan', 'zou', 'nu', 'wel', 'nog', 'worden', 'bij', 'onder', 'tegen'},
            'patterns': [
                re.compile(r'\b(?:de|het)\s+\w+'),  # Articles
                re.compile(r'\bij\b'),  # Dutch 'ij' digraph
                re.compile(r'\b\w+(?:lijk|heid|tie)\b'),  # Common endings
            ]
        }
    }
    
    # Common false positives (technical terms, brand names, etc.)
    FALSE_POSITIVE_PATTERNS = [
        re.compile(r'\b[A-Z]{2,}\b'),  # Acronyms
        re.compile(r'\b\w*[0-9]\w*\b'),  # Terms with numbers
        re.compile(r'\b(?:https?|www|\.com|\.org|\.net)\b'),  # URLs
        re.compile(r'\b[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+\b'),  # Emails
        re.compile(r'\b(?:API|JSON|XML|HTML|CSS|JS|SQL|HTTP)\b'),  # Technical terms
    ]
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize heuristic verifier."""
        super().__init__(config)
        
        # Configuration
        self.leak_threshold = self.config.get('leak_threshold', 0.08)
        self.min_words_for_detection = self.config.get('min_words_for_detection', 3)
        self.confidence_boost_patterns = self.config.get('confidence_boost_patterns', True)
        self.check_capitalization = self.config.get('check_capitalization', True)
        
        # Whitelist for terms that might appear to be in wrong language
        self.whitelist = set(self.config.get('whitelist', [
            # Common technical terms
            'email', 'online', 'website', 'app', 'software', 'hardware',
            'login', 'logout', 'password', 'username', 'admin', 'user',
            'click', 'download', 'upload', 'submit', 'cancel', 'ok',
            # Brand names
            'google', 'microsoft', 'apple', 'facebook', 'twitter',
            # Common borrowed words
            'blog', 'podcast', 'streaming', 'wifi', 'smartphone',
        ]))
    
    def _check_impl(self, text: str, target_lang: str, context: Optional[TextBlock] = None) -> List[Issue]:
        """Perform heuristic checks on text."""
        issues = []
        
        # Language leakage detection
        issues.extend(self._detect_language_leakage(text, target_lang))
        
        # Capitalization checks
        if self.check_capitalization:
            issues.extend(self._check_capitalization_rules(text, target_lang))
        
        # Punctuation and spacing
        issues.extend(self._check_punctuation_rules(text, target_lang))
        
        # Consistency checks
        issues.extend(self._check_consistency_issues(text, target_lang))
        
        return issues
    
    def _detect_language_leakage(self, text: str, target_lang: str) -> List[Issue]:
        """Detect words/phrases in wrong language."""
        issues = []
        
        if target_lang not in self.LANGUAGE_PATTERNS:
            return issues
        
        # Tokenize text
        words = self._extract_words(text)
        if len(words) < self.min_words_for_detection:
            return issues
        
        # Count language indicators for each language
        language_scores = {}
        word_evidence = {}  # Track which words contributed to each language
        
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            if lang == target_lang:
                continue  # Skip target language in leakage detection
            
            score = 0
            evidence_words = []
            
            # Character-based scoring
            char_matches = patterns['chars'].findall(text)
            char_score = len(char_matches) / max(len(text), 1)
            score += char_score * 0.3
            
            # Word-based scoring
            target_words = patterns['words']
            matching_words = [word for word in words 
                            if word.lower() in target_words and word.lower() not in self.whitelist]
            word_score = len(matching_words) / len(words)
            score += word_score * 0.5
            evidence_words.extend(matching_words)
            
            # Pattern-based scoring
            pattern_matches = 0
            for pattern in patterns['patterns']:
                pattern_matches += len(pattern.findall(text))
            pattern_score = pattern_matches / max(len(words), 1)
            score += pattern_score * 0.2
            
            language_scores[lang] = score
            word_evidence[lang] = evidence_words
        
        # Check if any language exceeds threshold
        for lang, score in language_scores.items():
            if score >= self.leak_threshold:
                evidence = word_evidence[lang]
                
                # Create leakage issue
                confidence = min(0.95, score * 2)  # Convert score to confidence
                
                if evidence:
                    sample_words = evidence[:5]  # Show first 5 words as evidence
                    message = f"Possible {lang.upper()} words detected: {', '.join(sample_words)}"
                    if len(evidence) > 5:
                        message += f" (+{len(evidence)-5} more)"
                else:
                    message = f"Text appears to contain {lang.upper()} content"
                
                issue = self._create_issue(
                    IssueType.LANGUAGE_LEAK,
                    message,
                    text, 0, len(text), target_lang,
                    suggestion=f"Review content - expected {target_lang.upper()} text",
                    rule_id=f"LANGUAGE_LEAK_{lang.upper()}",
                    confidence=confidence
                )
                
                # Store detection details in issue
                issue.detected_lang = lang
                issue.detected_lang_confidence = score
                
                issues.append(issue)
        
        return issues
    
    def _check_capitalization_rules(self, text: str, target_lang: str) -> List[Issue]:
        """Check language-specific capitalization rules."""
        issues = []
        
        # Check sentence capitalization
        sentences = re.split(r'[.!?]+\s*', text)
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence starts with lowercase (excluding special cases)
            first_word = sentence.split()[0] if sentence.split() else ''
            if (first_word and 
                first_word[0].islower() and 
                not self._is_capitalization_exception(first_word, target_lang)):
                
                # Find position in original text
                sentence_start = text.find(sentence)
                if sentence_start != -1:
                    issue = self._create_issue(
                        IssueType.CAPITALIZATION,
                        f"Sentence should start with capital letter: '{first_word}'",
                        text, sentence_start, sentence_start + len(first_word), target_lang,
                        suggestion=first_word.capitalize(),
                        rule_id="SENTENCE_CAPITALIZATION",
                        confidence=0.7
                    )
                    issues.append(issue)
        
        # Language-specific capitalization rules
        if target_lang == 'en':
            # Check title case for potential headings (all caps words)
            title_case_pattern = re.compile(r'\b[A-Z][A-Z\s]+[A-Z]\b')
            for match in title_case_pattern.finditer(text):
                if len(match.group().split()) > 1:  # Multiple words
                    suggestion = ' '.join(word.capitalize() for word in match.group().lower().split())
                    issue = self._create_issue(
                        IssueType.CAPITALIZATION,
                        f"Consider title case instead of all caps: '{match.group()}'",
                        text, match.start(), match.end(), target_lang,
                        suggestion=suggestion,
                        rule_id="ALL_CAPS_TITLE",
                        confidence=0.4  # Low confidence as all caps might be intentional
                    )
                    issues.append(issue)
        
        return issues
    
    def _check_punctuation_rules(self, text: str, target_lang: str) -> List[Issue]:
        """Check language-specific punctuation rules."""
        issues = []
        
        # Check for missing spaces after punctuation
        missing_space_pattern = re.compile(r'[.!?,:;][a-zA-Z]')
        for match in missing_space_pattern.finditer(text):
            issue = self._create_issue(
                IssueType.PUNCTUATION,
                f"Missing space after punctuation: '{match.group()}'",
                text, match.start(), match.end(), target_lang,
                suggestion=match.group()[0] + ' ' + match.group()[1:],
                rule_id="MISSING_SPACE_AFTER_PUNCT",
                confidence=0.8
            )
            issues.append(issue)
        
        # Language-specific punctuation rules
        if target_lang == 'es':
            # Check for missing opening question/exclamation marks
            missing_opening_q = re.compile(r'[^¿]\s*[A-ZÁÉÍÓÚÑÜ][^.!?]*\?')
            for match in missing_opening_q.finditer(text):
                issue = self._create_issue(
                    IssueType.PUNCTUATION,
                    "Spanish question missing opening ¿",
                    text, match.start(), match.end(), target_lang,
                    suggestion="Add ¿ at the beginning of the question",
                    rule_id="MISSING_SPANISH_QUESTION_MARK",
                    confidence=0.6
                )
                issues.append(issue)
            
            missing_opening_e = re.compile(r'[^¡]\s*[A-ZÁÉÍÓÚÑÜ][^.!?]*!')
            for match in missing_opening_e.finditer(text):
                issue = self._create_issue(
                    IssueType.PUNCTUATION,
                    "Spanish exclamation missing opening ¡",
                    text, match.start(), match.end(), target_lang,
                    suggestion="Add ¡ at the beginning of the exclamation",
                    rule_id="MISSING_SPANISH_EXCLAMATION_MARK",
                    confidence=0.6
                )
                issues.append(issue)
        
        return issues
    
    def _check_consistency_issues(self, text: str, target_lang: str) -> List[Issue]:
        """Check for general consistency issues."""
        issues = []
        
        # Check for inconsistent quotation marks
        quotes = re.findall(r'["""\'\'']', text)
        if len(quotes) >= 4:  # At least 2 pairs
            quote_types = set(quotes)
            if len(quote_types) > 2:  # More than 2 different quote types
                issue = self._create_issue(
                    IssueType.CONSISTENCY,
                    f"Inconsistent quotation marks: {', '.join(sorted(quote_types))}",
                    text, 0, len(text), target_lang,
                    suggestion="Use consistent quotation mark style",
                    rule_id="INCONSISTENT_QUOTES",
                    confidence=0.5
                )
                issues.append(issue)
        
        # Check for mixed case in what appears to be a title/heading
        if context and context.tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if re.search(r'[a-z].*[A-Z]|[A-Z].*[a-z].*[A-Z]', text):
                issue = self._create_issue(
                    IssueType.CAPITALIZATION,
                    "Inconsistent capitalization in heading",
                    text, 0, len(text), target_lang,
                    suggestion="Use consistent title case or sentence case",
                    rule_id="INCONSISTENT_HEADING_CASE",
                    confidence=0.4
                )
                issues.append(issue)
        
        return issues
    
    def _extract_words(self, text: str) -> List[str]:
        """Extract alphabetic words from text."""
        # Filter out false positives first
        filtered_text = text
        for pattern in self.FALSE_POSITIVE_PATTERNS:
            filtered_text = pattern.sub(' ', filtered_text)
        
        # Extract words (only alphabetic, minimum length 2)
        words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑëïöüÿ]{2,}\b', filtered_text)
        return words
    
    def _is_capitalization_exception(self, word: str, target_lang: str) -> bool:
        """Check if a word is an exception to capitalization rules."""
        exceptions = {
            'es': {'de', 'del', 'el', 'la', 'y', 'o', 'por', 'para', 'con', 'en'},
            'en': {'a', 'an', 'the', 'and', 'or', 'but', 'for', 'nor', 'so', 'yet', 'in', 'on', 'at', 'to', 'of'},
            'nl': {'de', 'het', 'een', 'en', 'van', 'in', 'op', 'aan', 'met', 'voor', 'door'}
        }
        
        return word.lower() in exceptions.get(target_lang, set())
    
    def detect_leakage(
        self, 
        text: str, 
        target_lang: str, 
        threshold: float = None,
        context: Optional[TextBlock] = None
    ) -> List[Issue]:
        """Detect language leakage with custom threshold."""
        if threshold is not None:
            original_threshold = self.leak_threshold
            self.leak_threshold = threshold
            
            issues = self._detect_language_leakage(text, target_lang)
            
            self.leak_threshold = original_threshold  # Restore original
            return issues
        
        return self._detect_language_leakage(text, target_lang)
    
    def get_language_confidence(self, text: str, target_lang: str) -> Dict[str, float]:
        """Get confidence scores for each language."""
        if target_lang not in self.LANGUAGE_PATTERNS:
            return {}
        
        words = self._extract_words(text)
        if not words:
            return {}
        
        confidence_scores = {}
        
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            
            # Character-based evidence
            char_matches = patterns['chars'].findall(text)
            char_score = len(char_matches) / max(len(text), 1)
            score += char_score * 0.3
            
            # Word-based evidence
            target_words = patterns['words']
            matching_words = [word for word in words 
                            if word.lower() in target_words and word.lower() not in self.whitelist]
            word_score = len(matching_words) / len(words) if words else 0
            score += word_score * 0.5
            
            # Pattern-based evidence
            pattern_matches = 0
            for pattern in patterns['patterns']:
                pattern_matches += len(pattern.findall(text))
            pattern_score = pattern_matches / max(len(words), 1)
            score += pattern_score * 0.2
            
            confidence_scores[lang] = min(1.0, score * 2)  # Scale to 0-1
        
        return confidence_scores

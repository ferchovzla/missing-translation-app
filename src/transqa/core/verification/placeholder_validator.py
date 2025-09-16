"""Placeholder and format validator."""

import logging
import re
from typing import List, Optional, Set

from transqa.core.verification.base import BaseVerifier
from transqa.core.interfaces import Issue, IssueType, Severity, TextBlock

logger = logging.getLogger(__name__)


class PlaceholderValidator(BaseVerifier):
    """Validator for placeholders, numbers, and format consistency."""
    
    # Enhanced placeholder patterns with validation rules
    PLACEHOLDER_RULES = {
        'curly_braces': {
            'pattern': re.compile(r'\{([^}]*)\}'),
            'valid_content': re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$'),  # Valid variable names
            'description': 'Curly brace variables {variable}'
        },
        'double_curly': {
            'pattern': re.compile(r'\{\{([^}]*)\}\}'),
            'valid_content': re.compile(r'^[a-zA-Z_][a-zA-Z0-9_.\[\]]*$'),  # Handlebars syntax
            'description': 'Handlebars templates {{variable}}'
        },
        'printf_style': {
            'pattern': re.compile(r'(%[sdifgeEGc%])'),
            'valid_content': re.compile(r'^%[sdifgeEGc%]$'),  # Printf format specifiers
            'description': 'Printf-style placeholders %s, %d'
        },
        'dollar_braces': {
            'pattern': re.compile(r'\$\{([^}]*)\}'),
            'valid_content': re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$'),
            'description': 'Shell/template variables ${variable}'
        },
        'colon_params': {
            'pattern': re.compile(r'(:)([a-zA-Z_][a-zA-Z0-9_]*)'),
            'valid_content': re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$'),
            'description': 'Colon parameters :parameter'
        },
        'angle_brackets': {
            'pattern': re.compile(r'<([^>]*)>'),
            'valid_content': re.compile(r'^[a-zA-Z_][a-zA-Z0-9_\s]*$'),  # Allow spaces for XML-like
            'description': 'Angle bracket placeholders <placeholder>'
        },
    }
    
    # Currency symbols by language
    CURRENCY_SYMBOLS = {
        'es': ['€', '$', '£'],
        'en': ['$', '£', '€'],
        'nl': ['€', '$', '£']
    }
    
    # Quote styles by language
    QUOTE_STYLES = {
        'es': {
            'primary': ['"', '"'],  # Curly quotes preferred
            'secondary': ["'", "'"],
            'incorrect': ['"', "'"]  # Straight quotes less preferred
        },
        'en': {
            'primary': ['"', '"'],  # Curly quotes preferred
            'secondary': ["'", "'"],
            'incorrect': ['"', "'"]  # Straight quotes acceptable but curly preferred
        },
        'nl': {
            'primary': ['"', '"'],
            'secondary': ["'", "'"],
            'incorrect': ['"', "'"]
        }
    }
    
    def __init__(self, config: Optional[dict] = None):
        """Initialize placeholder validator."""
        super().__init__(config)
        
        # Placeholder-specific configuration
        self.strict_placeholder_syntax = self.config.get('strict_placeholder_syntax', True)
        self.check_placeholder_consistency = self.config.get('check_placeholder_consistency', True)
        self.validate_number_formats = self.config.get('validate_number_formats', True)
        self.check_currency_placement = self.config.get('check_currency_placement', True)
        self.validate_quote_styles = self.config.get('validate_quote_styles', False)
        
        # Whitelisted terms that might look like invalid placeholders
        self.placeholder_whitelist = set(self.config.get('placeholder_whitelist', [
            '{enter}', '{tab}', '{space}', '{click}', '{hover}',  # UI instructions
            '<br>', '<hr>', '<b>', '<i>', '<em>', '<strong>',     # HTML tags
            ':)', ':D', ':(', ':P', ':o',                        # Emoticons
        ]))
    
    def _check_impl(self, text: str, target_lang: str, context: Optional[TextBlock] = None) -> List[Issue]:
        """Check text for placeholder and format issues."""
        issues = []
        
        # Check placeholders
        if self.check_placeholder_consistency:
            issues.extend(self._validate_placeholders(text, target_lang))
        
        # Check number formats
        if self.validate_number_formats:
            issues.extend(self._check_number_formats(text, target_lang))
        
        # Check currency placement
        if self.check_currency_placement:
            issues.extend(self._check_currency_formats(text, target_lang))
        
        # Check quote styles
        if self.validate_quote_styles:
            issues.extend(self._check_quote_styles(text, target_lang))
        
        # Check general consistency issues
        issues.extend(self._check_general_consistency(text, target_lang))
        
        return issues
    
    def validate_placeholders(self, text: str, context: Optional[TextBlock] = None) -> List[Issue]:
        """Main placeholder validation entry point."""
        return self._validate_placeholders(text, 'en')  # Default language for interface method
    
    def validate_numbers_and_formats(self, text: str, target_lang: str) -> List[Issue]:
        """Validate number formats and currency symbols."""
        issues = []
        issues.extend(self._check_number_formats(text, target_lang))
        issues.extend(self._check_currency_formats(text, target_lang))
        return issues
    
    def validate_punctuation_spacing(self, text: str, target_lang: str) -> List[Issue]:
        """Validate punctuation and spacing rules."""
        return self._check_punctuation_spacing(text, target_lang)
    
    def _validate_placeholders(self, text: str, target_lang: str) -> List[Issue]:
        """Validate placeholder syntax and consistency."""
        issues = []
        
        # Find all placeholders
        all_placeholders = []
        placeholder_types = set()
        
        for rule_name, rule in self.PLACEHOLDER_RULES.items():
            pattern = rule['pattern']
            
            for match in pattern.finditer(text):
                # Extract content and position
                if rule_name == 'colon_params':
                    # Special handling for colon parameters
                    content = match.group(2)  # Parameter name after colon
                    full_match = match.group(0)
                else:
                    content = match.group(1) if match.groups() else match.group(0)
                    full_match = match.group(0)
                
                start_pos = match.start()
                end_pos = match.end()
                
                # Skip whitelisted placeholders
                if full_match in self.placeholder_whitelist:
                    continue
                
                placeholder_info = {
                    'type': rule_name,
                    'content': content,
                    'full_match': full_match,
                    'start': start_pos,
                    'end': end_pos,
                    'rule': rule
                }
                
                all_placeholders.append(placeholder_info)
                placeholder_types.add(rule_name)
                
                # Validate individual placeholder syntax
                if self.strict_placeholder_syntax:
                    syntax_issues = self._validate_placeholder_syntax(placeholder_info, text, target_lang)
                    issues.extend(syntax_issues)
        
        # Check for mixed placeholder styles
        if len(placeholder_types) > 2:  # Allow some mixing, but flag excessive
            issue = self._create_issue(
                IssueType.PLACEHOLDER,
                f"Mixed placeholder styles detected: {', '.join(sorted(placeholder_types))}",
                text, 0, len(text), target_lang,
                suggestion="Consider using consistent placeholder style throughout text",
                rule_id="MIXED_PLACEHOLDER_STYLES",
                confidence=0.7
            )
            issues.append(issue)
        
        # Check for placeholder pairing (opening/closing)
        issues.extend(self._check_placeholder_pairing(all_placeholders, text, target_lang))
        
        return issues
    
    def _validate_placeholder_syntax(self, placeholder: dict, text: str, target_lang: str) -> List[Issue]:
        """Validate syntax of individual placeholder."""
        issues = []
        
        rule_name = placeholder['type']
        content = placeholder['content']
        full_match = placeholder['full_match']
        start = placeholder['start']
        end = placeholder['end']
        rule = placeholder['rule']
        
        # Check if content is valid
        valid_content_pattern = rule.get('valid_content')
        if valid_content_pattern and content and not valid_content_pattern.match(content):
            if rule_name == 'curly_braces' and not content.strip():
                # Empty placeholder
                issue = self._create_issue(
                    IssueType.PLACEHOLDER,
                    "Empty placeholder - should contain variable name",
                    text, start, end, target_lang,
                    suggestion="Add variable name: {variable_name}",
                    rule_id="EMPTY_PLACEHOLDER",
                    confidence=0.9
                )
                issues.append(issue)
            
            elif rule_name in ['curly_braces', 'dollar_braces'] and not re.match(r'^[a-zA-Z_]', content):
                # Invalid variable name
                issue = self._create_issue(
                    IssueType.PLACEHOLDER,
                    f"Invalid variable name in placeholder: '{content}'",
                    text, start, end, target_lang,
                    suggestion="Variable names should start with letter or underscore",
                    rule_id="INVALID_VARIABLE_NAME",
                    confidence=0.8
                )
                issues.append(issue)
            
            elif rule_name == 'printf_style' and content not in ['%s', '%d', '%i', '%f', '%g', '%e', '%E', '%G', '%c', '%%']:
                # Invalid printf specifier
                issue = self._create_issue(
                    IssueType.PLACEHOLDER,
                    f"Invalid printf format specifier: {content}",
                    text, start, end, target_lang,
                    suggestion="Use valid specifiers: %s (string), %d (integer), %f (float)",
                    rule_id="INVALID_PRINTF_SPECIFIER",
                    confidence=0.9
                )
                issues.append(issue)
        
        # Check for common mistakes
        if rule_name == 'curly_braces' and '{{' in full_match:
            issue = self._create_issue(
                IssueType.PLACEHOLDER,
                f"Mixed bracket styles in placeholder: {full_match}",
                text, start, end, target_lang,
                suggestion="Use either {variable} or {{variable}} consistently",
                rule_id="MIXED_BRACKET_STYLES",
                confidence=0.8
            )
            issues.append(issue)
        
        return issues
    
    def _check_placeholder_pairing(self, placeholders: List[dict], text: str, target_lang: str) -> List[Issue]:
        """Check for unmatched opening/closing placeholders."""
        issues = []
        
        # Group by type for pairing checks
        by_type = {}
        for ph in placeholders:
            type_name = ph['type']
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(ph)
        
        # Check for potential unmatched pairs in angle brackets (HTML-like)
        if 'angle_brackets' in by_type:
            angle_placeholders = by_type['angle_brackets']
            
            # Simple check for unmatched tags
            stack = []
            for ph in sorted(angle_placeholders, key=lambda x: x['start']):
                content = ph['content'].strip()
                
                if content.startswith('/'):
                    # Closing tag
                    tag_name = content[1:]
                    if stack and stack[-1]['tag'] == tag_name:
                        stack.pop()
                    else:
                        # Unmatched closing tag
                        issue = self._create_issue(
                            IssueType.PLACEHOLDER,
                            f"Unmatched closing tag: </{tag_name}>",
                            text, ph['start'], ph['end'], target_lang,
                            suggestion=f"Ensure there's a matching <{tag_name}> tag",
                            rule_id="UNMATCHED_CLOSING_TAG",
                            confidence=0.7
                        )
                        issues.append(issue)
                elif not content.endswith('/'):
                    # Opening tag (not self-closing)
                    stack.append({'tag': content, 'placeholder': ph})
            
            # Check for unmatched opening tags
            for unmatched in stack:
                ph = unmatched['placeholder']
                tag_name = unmatched['tag']
                issue = self._create_issue(
                    IssueType.PLACEHOLDER,
                    f"Unmatched opening tag: <{tag_name}>",
                    text, ph['start'], ph['end'], target_lang,
                    suggestion=f"Add closing tag: </{tag_name}>",
                    rule_id="UNMATCHED_OPENING_TAG",
                    confidence=0.7
                )
                issues.append(issue)
        
        return issues
    
    def _check_number_formats(self, text: str, target_lang: str) -> List[Issue]:
        """Check number format consistency."""
        issues = []
        
        if target_lang not in self.NUMBER_PATTERNS:
            return issues
        
        # Find all numbers
        all_numbers = []
        
        # US format: 1,234.56
        us_pattern = re.compile(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b')
        for match in us_pattern.finditer(text):
            all_numbers.append({
                'text': match.group(),
                'start': match.start(),
                'end': match.end(),
                'format': 'US'
            })
        
        # European format: 1.234,56
        eu_pattern = re.compile(r'\b\d{1,3}(?:\.\d{3})*(?:,\d+)?\b')
        for match in eu_pattern.finditer(text):
            # Avoid double-counting (US format is subset of this)
            if not any(n['start'] <= match.start() < n['end'] for n in all_numbers):
                all_numbers.append({
                    'text': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'format': 'EU'
                })
        
        if len(all_numbers) < 2:
            return issues  # Can't check consistency with fewer than 2 numbers
        
        # Check for format consistency
        formats = [n['format'] for n in all_numbers]
        if len(set(formats)) > 1:
            # Mixed formats detected
            for number in all_numbers:
                expected_format = 'US' if target_lang == 'en' else 'EU'
                if number['format'] != expected_format:
                    suggestion = self._get_number_format_suggestion(number['text'], target_lang)
                    
                    issue = self._create_issue(
                        IssueType.CONSISTENCY,
                        f"Incorrect number format for {target_lang.upper()}: {number['text']}",
                        text, number['start'], number['end'], target_lang,
                        suggestion=suggestion,
                        rule_id=f"INCORRECT_NUMBER_FORMAT_{target_lang.upper()}",
                        confidence=0.8
                    )
                    issues.append(issue)
        
        return issues
    
    def _get_number_format_suggestion(self, number_text: str, target_lang: str) -> str:
        """Get suggestion for correct number format."""
        if target_lang == 'en':
            # Convert to US format: 1,234.56
            if '.' in number_text and ',' in number_text:
                # Assume European format: 1.234,56 -> 1,234.56
                parts = number_text.split(',')
                if len(parts) == 2:
                    integer_part = parts[0].replace('.', ',')
                    decimal_part = parts[1]
                    return f"{integer_part}.{decimal_part}"
            return number_text.replace('.', ',')  # Simple case
        else:
            # Convert to European format: 1.234,56
            if ',' in number_text and '.' in number_text:
                # Assume US format: 1,234.56 -> 1.234,56
                parts = number_text.split('.')
                if len(parts) == 2:
                    integer_part = parts[0].replace(',', '.')
                    decimal_part = parts[1]
                    return f"{integer_part},{decimal_part}"
            return number_text.replace(',', '.')  # Simple case
    
    def _check_currency_formats(self, text: str, target_lang: str) -> List[Issue]:
        """Check currency symbol placement and format."""
        issues = []
        
        if target_lang not in self.CURRENCY_SYMBOLS:
            return issues
        
        expected_symbols = self.CURRENCY_SYMBOLS[target_lang]
        
        # Find currency patterns
        currency_pattern = re.compile(r'([€$£¥₹])\s*(\d[\d\s,.]*)|\b(\d[\d\s,.]*)\s*([€$£¥₹])')
        
        for match in currency_pattern.finditer(text):
            symbol_before = match.group(1)
            amount_after = match.group(2)
            amount_before = match.group(3)
            symbol_after = match.group(4)
            
            if symbol_before:
                # Symbol before amount (e.g., $100)
                symbol = symbol_before
                amount = amount_after
                placement = 'before'
            else:
                # Symbol after amount (e.g., 100€)
                symbol = symbol_after
                amount = amount_before
                placement = 'after'
            
            # Check placement conventions
            correct_placement = self._get_correct_currency_placement(symbol, target_lang)
            if placement != correct_placement:
                suggestion = f"{symbol}{amount}" if correct_placement == 'before' else f"{amount}{symbol}"
                
                issue = self._create_issue(
                    IssueType.CONSISTENCY,
                    f"Incorrect currency symbol placement for {target_lang.upper()}: {match.group()}",
                    text, match.start(), match.end(), target_lang,
                    suggestion=suggestion.strip(),
                    rule_id=f"CURRENCY_PLACEMENT_{target_lang.upper()}",
                    confidence=0.7
                )
                issues.append(issue)
        
        return issues
    
    def _get_correct_currency_placement(self, symbol: str, target_lang: str) -> str:
        """Get correct currency symbol placement for language."""
        # General rules (simplified)
        if symbol == '$':
            return 'before'  # $100 in most cases
        elif symbol == '€':
            if target_lang == 'en':
                return 'before'  # €100 in English
            else:
                return 'after'   # 100€ in Spanish/Dutch
        elif symbol == '£':
            return 'before'  # £100
        else:
            return 'before'  # Default
    
    def _check_quote_styles(self, text: str, target_lang: str) -> List[Issue]:
        """Check quote style consistency."""
        issues = []
        
        if target_lang not in self.QUOTE_STYLES:
            return issues
        
        quote_rules = self.QUOTE_STYLES[target_lang]
        
        # Find all quotes
        quote_pattern = re.compile(r'["""\'\'']')
        quotes = list(quote_pattern.finditer(text))
        
        if len(quotes) < 2:
            return issues  # Need pairs to check
        
        # Check for straight quotes in languages that prefer curly
        straight_quotes = ['"', "'"]
        for match in quotes:
            quote_char = match.group()
            if quote_char in straight_quotes:
                issue = self._create_issue(
                    IssueType.STYLE,
                    f"Consider using typographic quotes instead of straight quotes: {quote_char}",
                    text, match.start(), match.end(), target_lang,
                    suggestion="Use curly quotes for better typography",
                    rule_id="STRAIGHT_QUOTES",
                    confidence=0.3  # Low confidence as this is often acceptable
                )
                issues.append(issue)
        
        return issues
    
    def _check_general_consistency(self, text: str, target_lang: str) -> List[Issue]:
        """Check general format consistency issues."""
        issues = []
        
        # Check for multiple spaces
        multiple_spaces = re.compile(r'  +')
        for match in multiple_spaces.finditer(text):
            issue = self._create_issue(
                IssueType.PUNCTUATION,
                f"Multiple consecutive spaces: {len(match.group())} spaces",
                text, match.start(), match.end(), target_lang,
                suggestion="Use single space",
                rule_id="MULTIPLE_SPACES",
                confidence=0.8
            )
            issues.append(issue)
        
        # Check for tabs mixed with spaces (if text contains both)
        if '\t' in text and ' ' in text:
            # This is often intentional, so low confidence
            issue = self._create_issue(
                IssueType.CONSISTENCY,
                "Mixed tabs and spaces detected",
                text, 0, len(text), target_lang,
                suggestion="Use consistent indentation (either tabs or spaces)",
                rule_id="MIXED_TABS_SPACES",
                confidence=0.4
            )
            issues.append(issue)
        
        # Check for inconsistent line endings (if multiple lines)
        if '\r\n' in text and '\n' in text.replace('\r\n', ''):
            issue = self._create_issue(
                IssueType.CONSISTENCY,
                "Mixed line endings detected (CRLF and LF)",
                text, 0, len(text), target_lang,
                suggestion="Use consistent line endings",
                rule_id="MIXED_LINE_ENDINGS",
                confidence=0.6
            )
            issues.append(issue)
        
        return issues

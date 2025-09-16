"""Factory for creating verifier instances."""

import logging
from typing import Dict, List, Optional

from transqa.core.verification.base import BaseVerifier
from transqa.core.verification.composite_verifier import CompositeVerifier
from transqa.core.verification.heuristic_verifier import HeuristicVerifier
from transqa.core.verification.placeholder_validator import PlaceholderValidator
from transqa.core.interfaces import ConfigurationError

logger = logging.getLogger(__name__)

# Lazy imports to handle optional dependencies
def _get_languagetool_verifier():
    """Lazy import of LanguageToolVerifier to handle optional dependency."""
    try:
        from transqa.core.verification.languagetool_verifier import LanguageToolVerifier
        return LanguageToolVerifier
    except ImportError:
        return None


class VerifierFactory:
    """Factory for creating appropriate verifier instances."""
    
    @staticmethod
    def create_verifier(
        verifier_type: str = "auto",
        config: Optional[dict] = None
    ) -> BaseVerifier:
        """Create appropriate verifier instance.
        
        Args:
            verifier_type: Type of verifier ('auto', 'languagetool', 'heuristic', 'placeholder', 'composite')
            config: Configuration dictionary
            
        Returns:
            Configured verifier instance
            
        Raises:
            ConfigurationError: If requested verifier is not available
        """
        config = config or {}
        
        if verifier_type == "auto":
            return VerifierFactory._create_best_available(config)
        
        elif verifier_type == "languagetool":
            LanguageToolVerifier = _get_languagetool_verifier()
            if LanguageToolVerifier is None:
                raise ConfigurationError(
                    "LanguageTool verifier requested but not available. "
                    "Install with: pip install language-tool-python"
                )
            return LanguageToolVerifier(config)
        
        elif verifier_type == "heuristic":
            return HeuristicVerifier(config)
        
        elif verifier_type == "placeholder":
            return PlaceholderValidator(config)
        
        elif verifier_type == "composite":
            return VerifierFactory._create_composite_verifier(config)
        
        else:
            raise ConfigurationError(f"Unknown verifier type: {verifier_type}")
    
    @staticmethod
    def _create_best_available(config: dict) -> BaseVerifier:
        """Create the best available verifier automatically."""
        available_verifiers = VerifierFactory.get_available_verifiers()
        
        # If multiple verifiers available, create composite for best results
        available_count = sum(1 for available in available_verifiers.values() if available)
        
        if available_count > 1:
            logger.info("Creating composite verifier with all available components")
            return VerifierFactory._create_composite_verifier(config)
        
        # Single verifier - choose best available
        elif available_verifiers.get("languagetool", False):
            logger.info("Creating LanguageTool verifier")
            LanguageToolVerifier = _get_languagetool_verifier()
            return LanguageToolVerifier(config)
        
        elif available_verifiers.get("heuristic", False):
            logger.info("Creating heuristic verifier")
            return HeuristicVerifier(config)
        
        elif available_verifiers.get("placeholder", False):
            logger.info("Creating placeholder validator")
            return PlaceholderValidator(config)
        
        else:
            raise ConfigurationError(
                "No verifiers available. This should not happen as heuristic and placeholder "
                "verifiers are always available."
            )
    
    @staticmethod
    def _create_composite_verifier(config: dict) -> CompositeVerifier:
        """Create composite verifier with all available verifiers."""
        verifiers = []
        
        # Try to create each verifier
        # 1. LanguageTool (if available)
        LanguageToolVerifier = _get_languagetool_verifier()
        if LanguageToolVerifier:
            try:
                lt_config = config.get('languagetool', {})
                verifiers.append(LanguageToolVerifier(lt_config))
                logger.info("Added LanguageTool verifier to composite")
            except Exception as e:
                logger.warning(f"Failed to create LanguageTool verifier: {e}")
        
        # 2. Placeholder Validator (always available)
        try:
            placeholder_config = config.get('placeholder', {})
            verifiers.append(PlaceholderValidator(placeholder_config))
            logger.info("Added placeholder validator to composite")
        except Exception as e:
            logger.warning(f"Failed to create placeholder validator: {e}")
        
        # 3. Heuristic Verifier (always available)
        try:
            heuristic_config = config.get('heuristic', {})
            verifiers.append(HeuristicVerifier(heuristic_config))
            logger.info("Added heuristic verifier to composite")
        except Exception as e:
            logger.warning(f"Failed to create heuristic verifier: {e}")
        
        if not verifiers:
            raise ConfigurationError("No verifiers could be created for composite verifier")
        
        # Configure composite verifier
        composite_config = config.get('composite', {
            'deduplicate_issues': True,
            'merge_overlapping': True,
            'parallel_processing': False,
        })
        
        return CompositeVerifier(verifiers, composite_config)
    
    @staticmethod
    def create_from_config(app_config) -> BaseVerifier:
        """Create verifier from TransQA configuration object.
        
        Args:
            app_config: TransQAConfig instance
            
        Returns:
            Configured verifier instance
        """
        # Extract configuration for each verifier type
        verifier_config = {
            # LanguageTool configuration
            'languagetool': {
                'server_url': app_config.languagetool.server_url,
                'local_server': app_config.languagetool.local_server,
                'timeout': app_config.languagetool.timeout,
                'disabled_rules': app_config.languagetool.disabled_rules,
                'enabled_rules': app_config.languagetool.enabled_rules,
                'disabled_categories': [],  # Can be added to config if needed
            },
            
            # Placeholder validator configuration
            'placeholder': {
                'strict_placeholder_syntax': True,
                'check_placeholder_consistency': True,
                'validate_number_formats': True,
                'check_currency_placement': True,
                'validate_quote_styles': False,  # Often too strict
            },
            
            # Heuristic verifier configuration
            'heuristic': {
                'leak_threshold': app_config.rules.leak_threshold,
                'min_words_for_detection': 3,
                'confidence_boost_patterns': True,
                'check_capitalization': True,
                'whitelist': [],  # Could load from whitelist file
            },
            
            # Composite configuration
            'composite': {
                'deduplicate_issues': True,
                'merge_overlapping': True,
                'parallel_processing': False,
            },
            
            # Base configuration for all verifiers
            'severity_mapping': {
                'grammar': 'warning',
                'spelling': 'error',
                'style': 'info',
                'placeholder': 'error',
                'language_leak': 'error',
                'punctuation': 'warning',
                'capitalization': 'warning',
            },
            'skip_urls': True,
            'skip_emails': True,
            'min_text_length': 3,
        }
        
        # Load whitelist if available
        whitelist_path = app_config.get_whitelist_path()
        if whitelist_path and whitelist_path.exists():
            try:
                with open(whitelist_path, 'r', encoding='utf-8') as f:
                    whitelist_terms = []
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Handle language-specific terms (term:lang format)
                            if ':' in line:
                                term, lang = line.split(':', 1)
                                whitelist_terms.append(term.strip())
                            else:
                                whitelist_terms.append(line)
                    
                    verifier_config['heuristic']['whitelist'] = whitelist_terms
                    logger.info(f"Loaded {len(whitelist_terms)} whitelist terms")
            
            except Exception as e:
                logger.warning(f"Failed to load whitelist from {whitelist_path}: {e}")
        
        return VerifierFactory.create_verifier('auto', verifier_config)
    
    @staticmethod
    def get_available_verifiers() -> Dict[str, bool]:
        """Get information about available verifiers.
        
        Returns:
            Dictionary mapping verifier names to availability status
        """
        LanguageToolVerifier = _get_languagetool_verifier()
        
        return {
            'languagetool': LanguageToolVerifier is not None,
            'heuristic': True,  # Always available
            'placeholder': True,  # Always available
            'composite': True,  # Always available (depends on components)
        }
    
    @staticmethod
    def check_dependencies(verbose: bool = False) -> Dict[str, Dict[str, any]]:
        """Check verifier dependencies and capabilities.
        
        Args:
            verbose: Whether to include detailed information
            
        Returns:
            Dictionary with dependency information
        """
        results = {}
        
        # Check LanguageTool
        LanguageToolVerifier = _get_languagetool_verifier()
        if LanguageToolVerifier:
            try:
                lt_status = LanguageToolVerifier.check_availability()
                results['languagetool'] = {
                    'available': True,
                    'status': lt_status,
                    'capabilities': [
                        'grammar_checking',
                        'spelling_checking',
                        'style_checking',
                        'multi_language',
                        'rule_customization'
                    ],
                    'limitations': [
                        'requires_java_or_server',
                        'slower_than_heuristics',
                        'internet_for_full_features'
                    ]
                }
            except Exception as e:
                results['languagetool'] = {
                    'available': False,
                    'error': str(e),
                    'install_command': 'pip install language-tool-python'
                }
        else:
            results['languagetool'] = {
                'available': False,
                'error': 'Module not found',
                'install_command': 'pip install language-tool-python'
            }
        
        # Check Heuristic Verifier (always available)
        results['heuristic'] = {
            'available': True,
            'capabilities': [
                'language_leakage_detection',
                'capitalization_rules',
                'punctuation_rules',
                'consistency_checking',
                'fast_processing'
            ],
            'limitations': [
                'rule_based_only',
                'may_have_false_positives',
                'less_sophisticated_than_languagetool'
            ]
        }
        
        # Check Placeholder Validator (always available)
        results['placeholder'] = {
            'available': True,
            'capabilities': [
                'placeholder_validation',
                'number_format_checking',
                'currency_placement',
                'quote_consistency',
                'format_consistency'
            ],
            'limitations': [
                'specific_to_placeholders',
                'may_flag_intentional_formatting'
            ]
        }
        
        # Summary
        available_count = sum(1 for verifier, info in results.items() 
                             if info.get('available', False))
        
        results['summary'] = {
            'total_verifiers': len(results),
            'available_verifiers': available_count,
            'recommended_setup': []
        }
        
        if not results.get('languagetool', {}).get('available', False):
            results['summary']['recommended_setup'].append('pip install language-tool-python')
        
        return results
    
    @staticmethod
    def recommend_verifier(
        accuracy_priority: bool = True,
        speed_priority: bool = False,
        offline_mode: bool = False
    ) -> str:
        """Recommend appropriate verifier based on requirements.
        
        Args:
            accuracy_priority: Whether to prioritize accuracy
            speed_priority: Whether to prioritize speed
            offline_mode: Whether to work offline
            
        Returns:
            Recommended verifier name
        """
        available = VerifierFactory.get_available_verifiers()
        
        # If accuracy is most important and LanguageTool is available
        if accuracy_priority and available['languagetool'] and not speed_priority:
            return 'composite'  # Best of all worlds
        
        # If speed is critical or offline mode
        elif speed_priority or offline_mode:
            return 'heuristic'  # Fastest, works offline
        
        # If only specific validation needed
        elif not available['languagetool']:
            return 'composite'  # Combine available verifiers
        
        else:
            # Default to composite for balanced approach
            return 'composite'
    
    @staticmethod
    def create_minimal_verifier(config: Optional[dict] = None) -> BaseVerifier:
        """Create minimal verifier with just essential checks.
        
        This is useful for performance-critical scenarios.
        """
        config = config or {}
        
        # Use heuristic verifier with minimal configuration
        minimal_config = {
            'leak_threshold': config.get('leak_threshold', 0.15),  # Higher threshold = less sensitive
            'check_capitalization': False,  # Skip capitalization checks
            'min_words_for_detection': 5,   # Require more words
        }
        
        return HeuristicVerifier(minimal_config)
    
    @staticmethod
    def create_strict_verifier(config: Optional[dict] = None) -> BaseVerifier:
        """Create strict verifier with all checks enabled.
        
        This provides maximum coverage but may have more false positives.
        """
        config = config or {}
        
        # Create composite with strict settings
        strict_config = {
            'languagetool': {
                'local_server': True,
                'timeout': 60,  # Longer timeout for thorough checking
                'enabled_rules': [],  # Enable all rules
                'disabled_rules': [],  # Don't disable anything
            },
            'heuristic': {
                'leak_threshold': 0.05,  # Very sensitive
                'check_capitalization': True,
                'min_words_for_detection': 2,  # Detect with fewer words
            },
            'placeholder': {
                'strict_placeholder_syntax': True,
                'validate_quote_styles': True,  # Enable even picky checks
                'check_currency_placement': True,
            },
            'composite': {
                'deduplicate_issues': False,  # Keep all issues
                'merge_overlapping': False,   # Don't merge anything
            }
        }
        
        return VerifierFactory.create_verifier('composite', strict_config)

"""Composite language detector that combines multiple detection methods."""

import logging
import statistics
from typing import Dict, List, Optional, Tuple

from transqa.core.language.base import BaseLanguageDetector
from transqa.core.interfaces import LanguageDetectionResult

logger = logging.getLogger(__name__)


class CompositeLanguageDetector(BaseLanguageDetector):
    """Language detector that combines multiple detection methods for better accuracy."""
    
    def __init__(self, detectors: List[BaseLanguageDetector], config: Optional[dict] = None):
        """Initialize composite detector with multiple detectors.
        
        Args:
            detectors: List of language detector instances
            config: Configuration dictionary
        """
        super().__init__(config)
        
        if not detectors:
            raise ValueError("At least one detector must be provided")
        
        self.detectors = detectors
        
        # Composite-specific configuration
        self.voting_method = self.config.get('voting_method', 'weighted')  # 'weighted', 'majority', 'best'
        self.min_detectors = self.config.get('min_detectors', 1)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.3)
        
        # Detector weights for weighted voting
        self.detector_weights = self.config.get('detector_weights', {})
        
        # Performance tracking
        self.detector_performance = {}
    
    def initialize(self) -> None:
        """Initialize all component detectors."""
        super().initialize()
        
        initialized_count = 0
        for i, detector in enumerate(self.detectors):
            try:
                detector.initialize()
                initialized_count += 1
                logger.info(f"Initialized detector {i}: {detector.__class__.__name__}")
            except Exception as e:
                logger.warning(f"Failed to initialize detector {i} ({detector.__class__.__name__}): {e}")
        
        if initialized_count < self.min_detectors:
            raise RuntimeError(f"Only {initialized_count} detectors initialized, minimum required: {self.min_detectors}")
        
        logger.info(f"Composite detector initialized with {initialized_count} active detectors")
    
    def cleanup(self) -> None:
        """Cleanup all component detectors."""
        super().cleanup()
        
        for detector in self.detectors:
            try:
                detector.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up detector {detector.__class__.__name__}: {e}")
    
    def _detect_language_impl(self, text: str) -> Tuple[str, float, List[Tuple[str, float]]]:
        """Detect language using multiple detectors and combine results."""
        detector_results = []
        
        # Get results from all detectors
        for detector in self.detectors:
            try:
                result = detector.detect_block(text)
                if result.detected_language != 'unknown':
                    detector_results.append({
                        'detector': detector.__class__.__name__,
                        'language': result.detected_language,
                        'confidence': result.confidence,
                        'alternatives': result.alternative_languages or []
                    })
            except Exception as e:
                logger.warning(f"Detector {detector.__class__.__name__} failed: {e}")
        
        if not detector_results:
            return 'unknown', 0.0, []
        
        # Combine results based on voting method
        if self.voting_method == 'weighted':
            return self._weighted_voting(detector_results)
        elif self.voting_method == 'majority':
            return self._majority_voting(detector_results)
        elif self.voting_method == 'best':
            return self._best_confidence_voting(detector_results)
        else:
            raise ValueError(f"Unknown voting method: {self.voting_method}")
    
    def _weighted_voting(self, results: List[dict]) -> Tuple[str, float, List[Tuple[str, float]]]:
        """Combine results using weighted voting."""
        language_scores = {}
        total_weight = 0
        
        for result in results:
            detector_name = result['detector']
            language = result['language']
            confidence = result['confidence']
            
            # Get weight for this detector
            weight = self.detector_weights.get(detector_name, 1.0)
            
            # Update performance tracking
            self._update_performance_tracking(detector_name, confidence)
            
            # Add weighted score
            weighted_score = confidence * weight
            
            if language not in language_scores:
                language_scores[language] = {'score': 0, 'weight': 0, 'votes': 0}
            
            language_scores[language]['score'] += weighted_score
            language_scores[language]['weight'] += weight
            language_scores[language]['votes'] += 1
            total_weight += weight
        
        if not language_scores:
            return 'unknown', 0.0, []
        
        # Calculate final scores
        final_scores = []
        for lang, data in language_scores.items():
            if data['weight'] > 0:
                # Average weighted confidence
                avg_confidence = data['score'] / data['weight']
                # Boost score based on number of votes (consensus)
                consensus_boost = min(data['votes'] / len(results), 1.0) * 0.1
                final_score = min(avg_confidence + consensus_boost, 1.0)
                final_scores.append((lang, final_score))
        
        # Sort by score
        final_scores.sort(key=lambda x: x[1], reverse=True)
        
        if not final_scores:
            return 'unknown', 0.0, []
        
        primary_lang, primary_score = final_scores[0]
        alternatives = final_scores[1:5]  # Top 4 alternatives
        
        return primary_lang, primary_score, alternatives
    
    def _majority_voting(self, results: List[dict]) -> Tuple[str, float, List[Tuple[str, float]]]:
        """Combine results using majority voting."""
        language_votes = {}
        
        for result in results:
            language = result['language']
            confidence = result['confidence']
            
            if language not in language_votes:
                language_votes[language] = {'votes': 0, 'confidences': []}
            
            language_votes[language]['votes'] += 1
            language_votes[language]['confidences'].append(confidence)
        
        if not language_votes:
            return 'unknown', 0.0, []
        
        # Find language(s) with most votes
        max_votes = max(data['votes'] for data in language_votes.values())
        winners = [(lang, data) for lang, data in language_votes.items() 
                  if data['votes'] == max_votes]
        
        if len(winners) == 1:
            # Clear winner
            lang, data = winners[0]
            avg_confidence = statistics.mean(data['confidences'])
            
            # Create alternatives from other languages
            alternatives = []
            for other_lang, other_data in language_votes.items():
                if other_lang != lang:
                    other_conf = statistics.mean(other_data['confidences'])
                    alternatives.append((other_lang, other_conf))
            
            alternatives.sort(key=lambda x: x[1], reverse=True)
            return lang, avg_confidence, alternatives[:3]
        
        else:
            # Tie - use confidence as tiebreaker
            best_lang = None
            best_confidence = 0
            
            for lang, data in winners:
                avg_conf = statistics.mean(data['confidences'])
                if avg_conf > best_confidence:
                    best_confidence = avg_conf
                    best_lang = lang
            
            # Create alternatives
            alternatives = []
            for lang, data in language_votes.items():
                if lang != best_lang:
                    avg_conf = statistics.mean(data['confidences'])
                    alternatives.append((lang, avg_conf))
            
            alternatives.sort(key=lambda x: x[1], reverse=True)
            return best_lang, best_confidence, alternatives[:3]
    
    def _best_confidence_voting(self, results: List[dict]) -> Tuple[str, float, List[Tuple[str, float]]]:
        """Use result from detector with highest confidence."""
        if not results:
            return 'unknown', 0.0, []
        
        # Sort by confidence
        results.sort(key=lambda x: x['confidence'], reverse=True)
        best_result = results[0]
        
        # Collect alternatives from all detectors
        all_alternatives = {}
        
        for result in results:
            # Add primary detection as alternative if not the best
            if result != best_result:
                lang = result['language']
                conf = result['confidence']
                if lang not in all_alternatives or all_alternatives[lang] < conf:
                    all_alternatives[lang] = conf
            
            # Add detector's alternatives
            for alt_lang, alt_conf in result['alternatives']:
                if alt_lang not in all_alternatives or all_alternatives[alt_lang] < alt_conf:
                    all_alternatives[alt_lang] = alt_conf
        
        # Convert to list and sort
        alternatives = list(all_alternatives.items())
        alternatives.sort(key=lambda x: x[1], reverse=True)
        
        return best_result['language'], best_result['confidence'], alternatives[:3]
    
    def _update_performance_tracking(self, detector_name: str, confidence: float) -> None:
        """Update performance tracking for a detector."""
        if detector_name not in self.detector_performance:
            self.detector_performance[detector_name] = {
                'total_detections': 0,
                'confidence_sum': 0,
                'avg_confidence': 0
            }
        
        perf = self.detector_performance[detector_name]
        perf['total_detections'] += 1
        perf['confidence_sum'] += confidence
        perf['avg_confidence'] = perf['confidence_sum'] / perf['total_detections']
    
    def get_detector_stats(self) -> Dict[str, dict]:
        """Get performance statistics for each detector."""
        stats = {}
        
        for detector in self.detectors:
            detector_name = detector.__class__.__name__
            stats[detector_name] = {
                'initialized': getattr(detector, '_initialized', False) or getattr(detector, 'is_initialized', False),
                'weight': self.detector_weights.get(detector_name, 1.0),
                'performance': self.detector_performance.get(detector_name, {})
            }
            
            # Add detector-specific info if available
            if hasattr(detector, 'get_model_info'):
                try:
                    stats[detector_name]['model_info'] = detector.get_model_info()
                except Exception as e:
                    stats[detector_name]['model_info_error'] = str(e)
        
        return stats
    
    def get_consensus_threshold(self, text: str) -> float:
        """Get consensus score for a text across all detectors."""
        detector_results = []
        
        for detector in self.detectors:
            try:
                result = detector.detect_block(text)
                if result.detected_language != 'unknown':
                    detector_results.append(result.detected_language)
            except Exception:
                continue
        
        if not detector_results:
            return 0.0
        
        # Calculate consensus as percentage of detectors agreeing on most common language
        from collections import Counter
        lang_counts = Counter(detector_results)
        most_common_count = lang_counts.most_common(1)[0][1]
        
        consensus = most_common_count / len(detector_results)
        return consensus
    
    def update_detector_weights(self, performance_data: Dict[str, float]) -> None:
        """Update detector weights based on performance data.
        
        Args:
            performance_data: Dictionary mapping detector names to performance scores (0-1)
        """
        for detector_name, performance_score in performance_data.items():
            # Convert performance score to weight (higher performance = higher weight)
            weight = max(0.1, min(2.0, performance_score * 2))  # Weight range: 0.1 to 2.0
            self.detector_weights[detector_name] = weight
        
        logger.info(f"Updated detector weights: {self.detector_weights}")

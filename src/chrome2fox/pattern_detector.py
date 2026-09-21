"""
Pattern Detector — Detect repeated repair patterns.

Tracks successful repairs and detects patterns that can be
converted to deterministic transforms.
"""

import json
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RepairPattern:
    """A detected repair pattern."""
    pattern_id: str
    description: str
    chrome_api: str
    firefox_equivalent: str
    evidence_count: int
    success_rate: float
    examples: list[dict[str, Any]] = field(default_factory=list)
    suggested_rule: str = ""
    confidence: float = 0.0


@dataclass
class PatternStats:
    """Statistics for pattern detection."""
    total_repairs: int = 0
    successful_repairs: int = 0
    patterns_detected: int = 0
    rules_generated: int = 0
    api_mappings: dict[str, int] = field(default_factory=dict)
    common_failures: list[dict[str, Any]] = field(default_factory=list)


class PatternDetector:
    """
    Detect repeated repair patterns.
    
    Tracks successful repairs and identifies patterns that
    can be converted to deterministic transforms.
    
    Usage:
        detector = PatternDetector()
        
        # Load existing corpus
        detector.load_corpus("./repair_corpus")
        
        # Analyze a new repair
        pattern = detector.analyze_repair(repair_receipt)
        
        # Get suggested rules
        rules = detector.get_suggested_rules()
    """
    
    def __init__(self, corpus_dir: Path | None = None):
        """
        Initialize pattern detector.
        
        Args:
            corpus_dir: Directory containing repair receipts
        """
        self.corpus_dir = corpus_dir or Path("./repair_corpus")
        self.patterns: dict[str, RepairPattern] = {}
        self.stats = PatternStats()
        self._api_counts: dict[str, int] = defaultdict(int)
        self._repair_history: list[dict[str, Any]] = []
    
    def load_corpus(self, corpus_dir: Path | None = None) -> int:
        """
        Load repair receipts from corpus directory.
        
        Args:
            corpus_dir: Directory containing repair_receipt.json files
            
        Returns:
            Number of receipts loaded
        """
        if corpus_dir:
            self.corpus_dir = corpus_dir
        
        if not self.corpus_dir.exists():
            return 0
        
        count = 0
        
        # Find all repair receipts
        for receipt_path in self.corpus_dir.rglob("repair_receipt.json"):
            try:
                with open(receipt_path, "r", encoding="utf-8") as f:
                    receipt = json.load(f)
                
                self._repair_history.append(receipt)
                self._analyze_receipt(receipt)
                count += 1
                
            except Exception:
                pass
        
        # Calculate stats
        self._calculate_stats()
        
        return count
    
    def analyze_repair(self, repair_receipt: dict[str, Any]) -> list[RepairPattern]:
        """
        Analyze a repair receipt for patterns.
        
        Args:
            repair_receipt: RepairReceipt as dict
            
        Returns:
            List of detected patterns
        """
        detected = []
        
        # Extract API mappings from patches
        api_mappings = self._extract_api_mappings(repair_receipt)
        
        for chrome_api, firefox_api in api_mappings.items():
            pattern_id = self._generate_pattern_id(chrome_api, firefox_api)
            
            if pattern_id in self.patterns:
                # Update existing pattern
                pattern = self.patterns[pattern_id]
                pattern.evidence_count += 1
                
                # Add example
                pattern.examples.append({
                    "extension": repair_receipt.get("extension_name", "unknown"),
                    "verdict": repair_receipt.get("verdict", "UNKNOWN"),
                    "patch_hash": repair_receipt.get("attempts", [{}])[-1].get("patch_hash", "")
                })
                
                # Update success rate
                successful = sum(
                    1 for ex in pattern.examples
                    if ex.get("verdict") == "PASS"
                )
                pattern.success_rate = successful / len(pattern.examples)
                
                # Update confidence
                pattern.confidence = min(1.0, pattern.evidence_count / 5.0)
                
                detected.append(pattern)
            else:
                # Create new pattern
                pattern = RepairPattern(
                    pattern_id=pattern_id,
                    description=f"Replace {chrome_api} with {firefox_api}",
                    chrome_api=chrome_api,
                    firefox_equivalent=firefox_api,
                    evidence_count=1,
                    success_rate=0.0,
                    examples=[{
                        "extension": repair_receipt.get("extension_name", "unknown"),
                        "verdict": repair_receipt.get("verdict", "UNKNOWN"),
                        "patch_hash": repair_receipt.get("attempts", [{}])[-1].get("patch_hash", "")
                    }],
                    suggested_rule=f"{chrome_api} → {firefox_api}",
                    confidence=0.2
                )
                
                self.patterns[pattern_id] = pattern
                detected.append(pattern)
        
        # Store in history
        self._repair_history.append(repair_receipt)
        self._calculate_stats()
        
        return detected
    
    def get_suggested_rules(self, min_confidence: float = 0.6) -> list[RepairPattern]:
        """
        Get suggested deterministic rules.
        
        Args:
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of patterns with confidence >= threshold
        """
        return [
            pattern for pattern in self.patterns.values()
            if pattern.confidence >= min_confidence
        ]
    
    def get_stats(self) -> PatternStats:
        """Get pattern detection statistics."""
        return self.stats
    
    def export_rules(self, output_path: Path) -> int:
        """
        Export suggested rules to a file.
        
        Args:
            output_path: Path to save rules
            
        Returns:
            Number of rules exported
        """
        rules = self.get_suggested_rules(min_confidence=0.6)
        
        rules_data = []
        for rule in rules:
            rules_data.append({
                "pattern_id": rule.pattern_id,
                "description": rule.description,
                "chrome_api": rule.chrome_api,
                "firefox_equivalent": rule.firefox_equivalent,
                "evidence_count": rule.evidence_count,
                "success_rate": rule.success_rate,
                "confidence": rule.confidence,
                "suggested_rule": rule.suggested_rule
            })
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(rules_data, f, indent=2, ensure_ascii=False)
        
        return len(rules_data)
    
    def _extract_api_mappings(self, receipt: dict[str, Any]) -> dict[str, str]:
        """Extract API mappings from repair receipt."""
        mappings = {}
        
        for attempt in receipt.get("attempts", []):
            patch = attempt.get("patch", {})
            for file_patch in patch.get("file_patches", []):
                old_content = file_patch.get("old_content", "")
                new_content = file_patch.get("new_content", "")
                
                # Find chrome.* in old content
                import re
                chrome_apis = re.findall(r'chrome\.(\w+)', old_content)
                
                # Find browser.* in new content
                browser_apis = re.findall(r'browser\.(\w+)', new_content)
                
                # Match by position
                for chrome_api in chrome_apis:
                    for browser_api in browser_apis:
                        if chrome_api == browser_api:
                            mappings[f"chrome.{chrome_api}"] = f"browser.{browser_api}"
        
        return mappings
    
    def _generate_pattern_id(self, chrome_api: str, firefox_api: str) -> str:
        """Generate a unique pattern ID."""
        key = f"{chrome_api}:{firefox_api}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]
    
    def _analyze_receipt(self, receipt: dict[str, Any]) -> None:
        """Analyze a single receipt for patterns."""
        # Track API usage
        for attempt in receipt.get("attempts", []):
            patch = attempt.get("patch", {})
            for file_patch in patch.get("file_patches", []):
                content = file_patch.get("new_content", "")
                
                # Count browser.* APIs
                import re
                apis = re.findall(r'browser\.(\w+)', content)
                for api in apis:
                    self._api_counts[f"browser.{api}"] += 1
    
    def _calculate_stats(self) -> None:
        """Calculate statistics from repair history."""
        self.stats.total_repairs = len(self._repair_history)
        
        # Count successful repairs
        successful = 0
        for receipt in self._repair_history:
            if receipt.get("verdict") == "PASS":
                successful += 1
        
        self.stats.successful_repairs = successful
        self.stats.patterns_detected = len(self.patterns)
        
        # Count rules generated
        rules = self.get_suggested_rules(min_confidence=0.6)
        self.stats.rules_generated = len(rules)
        
        # API mappings
        self.stats.api_mappings = dict(self._api_counts)
        
        # Common failures
        failure_counts = defaultdict(int)
        for receipt in self._repair_history:
            for attempt in receipt.get("attempts", []):
                if not attempt.get("success"):
                    for file_patch in attempt.get("patch", {}).get("file_patches", []):
                        content = file_patch.get("new_content", "")
                        if "chrome." in content:
                            failure_counts["api_mismatch"] += 1
        
        self.stats.common_failures = [
            {"type": k, "count": v}
            for k, v in sorted(failure_counts.items(), key=lambda x: -x[1])[:10]
        ]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "stats": {
                "total_repairs": self.stats.total_repairs,
                "successful_repairs": self.stats.successful_repairs,
                "patterns_detected": self.stats.patterns_detected,
                "rules_generated": self.stats.rules_generated,
                "api_mappings": self.stats.api_mappings,
                "common_failures": self.stats.common_failures
            },
            "patterns": {
                pid: {
                    "description": p.description,
                    "chrome_api": p.chrome_api,
                    "firefox_equivalent": p.firefox_equivalent,
                    "evidence_count": p.evidence_count,
                    "success_rate": p.success_rate,
                    "confidence": p.confidence,
                    "suggested_rule": p.suggested_rule
                }
                for pid, p in self.patterns.items()
            }
        }


def detect_patterns(
    corpus_dir: Path,
    output_path: Path | None = None
) -> dict[str, Any]:
    """
    Convenience function to detect patterns from a corpus.
    
    Args:
        corpus_dir: Directory containing repair receipts
        output_path: Optional path to save results
        
    Returns:
        Pattern detection results
    """
    detector = PatternDetector(corpus_dir)
    count = detector.load_corpus()
    
    results = {
        "receipts_loaded": count,
        "stats": detector.get_stats().__dict__,
        "suggested_rules": [
            {
                "pattern_id": p.pattern_id,
                "description": p.description,
                "chrome_api": p.chrome_api,
                "firefox_equivalent": p.firefox_equivalent,
                "evidence_count": p.evidence_count,
                "confidence": p.confidence
            }
            for p in detector.get_suggested_rules()
        ]
    }
    
    if output_path:
        detector.export_rules(output_path)
    
    return results


if __name__ == "__main__":
    print("Pattern Detector for Chrome-to-Fox")
    print("=" * 60)
    print("Detects repeated repair patterns")
    print("\nUsage:")
    print("  from chrome2fox.pattern_detector import PatternDetector")
    print("  detector = PatternDetector()")
    print("  detector.load_corpus('./repair_corpus')")
    print("  rules = detector.get_suggested_rules()")

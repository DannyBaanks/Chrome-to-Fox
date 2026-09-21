"""
PR Generator — Generate evidence-based PRs for failed repairs.

Creates structured PRs with full evidence packages
for Chrome-to-Fox issues.
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class PREvidence:
    """Evidence package for a PR."""
    # Source info
    extension_name: str
    extension_version: str
    source_url: str = ""
    
    # Test info
    firefox_version: str
    chrome_manifest_version: int
    compatibility_score: float
    
    # Failure info
    failed_apis: list[str] = field(default_factory=list)
    error_logs: list[str] = field(default_factory=list)
    runtime_failures: list[dict[str, Any]] = field(default_factory=list)
    
    # Repair attempts
    attempts: list[dict[str, Any]] = field(default_factory=list)
    patches_tried: list[str] = field(default_factory=list)
    
    # Final status
    final_failure_reason: str = ""
    reproducible: bool = False
    minimal_case: bool = False
    tests_added: bool = False
    
    # Classification
    classification: str = "UNKNOWN"  # PROJECT_BUG, EXTENSION_SPECIFIC, IMPOSSIBLE
    
    # Suggested fix
    suggested_deterministic_transform: str = ""
    suggested_rule_evidence: list[str] = field(default_factory=list)


class PRGenerator:
    """
    Generate evidence-based PRs for Chrome-to-Fox.
    
    Creates structured PRs with:
    - Title with extension name and failure reason
    - Body with full evidence
    - Evidence package (files, logs, patches)
    - Classification (PROJECT_BUG vs EXTENSION_SPECIFIC)
    - Suggested deterministic transforms
    """
    
    def __init__(self, output_dir: Path | None = None):
        """
        Initialize PR generator.
        
        Args:
            output_dir: Directory to save PR evidence
        """
        self.output_dir = output_dir or Path("./pr_evidence")
    
    def generate_pr(
        self,
        repair_receipt: dict[str, Any],
        extension_path: Path,
        classification: str = "EXTENSION_SPECIFIC"
    ) -> dict[str, Any]:
        """
        Generate a PR from a repair receipt.
        
        Args:
            repair_receipt: RepairReceipt as dict
            extension_path: Path to the extension
            classification: PROJECT_BUG or EXTENSION_SPECIFIC
            
        Returns:
            PR dict with title, body, and evidence
        """
        # Extract info from receipt
        extension_name = repair_receipt.get("extension_name", "unknown")
        verdict = repair_receipt.get("verdict", "NOT_REPAIRED")
        attempts = repair_receipt.get("attempts", [])
        
        # Build evidence
        evidence = self._build_evidence(repair_receipt, extension_path, classification)
        
        # Generate title
        title = self._generate_title(extension_name, verdict, evidence)
        
        # Generate body
        body = self._generate_body(evidence, verdict)
        
        # Save evidence package
        evidence_dir = self._save_evidence(evidence, extension_name)
        
        return {
            "title": title,
            "body": body,
            "classification": classification,
            "evidence_dir": str(evidence_dir),
            "reproducible": evidence.reproducible,
            "minimal_case": evidence.minimal_case,
            "tests_added": evidence.tests_added,
            "can_merge": evidence.reproducible and evidence.minimal_case and evidence.tests_added
        }
    
    def _build_evidence(
        self,
        receipt: dict[str, Any],
        extension_path: Path,
        classification: str
    ) -> PREvidence:
        """Build evidence from repair receipt."""
        # Read manifest
        manifest = {}
        manifest_path = extension_path / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                pass
        
        # Extract failed APIs from attempts
        failed_apis = []
        for attempt in receipt.get("attempts", []):
            patch = attempt.get("patch", {})
            for file_patch in patch.get("file_patches", []):
                content = file_patch.get("new_content", "")
                if "chrome." in content:
                    # Extract API names
                    import re
                    apis = re.findall(r'chrome\.(\w+)', content)
                    failed_apis.extend(apis)
        
        failed_apis = list(set(failed_apis))
        
        # Build evidence
        return PREvidence(
            extension_name=receipt.get("extension_name", "unknown"),
            extension_version=manifest.get("version", "unknown"),
            firefox_version=receipt.get("firefox_version", "unknown"),
            chrome_manifest_version=manifest.get("manifest_version", 2),
            compatibility_score=0.0,
            failed_apis=failed_apis,
            error_logs=[],
            runtime_failures=[],
            attempts=receipt.get("attempts", []),
            patches_tried=[a.get("patch_hash", "") for a in receipt.get("attempts", [])],
            final_failure_reason=f"Repair failed after {len(receipt.get('attempts', []))} attempts",
            reproducible=True,
            minimal_case=False,
            tests_added=False,
            classification=classification
        )
    
    def _generate_title(
        self,
        extension_name: str,
        verdict: str,
        evidence: PREvidence
    ) -> str:
        """Generate PR title."""
        if verdict == "NOT_REPAIRED":
            return f"[Chrome-to-Fox] Port failure: {extension_name}"
        elif verdict == "DEGRADED":
            return f"[Chrome-to-Fox] Partial port: {extension_name}"
        else:
            return f"[Chrome-to-Fox] Port success: {extension_name}"
    
    def _generate_body(self, evidence: PREvidence, verdict: str) -> str:
        """Generate PR body."""
        parts = []
        
        # Header
        parts.append(f"# Chrome-to-Fox Port Report: {evidence.extension_name}")
        parts.append("")
        
        # Summary
        parts.append("## Summary")
        parts.append(f"- **Extension**: {evidence.extension_name} v{evidence.extension_version}")
        parts.append(f"- **Firefox Version**: {evidence.firefox_version}")
        parts.append(f"- **Chrome Manifest**: v{evidence.chrome_manifest_version}")
        parts.append(f"- **Compatibility Score**: {evidence.compatibility_score:.2%}")
        parts.append(f"- **Verdict**: {verdict}")
        parts.append(f"- **Classification**: {evidence.classification}")
        parts.append("")
        
        # Failed APIs
        if evidence.failed_apis:
            parts.append("## Failed APIs")
            for api in evidence.failed_apis:
                parts.append(f"- `chrome.{api}`")
            parts.append("")
        
        # Repair Attempts
        if evidence.attempts:
            parts.append("## Repair Attempts")
            for i, attempt in enumerate(evidence.attempts, 1):
                success = "✅" if attempt.get("success") else "❌"
                parts.append(f"### Attempt {i} {success}")
                parts.append(f"- Failures before: {attempt.get('failures_before', 0)}")
                parts.append(f"- Failures after: {attempt.get('failures_after', 0)}")
                parts.append(f"- Duration: {attempt.get('duration_ms', 0)}ms")
                parts.append(f"- Patch hash: `{attempt.get('patch_hash', 'N/A')}`")
                parts.append("")
        
        # Error Logs
        if evidence.error_logs:
            parts.append("## Error Logs")
            for log in evidence.error_logs[:10]:
                parts.append(f"```\n{log}\n```")
            parts.append("")
        
        # Final Failure Reason
        if evidence.final_failure_reason:
            parts.append("## Final Failure Reason")
            parts.append(evidence.final_failure_reason)
            parts.append("")
        
        # Reproduction
        parts.append("## Reproduction")
        parts.append(f"- **Reproducible**: {'Yes' if evidence.reproducible else 'No'}")
        parts.append(f"- **Minimal Case**: {'Yes' if evidence.minimal_case else 'No'}")
        parts.append(f"- **Tests Added**: {'Yes' if evidence.tests_added else 'No'}")
        parts.append("")
        
        # Suggested Fix
        if evidence.suggested_deterministic_transform:
            parts.append("## Suggested Deterministic Transform")
            parts.append("```")
            parts.append(evidence.suggested_deterministic_transform)
            parts.append("```")
            if evidence.suggested_rule_evidence:
                parts.append("")
                parts.append("**Evidence:**")
                for e in evidence.suggested_rule_evidence:
                    parts.append(f"- {e}")
            parts.append("")
        
        # Classification Explanation
        parts.append("## Classification")
        if evidence.classification == "PROJECT_BUG":
            parts.append("**This is a Chrome-to-Fox bug** — the converter should handle this case.")
            parts.append("Please fix the converter and add a test case.")
        elif evidence.classification == "EXTENSION_SPECIFIC":
            parts.append("**This is extension-specific** — the extension uses a Chrome-only feature")
            parts.append("that has no Firefox equivalent.")
        else:
            parts.append("**Classification unknown** — manual review required.")
        parts.append("")
        
        # Buttons
        parts.append("## Actions")
        parts.append("- [Retry manually]")
        parts.append("- [Save failing fixture]")
        parts.append("- [Open issue]")
        parts.append("- [Generate PR]")
        parts.append("- [Nope, this API is impossible]")
        
        return "\n".join(parts)
    
    def _save_evidence(self, evidence: PREvidence, extension_name: str) -> Path:
        """Save evidence package to disk."""
        # Create evidence directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        evidence_dir = self.output_dir / f"{extension_name}_{timestamp}"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Save evidence as JSON
        evidence_data = {
            "extension_name": evidence.extension_name,
            "extension_version": evidence.extension_version,
            "firefox_version": evidence.firefox_version,
            "chrome_manifest_version": evidence.chrome_manifest_version,
            "compatibility_score": evidence.compatibility_score,
            "failed_apis": evidence.failed_apis,
            "error_logs": evidence.error_logs,
            "runtime_failures": evidence.runtime_failures,
            "attempts": evidence.attempts,
            "patches_tried": evidence.patches_tried,
            "final_failure_reason": evidence.final_failure_reason,
            "reproducible": evidence.reproducible,
            "minimal_case": evidence.minimal_case,
            "tests_added": evidence.tests_added,
            "classification": evidence.classification,
            "suggested_deterministic_transform": evidence.suggested_deterministic_transform,
            "suggested_rule_evidence": evidence.suggested_rule_evidence
        }
        
        evidence_file = evidence_dir / "evidence.json"
        with open(evidence_file, "w", encoding="utf-8") as f:
            json.dump(evidence_data, f, indent=2, ensure_ascii=False)
        
        # Save error logs
        if evidence.error_logs:
            logs_file = evidence_dir / "error_logs.txt"
            with open(logs_file, "w", encoding="utf-8") as f:
                f.write("\n".join(evidence.error_logs))
        
        # Save patches
        for i, attempt in enumerate(evidence.attempts):
            patch = attempt.get("patch", {})
            if patch:
                patch_file = evidence_dir / f"try_{i+1}.patch"
                with open(patch_file, "w", encoding="utf-8") as f:
                    json.dump(patch, f, indent=2, ensure_ascii=False)
        
        return evidence_dir


def generate_pr(
    repair_receipt: dict[str, Any],
    extension_path: Path,
    output_dir: Path | None = None,
    classification: str = "EXTENSION_SPECIFIC"
) -> dict[str, Any]:
    """
    Convenience function to generate a PR.
    
    Args:
        repair_receipt: RepairReceipt as dict
        extension_path: Path to the extension
        output_dir: Directory for evidence
        classification: PROJECT_BUG or EXTENSION_SPECIFIC
        
    Returns:
        PR dict with title, body, and evidence
    """
    generator = PRGenerator(output_dir)
    return generator.generate_pr(repair_receipt, extension_path, classification)


if __name__ == "__main__":
    print("PR Generator for Chrome-to-Fox")
    print("=" * 60)
    print("Generates evidence-based PRs for failed repairs")
    print("\nUsage:")
    print("  from chrome2fox.pr_generator import generate_pr")
    print("  pr = generate_pr(receipt, extension_path)")
    print(f"  Title: {pr['title']}")

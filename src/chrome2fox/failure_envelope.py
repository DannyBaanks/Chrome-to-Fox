"""
Failure Envelope — Normalize test failures for LLM consumption.

Takes raw test results and produces a structured envelope
that the LLM can use to generate targeted patches.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FailureCategory:
    """A category of failures."""
    category: str  # manifest, runtime, permissions, api_mismatch, behavior
    failures: list[dict[str, Any]] = field(default_factory=list)
    severity: str = "error"  # error, warning, info


@dataclass
class FailureEnvelope:
    """
    Normalized failure envelope for LLM consumption.
    
    Contains all the information an LLM needs to understand
    what went wrong and generate a targeted fix.
    """
    # Source info
    extension_name: str
    extension_version: str
    chrome_manifest_version: int
    firefox_version: str
    
    # Conversion info
    original_hash: str
    converted_hash: str
    compatibility_score: float
    
    # Test results
    test_status: str  # pass, fail, error
    test_duration_ms: int
    
    # Failures by category
    categories: list[FailureCategory] = field(default_factory=list)
    
    # Specific failures
    manifest_failures: list[dict[str, Any]] = field(default_factory=list)
    runtime_failures: list[dict[str, Any]] = field(default_factory=list)
    permission_failures: list[dict[str, Any]] = field(default_factory=list)
    api_mismatches: list[dict[str, Any]] = field(default_factory=list)
    behavior_mismatches: list[dict[str, Any]] = field(default_factory=list)
    
    # Files involved
    files_involved: list[dict[str, Any]] = field(default_factory=list)
    
    # Diff info
    chrome_to_firefox_diff: str = ""
    
    # Available Firefox APIs
    available_firefox_apis: list[str] = field(default_factory=list)
    
    # Error logs
    error_logs: list[str] = field(default_factory=list)
    console_logs: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "extension_name": self.extension_name,
            "extension_version": self.extension_version,
            "chrome_manifest_version": self.chrome_manifest_version,
            "firefox_version": self.firefox_version,
            "original_hash": self.original_hash,
            "converted_hash": self.converted_hash,
            "compatibility_score": self.compatibility_score,
            "test_status": self.test_status,
            "test_duration_ms": self.test_duration_ms,
            "categories": [
                {
                    "category": c.category,
                    "failures": c.failures,
                    "severity": c.severity
                }
                for c in self.categories
            ],
            "manifest_failures": self.manifest_failures,
            "runtime_failures": self.runtime_failures,
            "permission_failures": self.permission_failures,
            "api_mismatches": self.api_mismatches,
            "behavior_mismatches": self.behavior_mismatches,
            "files_involved": self.files_involved,
            "chrome_to_firefox_diff": self.chrome_to_firefox_diff,
            "available_firefox_apis": self.available_firefox_apis,
            "error_logs": self.error_logs,
            "console_logs": self.console_logs
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def to_prompt(self) -> str:
        """
        Convert to a prompt suitable for LLM consumption.
        
        This produces a structured prompt that tells the LLM
        exactly what went wrong and what files to fix.
        """
        prompt_parts = []
        
        # Header
        prompt_parts.append(f"# Repair Request: {self.extension_name}")
        prompt_parts.append("")
        prompt_parts.append(f"Extension Version: {self.extension_version}")
        prompt_parts.append(f"Chrome Manifest V{self.chrome_manifest_version}")
        prompt_parts.append(f"Firefox Version: {self.firefox_version}")
        prompt_parts.append(f"Compatibility Score: {self.compatibility_score:.2%}")
        prompt_parts.append("")
        
        # Summary
        prompt_parts.append("## Test Result: FAIL")
        prompt_parts.append(f"Duration: {self.test_duration_ms}ms")
        prompt_parts.append("")
        
        # Manifest Failures
        if self.manifest_failures:
            prompt_parts.append("## Manifest Failures")
            for f in self.manifest_failures:
                prompt_parts.append(f"- {f.get('issue', 'Unknown')}: {f.get('details', '')}")
            prompt_parts.append("")
        
        # Runtime Failures
        if self.runtime_failures:
            prompt_parts.append("## Runtime Failures")
            for f in self.runtime_failures:
                prompt_parts.append(f"- {f.get('api', 'Unknown')}: {f.get('error', '')}")
            prompt_parts.append("")
        
        # Permission Failures
        if self.permission_failures:
            prompt_parts.append("## Permission Failures")
            for f in self.permission_failures:
                prompt_parts.append(f"- {f.get('permission', 'Unknown')}: {f.get('issue', '')}")
                if 'suggestion' in f:
                    prompt_parts.append(f"  Suggestion: {f['suggestion']}")
            prompt_parts.append("")
        
        # API Mismatches
        if self.api_mismatches:
            prompt_parts.append("## API Mismatches")
            for f in self.api_mismatches:
                prompt_parts.append(f"- {f.get('api', 'Unknown')} in {f.get('file', 'unknown')}: {f.get('issue', '')}")
            prompt_parts.append("")
        
        # Files Involved
        if self.files_involved:
            prompt_parts.append("## Files Involved")
            for f in self.files_involved:
                prompt_parts.append(f"- {f.get('path', 'unknown')}: {f.get('action', 'unknown')}")
            prompt_parts.append("")
        
        # Available Firefox APIs
        if self.available_firefox_apis:
            prompt_parts.append("## Available Firefox APIs")
            prompt_parts.append(", ".join(self.available_firefox_apis[:20]))
            prompt_parts.append("")
        
        # Error Logs
        if self.error_logs:
            prompt_parts.append("## Error Logs")
            for log in self.error_logs[:10]:
                prompt_parts.append(f"```\n{log}\n```")
            prompt_parts.append("")
        
        # Instructions
        prompt_parts.append("## Instructions")
        prompt_parts.append("Generate a patch that fixes the failures above.")
        prompt_parts.append("The patch should:")
        prompt_parts.append("1. Fix manifest issues for Firefox compatibility")
        prompt_parts.append("2. Replace Chrome-only APIs with Firefox equivalents")
        prompt_parts.append("3. Preserve original functionality as much as possible")
        prompt_parts.append("4. Use available Firefox APIs listed above")
        prompt_parts.append("")
        prompt_parts.append("Return the patch as a JSON object with:")
        prompt_parts.append("- file_patches: list of {path, old_content, new_content}")
        prompt_parts.append("- explanation: what was changed and why")
        
        return "\n".join(prompt_parts)


class FailureEnvelopeBuilder:
    """
    Build a FailureEnvelope from test results.
    """
    
    @staticmethod
    def from_test_result(
        test_result: Any,  # TestResult from test_harness
        extension_path: Path,
        original_hash: str = "",
        converted_hash: str = "",
        compatibility_score: float = 0.0
    ) -> FailureEnvelope:
        """
        Build a FailureEnvelope from a TestResult.
        
        Args:
            test_result: TestResult from test_harness
            extension_path: Path to the extension
            original_hash: Hash of original Chrome extension
            converted_hash: Hash of converted Firefox extension
            compatibility_score: Compatibility score from analyzer
            
        Returns:
            FailureEnvelope with all failure information
        """
        # Read manifest
        manifest = {}
        manifest_path = extension_path / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                pass
        
        # Extract extension info
        extension_name = manifest.get("name", "unknown")
        extension_version = manifest.get("version", "unknown")
        chrome_manifest_version = manifest.get("manifest_version", 2)
        
        # Read Firefox version from test result
        firefox_version = test_result.firefox_version if hasattr(test_result, 'firefox_version') else "unknown"
        
        # Build categories
        categories = []
        
        # Manifest category
        if test_result.permission_errors:
            categories.append(FailureCategory(
                category="permissions",
                failures=test_result.permission_errors,
                severity="error"
            ))
        
        # API mismatch category
        if test_result.api_mismatches:
            categories.append(FailureCategory(
                category="api_mismatch",
                failures=test_result.api_mismatches,
                severity="error"
            ))
        
        # Runtime category
        if test_result.runtime_errors:
            categories.append(FailureCategory(
                category="runtime",
                failures=test_result.runtime_errors,
                severity="error"
            ))
        
        # Collect files involved
        files_involved = []
        
        # Add JS files that were patched
        for js_file in extension_path.rglob("*.js"):
            try:
                content = js_file.read_text(encoding="utf-8")
                if "chrome." in content or "browser." in content:
                    files_involved.append({
                        "path": str(js_file.relative_to(extension_path)),
                        "action": "contains_api_calls",
                        "size": len(content)
                    })
            except Exception:
                pass
        
        # Add manifest
        files_involved.append({
            "path": "manifest.json",
            "action": "manifest",
            "size": manifest_path.stat().st_size if manifest_path.exists() else 0
        })
        
        # Collect error logs
        error_logs = []
        console_logs = []
        
        if hasattr(test_result, 'console_logs'):
            for log in test_result.console_logs:
                msg = log.get('message', '')
                if 'error' in msg.lower() or 'exception' in msg.lower():
                    error_logs.append(msg)
                else:
                    console_logs.append(msg)
        
        # Build envelope
        envelope = FailureEnvelope(
            extension_name=extension_name,
            extension_version=extension_version,
            chrome_manifest_version=chrome_manifest_version,
            firefox_version=firefox_version,
            original_hash=original_hash,
            converted_hash=converted_hash,
            compatibility_score=compatibility_score,
            test_status=test_result.overall_status,
            test_duration_ms=test_result.duration_ms,
            categories=categories,
            manifest_failures=test_result.permission_errors,
            runtime_failures=test_result.runtime_errors,
            permission_failures=test_result.permission_errors,
            api_mismatches=test_result.api_mismatches,
            behavior_mismatches=[],
            files_involved=files_involved,
            available_firefox_apis=[
                "browser.tabs", "browser.storage", "browser.runtime",
                "browser.alarms", "browser.cookies", "browser.action",
                "browser.downloads", "browser.scripting", "browser.sidebarAction",
                "browser.webRequest", "browser.contextMenus", "browser.i18n",
                "browser.notifications", "browser.permissions", "browser.windows",
                "browser.bookmarks", "browser.history", "browser.topSites"
            ],
            error_logs=error_logs,
            console_logs=console_logs
        )
        
        return envelope


def create_failure_envelope(
    test_result: Any,
    extension_path: Path,
    original_hash: str = "",
    converted_hash: str = "",
    compatibility_score: float = 0.0
) -> FailureEnvelope:
    """
    Convenience function to create a failure envelope.
    
    Args:
        test_result: TestResult from test_harness
        extension_path: Path to the extension
        original_hash: Hash of original Chrome extension
        converted_hash: Hash of converted Firefox extension
        compatibility_score: Compatibility score from analyzer
        
    Returns:
        FailureEnvelope
    """
    return FailureEnvelopeBuilder.from_test_result(
        test_result,
        extension_path,
        original_hash,
        converted_hash,
        compatibility_score
    )


if __name__ == "__main__":
    # Test the envelope builder
    print("Failure Envelope Builder")
    print("=" * 60)
    print("This module builds structured failure envelopes for LLM consumption.")
    print("Use create_failure_envelope() to build an envelope from test results.")

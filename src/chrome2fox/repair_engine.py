"""
Repair Engine — Orchestrates the test-fail-repair-retest loop.

Bounded iterations with LLM-powered repairs.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .failure_envelope import FailureEnvelope, create_failure_envelope
from .llm_client import LLMClient, LLMConfig, LLMError


@dataclass
class RepairAttempt:
    """A single repair attempt."""
    attempt_number: int
    patch: dict[str, Any]
    patch_hash: str
    test_status_before: str
    test_status_after: str
    failures_before: int
    failures_after: int
    duration_ms: int
    llm_model: str
    llm_tokens_used: int
    success: bool


@dataclass
class RepairReceipt:
    """
    Repair receipt documenting the entire repair process.
    
    This is the audit trail for debugging and corpus building.
    """
    # Source hashes
    original_hash: str
    converted_hash: str
    final_hash: str
    
    # Test info
    test_suite: str
    firefox_version: str
    extension_name: str
    
    # Repair attempts
    attempts: list[RepairAttempt] = field(default_factory=list)
    
    # Final result
    verdict: str = "UNKNOWN"  # PASS, DEGRADED, NOT_REPAIRED
    
    # LLM info
    model: str = ""
    provider: str = ""
    prompt_contract_version: str = "1.0"
    
    # Timing
    total_duration_ms: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_hash": self.original_hash,
            "converted_hash": self.converted_hash,
            "final_hash": self.final_hash,
            "test_suite": self.test_suite,
            "firefox_version": self.firefox_version,
            "extension_name": self.extension_name,
            "attempts": [
                {
                    "attempt_number": a.attempt_number,
                    "patch_hash": a.patch_hash,
                    "test_status_before": a.test_status_before,
                    "test_status_after": a.test_status_after,
                    "failures_before": a.failures_before,
                    "failures_after": a.failures_after,
                    "duration_ms": a.duration_ms,
                    "llm_model": a.llm_model,
                    "llm_tokens_used": a.llm_tokens_used,
                    "success": a.success
                }
                for a in self.attempts
            ],
            "verdict": self.verdict,
            "model": self.model,
            "provider": self.provider,
            "prompt_contract_version": self.prompt_contract_version,
            "total_duration_ms": self.total_duration_ms
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class RepairEngine:
    """
    Orchestrates the test-fail-repair-retest loop.
    
    Flow:
    1. Test extension in Firefox
    2. If FAIL, build failure envelope
    3. Send envelope to LLM
    4. Apply patch
    5. Retest
    6. Repeat until PASS or max iterations
    
    Usage:
        engine = RepairEngine(
            llm_config=LLMConfig(base_url="...", api_key="...")
        )
        
        receipt = engine.repair(
            extension_path=Path("./output/my-extension"),
            max_attempts=3
        )
        
        print(receipt.verdict)  # PASS, DEGRADED, or NOT_REPAIRED
    """
    
    def __init__(
        self,
        llm_config: LLMConfig | None = None,
        firefox_binary: str | None = None
    ):
        """
        Initialize the repair engine.
        
        Args:
            llm_config: LLM configuration
            firefox_binary: Path to Firefox (optional)
        """
        self.llm_client = LLMClient(config=llm_config) if llm_config else None
        self.firefox_binary = firefox_binary
        
        # Lazy import to avoid circular imports
        self._test_harness = None
    
    def _get_test_harness(self):
        """Get or create test harness."""
        if self._test_harness is None:
            from .test_harness import FirefoxTestHarness
            self._test_harness = FirefoxTestHarness(self.firefox_binary)
        return self._test_harness
    
    def repair(
        self,
        extension_path: Path,
        max_attempts: int = 3,
        verbose: bool = False
    ) -> RepairReceipt:
        """
        Attempt to repair a converted extension.
        
        Args:
            extension_path: Path to the converted extension
            max_attempts: Maximum repair attempts (default 3)
            verbose: Print progress messages
            
        Returns:
            RepairReceipt with full audit trail
        """
        start_time = time.time()
        
        # Read manifest
        manifest = self._read_manifest(extension_path)
        
        # Calculate initial hashes
        original_hash = self._hash_extension(extension_path)
        converted_hash = original_hash  # Same at start
        
        # Initial test
        if verbose:
            print(f"\n{'='*60}")
            print(f"Chrome-to-Fox Repair Engine")
            print(f"{'='*60}")
            print(f"Extension: {manifest.get('name', 'unknown')}")
            print(f"Version: {manifest.get('version', 'unknown')}")
            print(f"Max Attempts: {max_attempts}")
            print(f"\n[1/4] Initial Test...")
        
        test_result = self._test_extension(extension_path, verbose)
        
        if test_result.overall_status == "pass":
            if verbose:
                print(f"\n✅ Extension passes all tests!")
            
            return RepairReceipt(
                original_hash=original_hash,
                converted_hash=converted_hash,
                final_hash=converted_hash,
                test_suite="chrome2fox_v1",
                firefox_version=test_result.firefox_version,
                extension_name=manifest.get("name", "unknown"),
                verdict="PASS",
                total_duration_ms=int((time.time() - start_time) * 1000)
            )
        
        # Build failure envelope
        if verbose:
            print(f"\n[2/4] Building failure envelope...")
        
        envelope = create_failure_envelope(
            test_result,
            extension_path,
            original_hash=original_hash,
            converted_hash=converted_hash,
            compatibility_score=0.0
        )
        
        if verbose:
            print(f"  Failures: {len(envelope.manifest_failures)} manifest, "
                  f"{len(envelope.runtime_failures)} runtime, "
                  f"{len(envelope.api_mismatches)} API")
        
        # Check if LLM is configured
        if not self.llm_client:
            if verbose:
                print(f"\n⚠️  No LLM configured. Cannot repair.")
                print(f"  Use --llm-base-url and --api-key to enable repair.")
            
            return RepairReceipt(
                original_hash=original_hash,
                converted_hash=converted_hash,
                final_hash=converted_hash,
                test_suite="chrome2fox_v1",
                firefox_version=test_result.firefox_version,
                extension_name=manifest.get("name", "unknown"),
                verdict="NOT_REPAIRED",
                total_duration_ms=int((time.time() - start_time) * 1000)
            )
        
        # Repair loop
        attempts = []
        current_path = extension_path
        
        for attempt_num in range(1, max_attempts + 1):
            if verbose:
                print(f"\n[3/4] Repair Attempt {attempt_num}/{max_attempts}...")
            
            attempt_start = time.time()
            
            # Generate patch
            try:
                envelope_dict = envelope.to_dict()
                patch = self.llm_client.generate_patch(envelope_dict)
                
                if verbose:
                    print(f"  Patch generated: {len(patch.get('file_patches', []))} files")
                
            except LLMError as e:
                if verbose:
                    print(f"  ❌ LLM error: {e}")
                
                attempts.append(RepairAttempt(
                    attempt_number=attempt_num,
                    patch={},
                    patch_hash="",
                    test_status_before="fail",
                    test_status_after="fail",
                    failures_before=len(envelope.manifest_failures) + len(envelope.runtime_failures),
                    failures_after=len(envelope.manifest_failures) + len(envelope.runtime_failures),
                    duration_ms=int((time.time() - attempt_start) * 1000),
                    llm_model=self.llm_client.config.model if self.llm_client else "",
                    llm_tokens_used=0,
                    success=False
                ))
                continue
            
            # Apply patch
            try:
                self._apply_patch(current_path, patch)
                
                if verbose:
                    print(f"  Patch applied")
                
            except Exception as e:
                if verbose:
                    print(f"  ❌ Patch apply failed: {e}")
                
                attempts.append(RepairAttempt(
                    attempt_number=attempt_num,
                    patch=patch,
                    patch_hash=hashlib.sha256(json.dumps(patch).encode()).hexdigest()[:16],
                    test_status_before="fail",
                    test_status_after="fail",
                    failures_before=len(envelope.manifest_failures) + len(envelope.runtime_failures),
                    failures_after=len(envelope.manifest_failures) + len(envelope.runtime_failures),
                    duration_ms=int((time.time() - attempt_start) * 1000),
                    llm_model=self.llm_client.config.model if self.llm_client else "",
                    llm_tokens_used=0,
                    success=False
                ))
                continue
            
            # Retest
            if verbose:
                print(f"  Retesting...")
            
            test_result_after = self._test_extension(current_path, verbose)
            
            # Count failures
            failures_before = len(envelope.manifest_failures) + len(envelope.runtime_failures)
            failures_after = len(test_result_after.permission_errors) + len(test_result_after.runtime_errors)
            
            success = test_result_after.overall_status == "pass"
            
            attempts.append(RepairAttempt(
                attempt_number=attempt_num,
                patch=patch,
                patch_hash=hashlib.sha256(json.dumps(patch).encode()).hexdigest()[:16],
                test_status_before="fail",
                test_status_after=test_result_after.overall_status,
                failures_before=failures_before,
                failures_after=failures_after,
                duration_ms=int((time.time() - attempt_start) * 1000),
                llm_model=self.llm_client.config.model if self.llm_client else "",
                llm_tokens_used=0,  # Would need to track from LLM responses
                success=success
            ))
            
            if success:
                if verbose:
                    print(f"\n✅ Repair successful on attempt {attempt_num}!")
                
                # Update envelope for next iteration
                envelope = create_failure_envelope(
                    test_result_after,
                    current_path,
                    original_hash=original_hash,
                    converted_hash=self._hash_extension(current_path),
                    compatibility_score=0.0
                )
                
                break
            
            # Update envelope for next iteration
            envelope = create_failure_envelope(
                test_result_after,
                current_path,
                original_hash=original_hash,
                converted_hash=self._hash_extension(current_path),
                compatibility_score=0.0
            )
            
            if verbose:
                print(f"  Failures remaining: {failures_after}")
        
        # Determine verdict
        final_hash = self._hash_extension(current_path)
        
        if attempts and attempts[-1].success:
            verdict = "PASS"
        elif attempts and attempts[-1].failures_after < attempts[0].failures_before:
            verdict = "DEGRADED"
        else:
            verdict = "NOT_REPAIRED"
        
        if verbose:
            print(f"\n[4/4] Final Result: {verdict}")
            print(f"{'='*60}\n")
        
        return RepairReceipt(
            original_hash=original_hash,
            converted_hash=converted_hash,
            final_hash=final_hash,
            test_suite="chrome2fox_v1",
            firefox_version=test_result.firefox_version if test_result else "unknown",
            extension_name=manifest.get("name", "unknown"),
            attempts=attempts,
            verdict=verdict,
            model=self.llm_client.config.model if self.llm_client else "",
            provider=self.llm_client.config.base_url if self.llm_client else "",
            total_duration_ms=int((time.time() - start_time) * 1000)
        )
    
    def _test_extension(self, extension_path: Path, verbose: bool = False) -> Any:
        """Test an extension."""
        harness = self._get_test_harness()
        return harness.test_extension(extension_path, timeout_seconds=15)
    
    def _apply_patch(self, extension_path: Path, patch: dict[str, Any]) -> None:
        """Apply a patch to the extension."""
        file_patches = patch.get("file_patches", [])
        
        for file_patch in file_patches:
            file_path = extension_path / file_patch["path"]
            
            if not file_path.exists():
                # Create the file
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_patch["new_content"], encoding="utf-8")
            else:
                # Replace content
                file_path.write_text(file_patch["new_content"], encoding="utf-8")
    
    def _read_manifest(self, extension_path: Path) -> dict[str, Any]:
        """Read the manifest file."""
        manifest_path = extension_path / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _hash_extension(self, extension_path: Path) -> str:
        """Calculate hash of extension contents."""
        hasher = hashlib.sha256()
        
        for file_path in sorted(extension_path.rglob("*")):
            if file_path.is_file():
                try:
                    content = file_path.read_bytes()
                    hasher.update(content)
                except Exception:
                    pass
        
        return hasher.hexdigest()[:16]


def create_repair_engine(
    base_url: str = "https://integrate.api.nvidia.com/v1",
    api_key: str = "",
    model: str = "meta/llama-3.1-70b-instruct",
    firefox_binary: str | None = None
) -> RepairEngine:
    """
    Convenience function to create a repair engine.
    
    Args:
        base_url: LLM API endpoint
        api_key: API key
        model: Model name
        firefox_binary: Path to Firefox (optional)
        
    Returns:
        RepairEngine instance
    """
    config = LLMConfig(
        base_url=base_url,
        api_key=api_key,
        model=model
    )
    
    return RepairEngine(
        llm_config=config,
        firefox_binary=firefox_binary
    )


if __name__ == "__main__":
    print("Repair Engine for Chrome-to-Fox")
    print("=" * 60)
    print("Orchestrates test-fail-repair-retest loop with LLM")
    print("\nUsage:")
    print("  from chrome2fox.repair_engine import RepairEngine")
    print("  engine = RepairEngine(llm_config=...)")
    print("  receipt = engine.repair(extension_path, max_attempts=3)")
    print(f"\n  Verdict: {receipt.verdict}")

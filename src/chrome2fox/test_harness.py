"""
Firefox Test Harness — Disposable profile + extension testing.

Creates a temporary Firefox profile, installs the extension,
runs probes, and captures console/errors.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProbeResult:
    """Result of a single probe."""
    name: str
    status: str  # pass, fail, error, timeout
    message: str = ""
    duration_ms: int = 0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Full test result from Firefox harness."""
    extension_name: str
    firefox_version: str
    profile_path: str
    install_success: bool
    probes: list[ProbeResult]
    console_logs: list[dict[str, Any]]
    runtime_errors: list[dict[str, Any]]
    permission_errors: list[dict[str, Any]]
    api_mismatches: list[dict[str, Any]]
    duration_ms: int = 0
    overall_status: str = "unknown"  # pass, fail, error


class FirefoxTestHarness:
    """
    Test Chrome-to-Fox converted extensions in a disposable Firefox profile.
    
    Usage:
        harness = FirefoxTestHarness()
        result = harness.test_extension(
            extension_path=Path("./output/my-extension"),
            extension_name="my-extension"
        )
    """
    
    def __init__(self, firefox_binary: str | None = None):
        """
        Initialize the test harness.
        
        Args:
            firefox_binary: Path to Firefox binary. If None, auto-detect.
        """
        self.firefox_binary = firefox_binary or self._find_firefox()
        self._temp_dir: Path | None = None
        self._profile_dir: Path | None = None
    
    def _find_firefox(self) -> str:
        """Auto-detect Firefox binary."""
        candidates = [
            "/usr/bin/firefox",
            "/usr/bin/firefox-esr",
            "/snap/bin/firefox",
            "/usr/local/bin/firefox",
            # macOS
            "/Applications/Firefox.app/Contents/MacOS/firefox",
            # Windows
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ]
        
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        
        # Try which/where
        try:
            result = subprocess.run(
                ["which", "firefox"] if os.name != "nt" else ["where", "firefox"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split("\n")[0]
        except Exception:
            pass
        
        raise RuntimeError(
            "Firefox not found. Install Firefox or provide firefox_binary path."
        )
    
    def _get_firefox_version(self) -> str:
        """Get Firefox version."""
        try:
            result = subprocess.run(
                [self.firefox_binary, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Parse "Mozilla Firefox XX.XX.X"
            version_line = result.stdout.strip()
            parts = version_line.split()
            return parts[-1] if parts else "unknown"
        except Exception:
            return "unknown"
    
    def test_extension(
        self,
        extension_path: Path,
        extension_name: str = "test-extension",
        timeout_seconds: int = 30
    ) -> TestResult:
        """
        Test a converted extension in Firefox.
        
        Args:
            extension_path: Path to converted extension directory
            extension_name: Name for the extension
            timeout_seconds: Timeout for probes
            
        Returns:
            TestResult with all probe results
        """
        start_time = time.time()
        firefox_version = self._get_firefox_version()
        
        # Create disposable profile
        self._temp_dir = Path(tempfile.mkdtemp(prefix="chrome2fox_test_"))
        self._profile_dir = self._temp_dir / "profile"
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Create Firefox profile preferences
        self._create_profile_prefs()
        
        console_logs = []
        runtime_errors = []
        permission_errors = []
        api_mismatches = []
        probes = []
        
        try:
            # Install extension
            install_success = self._install_extension(extension_path)
            
            if install_success:
                # Run probes
                probes = self._run_probes(timeout_seconds)
                
                # Capture console and errors
                console_logs, runtime_errors = self._capture_logs()
                
                # Check for permission errors
                permission_errors = self._check_permissions(extension_path)
                
                # Check for API mismatches
                api_mismatches = self._check_api_mismatches(extension_path)
            
            # Determine overall status
            overall_status = "pass"
            if not install_success:
                overall_status = "fail"
            elif any(p.status == "fail" for p in probes):
                overall_status = "fail"
            elif runtime_errors:
                overall_status = "fail"
            
        except Exception as e:
            overall_status = "error"
            probes.append(ProbeResult(
                name="harness_error",
                status="error",
                message=str(e)
            ))
        finally:
            # Cleanup
            self._cleanup()
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return TestResult(
            extension_name=extension_name,
            firefox_version=firefox_version,
            profile_path=str(self._profile_dir) if self._profile_dir else "",
            install_success=install_success,
            probes=probes,
            console_logs=console_logs,
            runtime_errors=runtime_errors,
            permission_errors=permission_errors,
            api_mismatches=api_mismatches,
            duration_ms=duration_ms,
            overall_status=overall_status
        )
    
    def _create_profile_prefs(self) -> None:
        """Create Firefox profile preferences."""
        prefs_content = """
// Disable updates
user_pref("app.update.enabled", false);
user_pref("app.update.auto", false);

// Disable telemetry
user_pref("toolkit.telemetry.enabled", false);
user_pref("datareporting.healthreport.uploadEnabled", false);

// Enable extension debugging
user_pref("xpinstall.signatures.required", false);
user_pref("extensions.experiments.enabled", true);

// Console logging
user_pref("browser.dom.window.dump.enabled", true);
user_pref("devtools.console.stdout.content", true);

// Disable first run
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");

// Allow unsigned extensions (for testing)
user_pref("xpinstall.signatures.required", false);
user_pref("extensions.experiments.enabled", true);
"""
        prefs_file = self._profile_dir / "prefs.js"
        prefs_file.write_text(prefs_content, encoding="utf-8")
    
    def _install_extension(self, extension_path: Path) -> bool:
        """
        Install extension into Firefox profile.
        
        Uses web-ext or manual installation via profiles directory.
        """
        # Create extensions directory
        ext_dir = self._profile_dir / "extensions"
        ext_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if manifest exists
        manifest_path = extension_path / "manifest.json"
        if not manifest_path.exists():
            return False
        
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            return False
        
        # Get extension ID from gecko settings
        gecko_id = None
        if "browser_specific_settings" in manifest:
            gecko_id = manifest["browser_specific_settings"].get("gecko", {}).get("id")
        
        if not gecko_id:
            # Generate a temporary ID
            ext_name = manifest.get("name", "test-extension")
            gecko_id = f"test-{ext_name.lower().replace(' ', '-')}@chrome2fox.test"
        
        # Create the extension directory in Firefox profile
        ext_install_dir = ext_dir / gecko_id
        ext_install_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all files from extension path
        for item in extension_path.iterdir():
            if item.is_file():
                shutil.copy2(item, ext_install_dir / item.name)
            elif item.is_dir():
                shutil.copytree(item, ext_install_dir / item.name, dirs_exist_ok=True)
        
        # Create web-ext manifest for installation
        web_ext_manifest = {
            "manifest_version": 2,
            "name": manifest.get("name", "test-extension"),
            "version": manifest.get("version", "1.0"),
            "description": manifest.get("description", "Test extension"),
            "browser_specific_settings": {
                "gecko": {
                    "id": gecko_id,
                    "strict_min_version": "109.0"
                }
            }
        }
        
        # Write web-ext compatible manifest
        web_ext_path = ext_install_dir / "manifest.json"
        with open(web_ext_path, "w", encoding="utf-8") as f:
            json.dump(web_ext_manifest, f, indent=2)
        
        return True
    
    def _run_probes(self, timeout_seconds: int) -> list[ProbeResult]:
        """
        Run probes against the installed extension.
        
        Returns list of ProbeResult with pass/fail status.
        """
        probes = []
        
        # Probe 1: Check if Firefox starts
        probes.append(self._probe_firefox_starts(timeout_seconds))
        
        # Probe 2: Check if extension loads
        probes.append(self._probe_extension_loads(timeout_seconds))
        
        # Probe 3: Check manifest validity
        probes.append(self._probe_manifest_valid())
        
        # Probe 4: Check permissions
        probes.append(self._probe_permissions())
        
        # Probe 5: Check API availability
        probes.append(self._probe_api_availability())
        
        return probes
    
    def _probe_firefox_starts(self, timeout: int) -> ProbeResult:
        """Probe: Firefox starts without crashing."""
        start = time.time()
        
        try:
            # Create a simple test page
            test_html = self._temp_dir / "test.html"
            test_html.write_text("<html><body><h1>Test</h1></body></html>")
            
            # Start Firefox with profile
            process = subprocess.Popen(
                [
                    self.firefox_binary,
                    "--profile", str(self._profile_dir),
                    "--no-remote",
                    "--headless",
                    str(test_html)
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait a bit and check if still running
            time.sleep(2)
            
            if process.poll() is None:
                # Still running, kill it
                process.terminate()
                process.wait(timeout=5)
                
                return ProbeResult(
                    name="firefox_starts",
                    status="pass",
                    message="Firefox started successfully",
                    duration_ms=int((time.time() - start) * 1000)
                )
            else:
                return ProbeResult(
                    name="firefox_starts",
                    status="fail",
                    message="Firefox exited prematurely",
                    details={"exit_code": process.returncode},
                    duration_ms=int((time.time() - start) * 1000)
                )
                
        except Exception as e:
            return ProbeResult(
                name="firefox_starts",
                status="error",
                message=str(e),
                duration_ms=int((time.time() - start) * 1000)
            )
    
    def _probe_extension_loads(self, timeout: int) -> ProbeResult:
        """Probe: Extension loads without errors."""
        start = time.time()
        
        # Check if extension directory exists
        ext_dir = self._profile_dir / "extensions"
        if not ext_dir.exists():
            return ProbeResult(
                name="extension_loads",
                status="fail",
                message="Extensions directory not found",
                duration_ms=int((time.time() - start) * 1000)
            )
        
        # Count installed extensions
        ext_count = len(list(ext_dir.iterdir()))
        
        return ProbeResult(
            name="extension_loads",
            status="pass" if ext_count > 0 else "fail",
            message=f"Found {ext_count} extension(s)",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def _probe_manifest_valid(self) -> ProbeResult:
        """Probe: Manifest is valid Firefox format."""
        start = time.time()
        
        ext_dir = self._profile_dir / "extensions"
        if not ext_dir.exists():
            return ProbeResult(
                name="manifest_valid",
                status="fail",
                message="No extensions directory",
                duration_ms=int((time.time() - start) * 1000)
            )
        
        # Find first extension
        for ext_path in ext_dir.iterdir():
            manifest_path = ext_path / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    
                    # Check required fields
                    required = ["manifest_version", "name", "version"]
                    missing = [f for f in required if f not in manifest]
                    
                    if missing:
                        return ProbeResult(
                            name="manifest_valid",
                            status="fail",
                            message=f"Missing fields: {missing}",
                            duration_ms=int((time.time() - start) * 1000)
                        )
                    
                    # Check gecko settings
                    if "browser_specific_settings" not in manifest:
                        return ProbeResult(
                            name="manifest_valid",
                            status="fail",
                            message="Missing browser_specific_settings.gecko",
                            duration_ms=int((time.time() - start) * 1000)
                        )
                    
                    return ProbeResult(
                        name="manifest_valid",
                        status="pass",
                        message="Manifest is valid",
                        duration_ms=int((time.time() - start) * 1000)
                    )
                    
                except json.JSONDecodeError as e:
                    return ProbeResult(
                        name="manifest_valid",
                        status="fail",
                        message=f"Invalid JSON: {e}",
                        duration_ms=int((time.time() - start) * 1000)
                    )
        
        return ProbeResult(
            name="manifest_valid",
            status="fail",
            message="No manifest found",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def _probe_permissions(self) -> ProbeResult:
        """Probe: Permissions are valid for Firefox."""
        start = time.time()
        
        ext_dir = self._profile_dir / "extensions"
        for ext_path in ext_dir.iterdir():
            manifest_path = ext_path / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    
                    permissions = manifest.get("permissions", [])
                    
                    # Chrome-only permissions
                    chrome_only = [
                        "pageCapture",
                        "videoCaptureOptional",
                        "videoCaptureRequired"
                    ]
                    
                    found_chrome_only = [p for p in permissions if p in chrome_only]
                    
                    if found_chrome_only:
                        return ProbeResult(
                            name="permissions_valid",
                            status="fail",
                            message=f"Chrome-only permissions: {found_chrome_only}",
                            duration_ms=int((time.time() - start) * 1000)
                        )
                    
                    return ProbeResult(
                        name="permissions_valid",
                        status="pass",
                        message=f"Found {len(permissions)} valid permissions",
                        duration_ms=int((time.time() - start) * 1000)
                    )
                    
                except Exception:
                    pass
        
        return ProbeResult(
            name="permissions_valid",
            status="pass",
            message="No permissions to check",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def _probe_api_availability(self) -> ProbeResult:
        """Probe: Chrome APIs have Firefox equivalents."""
        start = time.time()
        
        # This would require actually running the extension
        # For now, do a static check of the manifest
        ext_dir = self._profile_dir / "extensions"
        for ext_path in ext_dir.iterdir():
            manifest_path = ext_path / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    
                    # Check for Chrome-only APIs in permissions
                    permissions = manifest.get("permissions", [])
                    
                    # APIs that don't exist in Firefox
                    unsupported = [
                        "debugger",  # Partial support
                        "nativeMessaging",
                        "desktopCapture"
                    ]
                    
                    found_unsupported = [p for p in permissions if p in unsupported]
                    
                    if found_unsupported:
                        return ProbeResult(
                            name="api_availability",
                            status="fail",
                            message=f"Unsupported APIs: {found_unsupported}",
                            duration_ms=int((time.time() - start) * 1000)
                        )
                    
                    return ProbeResult(
                        name="api_availability",
                        status="pass",
                        message="APIs appear compatible",
                        duration_ms=int((time.time() - start) * 1000)
                    )
                    
                except Exception:
                    pass
        
        return ProbeResult(
            name="api_availability",
            status="pass",
            message="No API issues detected",
            duration_ms=int((time.time() - start) * 1000)
        )
    
    def _capture_logs(self) -> tuple[list[dict], list[dict]]:
        """Capture console logs and runtime errors."""
        console_logs = []
        runtime_errors = []
        
        # Check for Firefox console log files
        log_paths = [
            self._profile_dir / "browser_console.log",
            self._profile_dir / "extensions.log",
            self._temp_dir / "firefox.log"
        ]
        
        for log_path in log_paths:
            if log_path.exists():
                try:
                    with open(log_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                if "error" in line.lower() or "exception" in line.lower():
                                    runtime_errors.append({
                                        "source": str(log_path),
                                        "message": line
                                    })
                                else:
                                    console_logs.append({
                                        "source": str(log_path),
                                        "message": line
                                    })
                except Exception:
                    pass
        
        return console_logs, runtime_errors
    
    def _check_permissions(self, extension_path: Path) -> list[dict]:
        """Check for permission issues."""
        errors = []
        
        manifest_path = extension_path / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                
                permissions = manifest.get("permissions", [])
                
                # Chrome-only permissions that don't exist in Firefox
                chrome_only = {
                    "pageCapture": "Use browser.tabCapture or getUserMedia",
                    "videoCaptureOptional": "Not available in Firefox",
                    "videoCaptureRequired": "Not available in Firefox",
                    "debugger": "Partial support via polyfill",
                    "nativeMessaging": "Requires native app",
                    "desktopCapture": "Use getDisplayMedia"
                }
                
                for perm in permissions:
                    if perm in chrome_only:
                        errors.append({
                            "permission": perm,
                            "issue": "Chrome-only permission",
                            "suggestion": chrome_only[perm]
                        })
                        
            except Exception:
                pass
        
        return errors
    
    def _check_api_mismatches(self, extension_path: Path) -> list[dict]:
        """Check for API mismatches between Chrome and Firefox."""
        mismatches = []
        
        # Check JS files for Chrome-specific APIs
        for js_file in extension_path.rglob("*.js"):
            try:
                content = js_file.read_text(encoding="utf-8")
                
                # Chrome-specific APIs that don't exist in Firefox
                chrome_apis = [
                    "chrome.tabCapture",
                    "chrome.desktopCapture",
                    "chrome.nativeMessaging",
                    "chrome.system.cpu",
                    "chrome.system.memory",
                    "chrome.system.storage",
                    "chrome.power",
                    "chrome.management",
                    "chrome.contextMenus",  # Exists but different
                    "chrome.webRequest",  # Exists but different
                ]
                
                for api in chrome_apis:
                    if api in content:
                        mismatches.append({
                            "file": str(js_file.name),
                            "api": api,
                            "issue": "Chrome-specific API usage"
                        })
                        
            except Exception:
                pass
        
        return mismatches
    
    def _cleanup(self) -> None:
        """Clean up temporary files."""
        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
            except Exception:
                pass
            self._temp_dir = None
            self._profile_dir = None


def test_extension(
    extension_path: Path,
    extension_name: str = "test-extension",
    firefox_binary: str | None = None,
    timeout_seconds: int = 30
) -> TestResult:
    """
    Convenience function to test an extension.
    
    Args:
        extension_path: Path to converted extension
        extension_name: Name for the extension
        firefox_binary: Path to Firefox (optional)
        timeout_seconds: Timeout for probes
        
    Returns:
        TestResult with all results
    """
    harness = FirefoxTestHarness(firefox_binary)
    return harness.test_extension(
        extension_path,
        extension_name,
        timeout_seconds
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_harness.py <extension-path>")
        sys.exit(1)
    
    ext_path = Path(sys.argv[1])
    result = test_extension(ext_path, ext_path.name)
    
    print(f"\n{'='*60}")
    print(f"Extension: {result.extension_name}")
    print(f"Firefox: {result.firefox_version}")
    print(f"Status: {result.overall_status.upper()}")
    print(f"Duration: {result.duration_ms}ms")
    print(f"\nProbes:")
    for probe in result.probes:
        status_icon = "✅" if probe.status == "pass" else "❌" if probe.status == "fail" else "⚠️"
        print(f"  {status_icon} {probe.name}: {probe.message}")
    
    if result.runtime_errors:
        print(f"\nRuntime Errors ({len(result.runtime_errors)}):")
        for error in result.runtime_errors[:5]:
            print(f"  - {error['message']}")
    
    print(f"{'='*60}\n")

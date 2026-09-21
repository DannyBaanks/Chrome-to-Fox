"""Analyzer — Scan Chrome extension for Firefox compatibility."""

import json
from pathlib import Path
from typing import Any


def analyze_extension(ext_path: Path) -> dict[str, Any]:
    """Analyze a Chrome extension and report Firefox compatibility.

    Args:
        ext_path: Path to Chrome extension directory, .zip, or .crx

    Returns:
        Analysis report with manifest_version, used_apis, chrome_only_apis, warnings, compatibility_score
    """
    ext_path = Path(ext_path)

    # Load manifest
    manifest_path = ext_path / "manifest.json"
    if not manifest_path.exists():
        return {"error": "manifest.json not found", "errors": ["No manifest.json"]}

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    report = {
        "input": str(ext_path),
        "manifest_version": manifest.get("manifest_version", 0),
        "name": manifest.get("name", "Unknown"),
        "version": manifest.get("version", "0.0.0"),
        "used_apis": [],
        "chrome_only_apis": [],
        "compatible_apis": [],
        "warnings": [],
        "errors": [],
        "manifest_issues": [],
        "compatibility_score": 1.0,
    }

    # Scan JS files for API usage
    js_files = list(ext_path.rglob("*.js"))
    for js_file in js_files:
        try:
            content = js_file.read_text(encoding="utf-8")
            _scan_js_for_apis(content, report)
        except Exception as e:
            report["warnings"].append(f"Could not read {js_file.name}: {e}")

    # Check manifest issues
    _check_manifest(manifest, report)

    # Calculate compatibility score
    total_apis = len(report["used_apis"])
    if total_apis > 0:
        chrome_only = len(report["chrome_only_apis"])
        report["compatibility_score"] = round(1.0 - (chrome_only / total_apis), 2)

    return report


def _scan_js_for_apis(content: str, report: dict):
    """Scan JavaScript content for chrome.* API calls."""
    import re

    # Match chrome.something.something patterns
    pattern = r'\bchrome\.(\w+)(?:\.(\w+))?\b'
    matches = re.findall(pattern, content)

    for namespace, method in matches:
        full_api = f"chrome.{namespace}" + (f".{method}" if method else "")
        if full_api not in report["used_apis"]:
            report["used_apis"].append(full_api)

            # Check if it's Chrome-only or incompatible
            status = _get_api_status(namespace, method)
            if status in ("chrome_only", "incompatible"):
                report["chrome_only_apis"].append(full_api)
            else:
                report["compatible_apis"].append(full_api)


def _get_api_status(namespace: str, method: str | None) -> str:
    """Get compatibility status for an API."""
    chrome_only = {
        "offscreen": "chrome_only",
        "tabGroups": "chrome_only",
        "declarativeContent": "chrome_only",
        "sidePanel": "chrome_only",
        "debugger": "incompatible",
        "tabCapture": "chrome_only",
        "tts": "chrome_only",
        "usb": "incompatible",
        "serial": "incompatible",
        "hid": "incompatible",
    }

    if namespace in chrome_only:
        return chrome_only[namespace]

    # Firefox-compatible APIs
    compatible = {
        "tabs", "runtime", "storage", "alarms", "bookmarks",
        "browserAction", "pageAction", "contextMenus", "cookies",
        "history", "i18n", "identity", "management", "menus",
        "notifications", "omnibox", "permissions", "pkcs11",
        "privacy", "proxy", "search", "sessions", "sidebarAction",
        "topSites", "webNavigation", "webRequest", "windows",
    }

    if namespace in compatible:
        return "compatible"

    return "unknown"


def _check_manifest(manifest: dict, report: dict):
    """Check manifest for Firefox compatibility issues."""
    mv = manifest.get("manifest_version", 0)

    # MV2 checks
    if mv == 2:
        if "browser_action" in manifest:
            report["manifest_issues"].append("MV2 uses browser_action (OK in Firefox)")
        if "page_action" in manifest:
            report["manifest_issues"].append("MV2 uses page_action (OK in Firefox)")

    # MV3 checks
    if mv == 3:
        if "action" in manifest:
            report["manifest_warnings"] = report.get("manifest_warnings", [])
            report["manifest_issues"].append("MV3 uses 'action' — Firefox prefers 'browser_action'")

        if "host_permissions" in manifest:
            report["manifest_issues"].append("MV3 host_permissions — Firefox may need them in 'permissions'")

    # Common checks
    if "key" in manifest:
        report["manifest_issues"].append("'key' field not supported in Firefox (uses random UUIDs)")

    if "minimum_chrome_version" in manifest:
        report["manifest_issues"].append("'minimum_chrome_version' is Chrome-specific")

    if "browser_specific_settings" not in manifest:
        report["manifest_issues"].append("Missing 'browser_specific_settings.gecko.id' (required for Firefox)")

"""Validator — Validate Firefox extension for submission."""

import json
from pathlib import Path
from typing import Any


def validate_extension(ext_path: Path) -> dict[str, Any]:
    """Validate a Firefox extension directory.

    Args:
        ext_path: Path to Firefox extension directory

    Returns:
        Validation result with valid, errors, warnings
    """
    ext_path = Path(ext_path)

    result = {
        "input": str(ext_path),
        "valid": True,
        "errors": [],
        "warnings": [],
        "checks": {},
    }

    # Check manifest exists
    manifest_path = ext_path / "manifest.json"
    if not manifest_path.exists():
        result["valid"] = False
        result["errors"].append("manifest.json not found")
        return result

    # Load and validate manifest
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        result["valid"] = False
        result["errors"].append(f"Invalid JSON in manifest.json: {e}")
        return result

    # Check required fields
    required_fields = ["name", "version", "manifest_version"]
    for field in required_fields:
        if field not in manifest:
            result["valid"] = False
            result["errors"].append(f"Missing required field: {field}")

    # Check manifest_version
    mv = manifest.get("manifest_version", 0)
    if mv not in (2, 3):
        result["valid"] = False
        result["errors"].append(f"Unsupported manifest_version: {mv}")

    # Check browser_specific_settings
    if "browser_specific_settings" not in manifest:
        result["warnings"].append("Missing browser_specific_settings.gecko.id")
    elif "gecko" not in manifest.get("browser_specific_settings", {}):
        result["warnings"].append("Missing browser_specific_settings.gecko.id")

    # Check for referenced files
    _check_referenced_files(manifest, ext_path, result)

    # Check for remaining chrome.* usage
    _check_chrome_usage(ext_path, result)

    result["checks"]["manifest_valid"] = len(result["errors"]) == 0
    result["checks"]["files_exist"] = True
    result["checks"]["no_chrome_apis"] = True

    return result


def _check_referenced_files(manifest: dict, ext_path: Path, result: dict):
    """Check that all files referenced in manifest exist."""
    # Check background scripts
    bg = manifest.get("background", {})
    scripts = bg.get("scripts", [])
    if isinstance(scripts, str):
        scripts = [scripts]
    service_worker = bg.get("service_worker")
    if service_worker:
        scripts.append(service_worker)

    for script in scripts:
        if not (ext_path / script).exists():
            result["valid"] = False
            result["errors"].append(f"Referenced file not found: {script}")

    # Check content scripts
    for cs in manifest.get("content_scripts", []):
        for js in cs.get("js", []):
            if not (ext_path / js).exists():
                result["valid"] = False
                result["errors"].append(f"Content script not found: {js}")

    # Check icons
    icons = manifest.get("icons", {})
    for size, path in icons.items():
        if not (ext_path / path).exists():
            result["warnings"].append(f"Icon not found: {path} ({size}px)")

    # Check action icons
    for action_key in ["action", "browser_action", "page_action"]:
        action = manifest.get(action_key, {})
        default_icon = action.get("default_icon", {})
        if isinstance(default_icon, str):
            default_icon = {"": default_icon}
        for size, path in default_icon.items():
            if not (ext_path / path).exists():
                result["warnings"].append(f"Action icon not found: {path}")


def _check_chrome_usage(ext_path: Path, result: dict):
    """Check for remaining chrome.* API usage in JS files."""
    import re

    pattern = r'\bchrome\.(\w+)\b'
    chrome_apis_found = []

    for js_file in ext_path.rglob("*.js"):
        try:
            content = js_file.read_text(encoding="utf-8")
            matches = re.findall(pattern, content)
            for api in matches:
                if api not in chrome_apis_found:
                    chrome_apis_found.append(api)
        except Exception:
            pass

    if chrome_apis_found:
        result["checks"]["no_chrome_apis"] = False
        result["warnings"].append(f"Remaining chrome.* APIs: {', '.join(chrome_apis_found)}")

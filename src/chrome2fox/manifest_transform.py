"""Manifest Transformer — Convert Chrome manifest to Firefox format."""

import hashlib
import json
from typing import Any


def transform_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Transform a Chrome manifest.json to Firefox-compatible format.

    Args:
        manifest: Chrome manifest dictionary

    Returns:
        Firefox-compatible manifest dictionary
    """
    result = json.loads(json.dumps(manifest))  # Deep copy

    # Ensure manifest_version is supported
    mv = result.get("manifest_version", 2)
    if mv not in (2, 3):
        raise ValueError(f"Unsupported manifest_version: {mv}")

    # Add browser_specific_settings.gecko.id if missing
    if "browser_specific_settings" not in result:
        result["browser_specific_settings"] = _generate_gecko_settings(result)
    elif "gecko" not in result["browser_specific_settings"]:
        result["browser_specific_settings"]["gecko"] = _generate_gecko_id(result)

    # Remove Chrome-specific fields
    chrome_fields = ["key", "minimum_chrome_version"]
    for field in chrome_fields:
        result.pop(field, None)

    # MV3 specific transforms
    if mv == 3:
        result = _transform_mv3(result)

    # MV2 specific transforms
    if mv == 2:
        result = _transform_mv2(result)

    return result


def _generate_gecko_settings(manifest: dict) -> dict:
    """Generate browser_specific_settings.gecko from manifest."""
    name = manifest.get("name", "unknown-extension")
    ext_id = _name_to_gecko_id(name)
    return {
        "gecko": {
            "id": ext_id,
            "strict_min_version": "109.0"
        }
    }


def _generate_gecko_id(manifest: dict) -> dict:
    """Generate gecko ID from manifest name."""
    name = manifest.get("name", "unknown-extension")
    ext_id = _name_to_gecko_id(name)
    return {
        "id": ext_id,
        "strict_min_version": "109.0"
    }


def _name_to_gecko_id(name: str) -> str:
    """Convert extension name to a deterministic gecko ID."""
    # Generate a deterministic ID from the name
    hash_hex = hashlib.sha256(name.encode()).hexdigest()[:16]
    # Format as @{hash} for Firefox
    return f"@chrome2fox-{hash_hex}"


def _transform_mv3(manifest: dict) -> dict:
    """Transform MV3 manifest for Firefox compatibility."""
    # Convert service_worker to background.scripts (Firefox MV3 doesn't support service_worker)
    if "background" in manifest:
        bg = manifest["background"]
        if "service_worker" in bg:
            # Firefox requires scripts array, not service_worker
            service_worker = bg.pop("service_worker")
            # Convert to scripts array
            if "scripts" not in bg:
                bg["scripts"] = [service_worker]
            # Remove type: module if present (Firefox doesn't support it in MV3 background)
            bg.pop("type", None)
    
    # Convert side_panel to sidebar_action (Firefox doesn't support side_panel)
    if "side_panel" in manifest:
        side_panel = manifest.pop("side_panel")
        manifest["sidebar_action"] = {
            "default_title": side_panel.get("default_title", ""),
            "default_panel": side_panel.get("default_path", side_panel.get("default_panel", ""))
        }
    
    # Convert host_permissions to permissions if needed
    if "host_permissions" in manifest:
        host_perms = manifest.pop("host_permissions")
        existing_perms = manifest.get("permissions", [])
        # Add host permissions to the main permissions array
        for perm in host_perms:
            if perm not in existing_perms:
                existing_perms.append(perm)
        manifest["permissions"] = existing_perms

    return manifest


def _transform_mv2(manifest: dict) -> dict:
    """Transform MV2 manifest for Firefox compatibility."""
    # Firefox MV2 uses browser_action and page_action (same as Chrome MV2)
    # No changes needed for MV2 structure
    return manifest

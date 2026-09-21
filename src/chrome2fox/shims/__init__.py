"""Chrome-only APIs registry and polyfill management."""

import json
from pathlib import Path
from typing import Any


# Registry of Chrome-only APIs with their Firefox equivalents or polyfill status
CHROME_ONLY_APIS = {
    "chrome.offscreen": {
        "status": "chrome_only",
        "description": "Chrome-only API for offscreen documents",
        "shim": "offscreen_polyfill.js",
        "firefox_equivalent": None,
        "workaround": "Use background scripts or content scripts instead",
    },
    "chrome.tabGroups": {
        "status": "chrome_only",
        "description": "Chrome-only API for tab grouping",
        "shim": "tabgroups_polyfill.js",
        "firefox_equivalent": None,
        "workaround": "Use browser.tabs API with manual group tracking",
    },
    "chrome.declarativeContent": {
        "status": "chrome_only",
        "description": "Chrome-only API for declarative content matching",
        "shim": "declarativecontent_polyfill.js",
        "firefox_equivalent": "browser.declarativeNetRequest",
        "workaround": "Use declarativeNetRequest or content scripts",
    },
    "chrome.sidePanel": {
        "status": "chrome_only",
        "description": "Chrome-only API for side panel",
        "shim": "sidepanel_polyfill.js",
        "firefox_equivalent": "browser.sidebarAction",
        "workaround": "Use sidebarAction API",
    },
    "chrome.debugger": {
        "status": "incompatible",
        "description": "Chrome-only debugger API",
        "shim": "debugger_polyfill.js",
        "firefox_equivalent": None,
        "workaround": "No direct equivalent in Firefox",
    },
    "chrome.tabCapture": {
        "status": "chrome_only",
        "description": "Chrome-only API for tab capture",
        "shim": "tabcapture_polyfill.js",
        "firefox_equivalent": None,
        "workaround": "Use getUserMedia or screen capture APIs",
    },
    "chrome.tts": {
        "status": "chrome_only",
        "description": "Chrome-only text-to-speech API",
        "shim": "tts_polyfill.js",
        "firefox_equivalent": None,
        "workaround": "Use Web Speech API or browser.tts if available",
    },
    "chrome.usb": {
        "status": "incompatible",
        "description": "Chrome-only USB API",
        "shim": "usb_polyfill.js",
        "firefox_equivalent": None,
        "workaround": "No direct equivalent in Firefox",
    },
    "chrome.serial": {
        "status": "incompatible",
        "description": "Chrome-only serial API",
        "shim": "serial_polyfill.js",
        "firefox_equivalent": None,
        "workaround": "No direct equivalent in Firefox",
    },
    "chrome.hid": {
        "status": "incompatible",
        "description": "Chrome-only HID API",
        "shim": "hid_polyfill.js",
        "firefox_equivalent": None,
        "workaround": "No direct equivalent in Firefox",
    },
}


def get_chrome_only_apis() -> dict[str, Any]:
    """Get the registry of Chrome-only APIs."""
    return CHROME_ONLY_APIS.copy()


def get_shim_for_api(api_name: str) -> str | None:
    """Get the polyfill shim filename for a Chrome-only API."""
    # Try exact match first
    api_info = CHROME_ONLY_APIS.get(api_name)
    if api_info:
        return api_info.get("shim")
    
    # Try matching by namespace (e.g., chrome.debugger.getTargets -> chrome.debugger)
    parts = api_name.split(".")
    if len(parts) >= 2:
        namespace = ".".join(parts[:2])  # e.g., "chrome.debugger"
        api_info = CHROME_ONLY_APIS.get(namespace)
        if api_info:
            return api_info.get("shim")
    
    return None


def get_required_shims(used_apis: list[str]) -> list[str]:
    """Get list of required shim files for the used APIs."""
    shims = []
    for api in used_apis:
        shim = get_shim_for_api(api)
        if shim and shim not in shims:
            shims.append(shim)
    
    # Also check by namespace (e.g., chrome.debugger.getTargets -> chrome.debugger)
    for api in used_apis:
        parts = api.split(".")
        if len(parts) >= 2:
            namespace = ".".join(parts[:2])
            shim = get_shim_for_api(namespace)
            if shim and shim not in shims:
                shims.append(shim)
    
    return shims


def generate_shims_content(used_apis: list[str]) -> str:
    """Generate JavaScript content for required shims."""
    shims = get_required_shims(used_apis)
    if not shims:
        return ""

    content = "// Chrome-to-Fox Polyfills\n"
    content += "// Auto-generated shims for Chrome-only APIs\n\n"

    for shim_file in shims:
        shim_path = Path(__file__).parent / shim_file
        if shim_path.exists():
            content += f"// --- {shim_file} ---\n"
            content += shim_path.read_text(encoding="utf-8")
            content += "\n\n"

    return content

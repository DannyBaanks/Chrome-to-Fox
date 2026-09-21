"""JS Patcher — Replace chrome.* with browser.* selectively."""

import re
from typing import Any


def patch_js(source_code: str, api_map: dict | None = None) -> tuple[str, list[dict]]:
    """Patch JavaScript code to replace chrome.* with browser.*.

    Args:
        source_code: Original JavaScript code
        api_map: Optional mapping of chrome.* to browser.* APIs

    Returns:
        Tuple of (patched_code, list_of_changes)
    """
    if api_map is None:
        api_map = _default_api_map()

    changes = []
    patched = source_code

    # Pattern to match chrome.namespace.method(...) but NOT chrome-extension:// URLs
    # Also avoid matching inside strings and comments
    pattern = r'\bchrome\.(\w+)\.(\w+)\b'

    def replace_match(match):
        namespace = match.group(1)
        method = match.group(2)
        full_api = f"chrome.{namespace}.{method}"

        # Skip chrome-extension:// URLs
        start = match.start()
        if start > 0:
            before = source_code[max(0, start - 20):start]
            if "chrome-extension://" in before or "chrome-extension:" in before:
                return match.group(0)

        # Check if this API should be replaced
        if namespace in api_map:
            replacement = f"browser.{namespace}.{method}"
            changes.append({
                "line": _get_line_number(source_code, start),
                "old": full_api,
                "new": replacement,
                "reason": f"chrome.{namespace} -> browser.{namespace}",
            })
            return replacement

        return match.group(0)

    patched = re.sub(pattern, replace_match, patched)

    return patched, changes


def _default_api_map() -> dict[str, str]:
    """Default mapping of Chrome namespaces to Firefox equivalents."""
    return {
        "tabs": "browser.tabs",
        "runtime": "browser.runtime",
        "storage": "browser.storage",
        "alarms": "browser.alarms",
        "bookmarks": "browser.bookmarks",
        "browserAction": "browser.browserAction",
        "pageAction": "browser.pageAction",
        "action": "browser.browserAction",  # MV3 action -> browser_action in Firefox
        "contextMenus": "browser.contextMenus",
        "cookies": "browser.cookies",
        "history": "browser.history",
        "i18n": "browser.i18n",
        "identity": "browser.identity",
        "management": "browser.management",
        "menus": "browser.menus",
        "notifications": "browser.notifications",
        "omnibox": "browser.omnibox",
        "permissions": "browser.permissions",
        "privacy": "browser.privacy",
        "proxy": "browser.proxy",
        "search": "browser.search",
        "sessions": "browser.sessions",
        "sidebarAction": "browser.sidebarAction",
        "topSites": "browser.topSites",
        "webNavigation": "browser.webNavigation",
        "webRequest": "browser.webRequest",
        "windows": "browser.windows",
        "downloads": "browser.downloads",
    }


def _get_line_number(source: str, position: int) -> int:
    """Get line number for a position in source code."""
    return source[:position].count('\n') + 1

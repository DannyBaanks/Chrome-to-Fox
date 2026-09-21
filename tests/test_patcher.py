"""Tests for JS Patcher module."""

from chrome2fox.patcher import patch_js


def test_patch_replaces_chrome_with_browser():
    """Test that chrome.* is replaced with browser.*."""
    code = "chrome.tabs.query({active: true}, function(tabs) { console.log(tabs[0].url); });"

    patched, changes = patch_js(code)

    assert "browser.tabs.query" in patched
    assert "chrome.tabs.query" not in patched
    assert len(changes) == 1
    assert changes[0]["old"] == "chrome.tabs.query"
    assert changes[0]["new"] == "browser.tabs.query"


def test_patch_preserves_chrome_extension_urls():
    """Test that chrome-extension:// URLs are not modified."""
    code = "const url = 'chrome-extension://abc123/popup.html';"

    patched, changes = patch_js(code)

    assert "chrome-extension://abc123/popup.html" in patched
    assert len(changes) == 0


def test_patch_multiple_apis():
    """Test patching multiple API calls."""
    code = """
chrome.runtime.sendMessage({type: 'init'});
chrome.storage.local.get('key', function(result) {
    console.log(result);
});
"""

    patched, changes = patch_js(code)

    assert "browser.runtime.sendMessage" in patched
    assert "browser.storage.local.get" in patched
    assert len(changes) == 2


def test_patch_unknown_api_unchanged():
    """Test that unknown chrome APIs are left unchanged."""
    code = "chrome.unknownAPI.doSomething();"

    patched, changes = patch_js(code)

    assert "chrome.unknownAPI.doSomething()" in patched
    assert len(changes) == 0

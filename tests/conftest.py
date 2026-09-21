"""Tests for Chrome-to-Fox converter."""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def simple_popup_manifest():
    """Simple popup extension manifest."""
    return {
        "manifest_version": 3,
        "name": "Simple Popup",
        "version": "1.0.0",
        "description": "A simple popup extension",
        "permissions": ["storage"],
        "action": {
            "default_popup": "popup.html",
            "default_icon": "icon.png"
        },
        "background": {
            "service_worker": "background.js"
        }
    }


@pytest.fixture
def content_script_manifest():
    """Content script extension manifest."""
    return {
        "manifest_version": 3,
        "name": "Content Script Extension",
        "version": "1.0.0",
        "description": "Extension with content scripts",
        "permissions": ["storage", "activeTab"],
        "content_scripts": [
            {
                "matches": ["*://*.example.com/*"],
                "js": ["content.js"]
            }
        ],
        "background": {
            "service_worker": "background.js"
        }
    }


@pytest.fixture
def has_offscreen_manifest():
    """Extension using Chrome-only offscreen API."""
    return {
        "manifest_version": 3,
        "name": "Offscreen Extension",
        "version": "1.0.0",
        "description": "Extension using offscreen API",
        "permissions": ["offscreen", "storage"],
        "background": {
            "service_worker": "background.js"
        }
    }


@pytest.fixture
def simple_popup_dir(tmp_path, simple_popup_manifest):
    """Create a simple popup extension directory."""
    ext_dir = tmp_path / "simple-popup"
    ext_dir.mkdir()

    # Write manifest
    with open(ext_dir / "manifest.json", "w") as f:
        json.dump(simple_popup_manifest, f)

    # Write background.js
    (ext_dir / "background.js").write_text(
        "chrome.runtime.onInstalled.addListener(() => {\n"
        "  console.log('Extension installed');\n"
        "});\n"
    )

    # Write popup.js
    (ext_dir / "popup.js").write_text(
        "document.getElementById('btn').addEventListener('click', () => {\n"
        "  chrome.storage.local.set({key: 'value'});\n"
        "});\n"
    )

    # Write popup.html
    (ext_dir / "popup.html").write_text(
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<body>\n"
        "  <button id='btn'>Click me</button>\n"
        "  <script src='popup.js'></script>\n"
        "</body>\n"
        "</html>\n"
    )

    # Write icon (empty placeholder)
    (ext_dir / "icon.png").write_bytes(b"PNG_PLACEHOLDER")

    return ext_dir

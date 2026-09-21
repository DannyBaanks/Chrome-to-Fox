"""Tests for Analyzer module."""

import json

from chrome2fox.analyzer import analyze_extension


def test_analyze_simple_extension(simple_popup_dir):
    """Test analyzing a simple extension."""
    report = analyze_extension(simple_popup_dir)

    assert "error" not in report
    assert report["manifest_version"] == 3
    assert report["name"] == "Simple Popup"
    assert report["compatibility_score"] == 1.0
    assert len(report["chrome_only_apis"]) == 0
    # APIs are captured with method: chrome.runtime.onInstalled, chrome.storage.local
    assert any("chrome.runtime" in api for api in report["used_apis"])
    assert any("chrome.storage" in api for api in report["used_apis"])


def test_analyze_missing_manifest(tmp_path):
    """Test analyzing a directory without manifest."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    report = analyze_extension(empty_dir)
    assert "error" in report
    assert "manifest.json not found" in report["error"]


def test_analyze_manifest_issues(simple_popup_dir):
    """Test that analyzer detects missing gecko settings."""
    report = analyze_extension(simple_popup_dir)

    # Should warn about missing browser_specific_settings
    assert any("browser_specific_settings" in issue for issue in report["manifest_issues"])

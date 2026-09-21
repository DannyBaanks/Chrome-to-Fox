"""Tests for Validator module."""

import json

from chrome2fox.validator import validate_extension


def test_validate_valid_extension(simple_popup_dir):
    """Test validating a valid extension."""
    result = validate_extension(simple_popup_dir)

    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_missing_manifest(tmp_path):
    """Test validating a directory without manifest."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = validate_extension(empty_dir)

    assert result["valid"] is False
    assert "manifest.json not found" in result["errors"]


def test_validate_warns_about_chrome_apis(simple_popup_dir):
    """Test that validator warns about remaining chrome.* APIs."""
    result = validate_extension(simple_popup_dir)

    # The simple popup has chrome.* APIs that weren't patched
    assert any("chrome.*" in w for w in result["warnings"])

"""Tests for Converter pipeline."""

import json

from chrome2fox.converter import convert_extension


def test_convert_simple_extension(simple_popup_dir, tmp_path):
    """Test converting a simple extension."""
    output_dir = tmp_path / "output"
    report = convert_extension(simple_popup_dir, output_dir)

    assert report["status"] == "success"
    assert report["manifest_version"] == 3
    assert report["files_processed"] > 0
    assert report["js_files_patched"] > 0

    # Check output manifest
    manifest_path = output_dir / "manifest.json"
    assert manifest_path.exists()

    with open(manifest_path) as f:
        manifest = json.load(f)

    assert "browser_specific_settings" in manifest
    assert "gecko" in manifest["browser_specific_settings"]


def test_convert_creates_output_directory(simple_popup_dir, tmp_path):
    """Test that conversion creates output directory."""
    output_dir = tmp_path / "new_output"
    report = convert_extension(simple_popup_dir, output_dir)

    assert output_dir.exists()
    assert (output_dir / "manifest.json").exists()

"""Tests for Package module."""

import hashlib
from pathlib import Path

from chrome2fox.package import package_extension


def test_package_creates_xpi(simple_popup_dir, tmp_path):
    """Test that packaging creates .xpi file."""
    output_xpi = tmp_path / "test.xpi"
    result = package_extension(simple_popup_dir, output_xpi)

    assert result["status"] == "success"
    assert output_xpi.exists()
    assert output_xpi.suffix == ".xpi"
    assert result["files_included"] > 0
    assert result["size_bytes"] > 0
    assert len(result["sha256"]) == 64  # SHA256 hex length


def test_package_calculates_sha256(simple_popup_dir, tmp_path):
    """Test that packaging calculates correct SHA256."""
    output_xpi = tmp_path / "test.xpi"
    result = package_extension(simple_popup_dir, output_xpi)

    # Verify SHA256 manually
    sha256 = hashlib.sha256()
    with open(output_xpi, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)

    assert result["sha256"] == sha256.hexdigest()

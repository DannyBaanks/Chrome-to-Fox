"""Tests for Manifest Transformer module."""

import json

from chrome2fox.manifest_transform import transform_manifest


def test_transform_adds_gecko_settings():
    """Test that transform adds browser_specific_settings.gecko.id."""
    manifest = {
        "manifest_version": 3,
        "name": "Test Extension",
        "version": "1.0.0",
    }

    result = transform_manifest(manifest)

    assert "browser_specific_settings" in result
    assert "gecko" in result["browser_specific_settings"]
    assert "id" in result["browser_specific_settings"]["gecko"]
    assert result["browser_specific_settings"]["gecko"]["id"].startswith("@chrome2fox-")


def test_transform_removes_chrome_fields():
    """Test that transform removes Chrome-specific fields."""
    manifest = {
        "manifest_version": 3,
        "name": "Test",
        "version": "1.0.0",
        "key": "some-chrome-key",
        "minimum_chrome_version": "102",
    }

    result = transform_manifest(manifest)

    assert "key" not in result
    assert "minimum_chrome_version" not in result


def test_transform_mv3_host_permissions():
    """Test that MV3 host_permissions are moved to permissions."""
    manifest = {
        "manifest_version": 3,
        "name": "Test",
        "version": "1.0.0",
        "permissions": ["storage"],
        "host_permissions": ["*://*.example.com/*"],
    }

    result = transform_manifest(manifest)

    assert "host_permissions" not in result
    assert "*://*.example.com/*" in result["permissions"]


def test_transform_preserves_existing_gecko():
    """Test that existing gecko settings are preserved."""
    manifest = {
        "manifest_version": 3,
        "name": "Test",
        "version": "1.0.0",
        "browser_specific_settings": {
            "gecko": {
                "id": "@my-extension",
                "strict_min_version": "115.0"
            }
        }
    }

    result = transform_manifest(manifest)

    assert result["browser_specific_settings"]["gecko"]["id"] == "@my-extension"
    assert result["browser_specific_settings"]["gecko"]["strict_min_version"] == "115.0"

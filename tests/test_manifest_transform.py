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
    """Test that MV3 host_permissions are preserved (Firefox supports them).

    Merging them into "permissions" is invalid per web-ext lint
    (MANIFEST_PERMISSIONS: Invalid permissions "<all_urls>").
    """
    manifest = {
        "manifest_version": 3,
        "name": "Test",
        "version": "1.0.0",
        "permissions": ["storage"],
        "host_permissions": ["*://*.example.com/*"],
    }

    result = transform_manifest(manifest)

    assert result["host_permissions"] == ["*://*.example.com/*"]
    assert result["permissions"] == ["storage"]


def test_transform_dnr_bumps_min_version():
    """Test that DNR usage stamps strict_min_version 113.0 (not 109.0)."""
    manifest = {
        "manifest_version": 3,
        "name": "Test",
        "version": "1.0.0",
        "permissions": ["declarativeNetRequest"],
        "declarative_net_request": {
            "rule_resources": [{"id": "ads", "enabled": True, "path": "rules.json"}]
        },
    }

    result = transform_manifest(manifest)

    assert result["browser_specific_settings"]["gecko"]["strict_min_version"] == "113.0"


def test_transform_no_dnr_keeps_min_version_109():
    """Test that non-DNR extensions keep strict_min_version 109.0."""
    manifest = {"manifest_version": 3, "name": "Test", "version": "1.0.0"}

    result = transform_manifest(manifest)

    assert result["browser_specific_settings"]["gecko"]["strict_min_version"] == "109.0"


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


def test_transform_stamps_data_collection_none():
    """Test que sella data_collection_permissions none por defecto (exigido AMO)."""
    manifest = {"manifest_version": 3, "name": "Test", "version": "1.0.0"}
    result = transform_manifest(manifest)
    assert result["browser_specific_settings"]["gecko"]["data_collection_permissions"] == {"required": ["none"]}


def test_transform_preserves_data_collection():
    """Test que respeta data_collection_permissions declarado por el dev."""
    manifest = {
        "manifest_version": 3, "name": "Test", "version": "1.0.0",
        "browser_specific_settings": {"gecko": {
            "id": "@x", "data_collection_permissions": {"required": ["websiteActivity"]}}},
    }
    result = transform_manifest(manifest)
    assert result["browser_specific_settings"]["gecko"]["data_collection_permissions"] == {"required": ["websiteActivity"]}

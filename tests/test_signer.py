"""Tests for Signer module (all mocked: no network, no real keys)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

from chrome2fox import signer
from chrome2fox.signer import sign_extension


def test_sign_missing_credentials(simple_popup_dir):
    """Test that signing without keys fails closed without subprocess."""
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("AMO_API_KEY", None)
        os.environ.pop("AMO_API_SECRET", None)
        with patch("subprocess.run") as run:
            result = sign_extension(simple_popup_dir)
    assert result["status"] == "error"
    assert any("credentials" in e for e in result["errors"])
    run.assert_not_called()


def test_sign_invalid_channel(simple_popup_dir):
    """Test that a bad channel is rejected."""
    result = sign_extension(simple_popup_dir, api_key="k", api_secret="s", channel="nope")
    assert result["status"] == "error"
    assert any("channel" in e for e in result["errors"])


def test_sign_missing_manifest(tmp_path):
    """Test that a dir without manifest.json is rejected."""
    result = sign_extension(tmp_path, api_key="k", api_secret="s")
    assert result["status"] == "error"
    assert any("manifest.json" in e for e in result["errors"])


def test_sign_success_mocked(simple_popup_dir, tmp_path):
    """Test the success path with mocked web-ext (secret never leaks)."""
    arts = tmp_path / "signed"
    arts.mkdir()
    fake_xpi = arts / "ext-1.0.xpi"
    fake_xpi.write_bytes(b"FAKEXPI")

    proc = MagicMock(returncode=0, stdout="signed", stderr="")
    with patch.object(signer.shutil, "which", return_value="/usr/bin/web-ext"):
        with patch("subprocess.run", return_value=proc) as run:
            result = sign_extension(
                simple_popup_dir, api_key="KEY", api_secret="SUPERSECRET",
                artifacts_dir=arts,
            )
    assert result["status"] == "success"
    assert result["signed_xpi"] == str(fake_xpi)
    argv = run.call_args[0][0]
    assert "SUPERSECRET" not in " ".join(argv)
    assert "SUPERSECRET" not in str(result)
    child_env = run.call_args[1]["env"]
    assert child_env["WEB_EXT_API_KEY"] == "KEY"
    assert child_env["WEB_EXT_API_SECRET"] == "SUPERSECRET"


def test_sign_webext_failure_mocked(simple_popup_dir, tmp_path):
    """Test that a web-ext error surfaces as error status."""
    proc = MagicMock(returncode=1, stdout="", stderr="401 Unauthorized: bad JWT")
    with patch.object(signer.shutil, "which", return_value="/usr/bin/web-ext"):
        with patch("subprocess.run", return_value=proc):
            result = sign_extension(
                simple_popup_dir, api_key="k", api_secret="s",
                artifacts_dir=tmp_path / "a",
            )
    assert result["status"] == "error"
    assert any("401" in e for e in result["errors"])


def test_sign_no_webext(simple_popup_dir):
    """Test that missing web-ext (no binary, no npx) is an error."""
    with patch.object(signer.shutil, "which", return_value=None):
        with patch("subprocess.run") as run:
            result = sign_extension(simple_popup_dir, api_key="k", api_secret="s")
    assert result["status"] == "error"
    assert any("web-ext" in e for e in result["errors"])
    run.assert_not_called()

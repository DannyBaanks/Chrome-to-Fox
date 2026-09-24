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


def test_sign_success_mocked(simple_popup_dir, tmp_path, monkeypatch):
    """Test the success path with mocked web-ext (secret never leaks)."""
    monkeypatch.setenv("CHROME2FOX_CONFIG", str(tmp_path / "cfg"))
    arts = tmp_path / "signed"
    arts.mkdir()
    fake_xpi = arts / "ext-1.0.xpi"
    fake_xpi.write_bytes(b"FAKEXPI")

    proc = MagicMock(returncode=0, stdout="signed", stderr="")
    with patch.object(signer.shutil, "which", return_value="/usr/bin/web-ext"):
        with patch("subprocess.run", return_value=proc) as run:
            result = sign_extension(
                simple_popup_dir, api_key="KEY", api_secret="SUPERSECRET-0123456789-abcdef",
                artifacts_dir=arts,
            )
    assert result["status"] == "success"
    assert result["signed_xpi"] == str(fake_xpi)
    argv = run.call_args[0][0]
    assert "SUPERSECRET" not in " ".join(argv)
    assert "SUPERSECRET" not in str(result)
    child_env = run.call_args[1]["env"]
    assert child_env["WEB_EXT_API_KEY"] == "KEY"
    assert child_env["WEB_EXT_API_SECRET"] == "SUPERSECRET-0123456789-abcdef"


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


def test_wait_signed_download_mocked(tmp_path, monkeypatch):
    """Test wait+download path with mocked AMO (no network)."""
    monkeypatch.setenv("CHROME2FOX_CONFIG", str(tmp_path / "cfg"))
    from chrome2fox.signer import wait_signed
    import io, json

    version_payload = {"results": [
        {"version": "0.1.0", "reviewed": True,
         "file": {"id": 1, "status": "public", "url": "https://amo/file/1"}}]}
    fake_file = io.BytesIO(b"SIGNEDXPI" * 100)

    class Resp:
        def __init__(self, payload=None, binary=None):
            self._p = payload; self._b = binary
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, n=-1):
            return self._b.read(n) if self._b else b""
    import urllib.request as urlreq
    calls = {"n": 0}
    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url.endswith(".xpi") or "/file/" in url:
            return Resp(binary=io.BytesIO(b"SIGNEDXPI" * 100))
        return Resp(payload=version_payload)
    with patch("json.load", return_value=version_payload):
        with patch.object(urlreq, "urlopen", side_effect=fake_urlopen):
            with patch("time.sleep", return_value=None):
                result = wait_signed("my-guid", "0.1.0", api_key="K",
                                     api_secret="S-0123456789-abcdef-0123456789ab", artifacts_dir=tmp_path,
                                     poll_seconds=0, max_waits=2)
    assert result["status"] == "success"
    assert Path(result["signed_xpi"]).exists()
    assert "S" * 3 not in str(result)


def test_wait_signed_still_pending(tmp_path):
    """Test waiter gives up cleanly while AMO still reviews."""
    from chrome2fox.signer import wait_signed
    pending = {"results": [
        {"version": "0.1.0", "reviewed": None,
         "file": {"id": 1, "status": "unreviewed", "url": None}}]}
    import urllib.request as urlreq
    with patch("json.load", return_value=pending):
        with patch.object(urlreq, "urlopen") as uo:
            uo.return_value.__enter__.return_value = None
            with patch("time.sleep", return_value=None):
                result = wait_signed("g", "0.1.0", api_key="K", api_secret="S-0123456789-abcdef-0123456789ab",
                                     artifacts_dir=tmp_path, poll_seconds=0, max_waits=2)
    assert result["status"] == "pending"
    assert result["signed_xpi"] is None


def test_get_status_awaiting(tmp_path):
    """Test status reports awaiting with review link (mocked)."""
    from chrome2fox import signer as S
    from chrome2fox.signer import get_status
    addon = {"id": 123, "status": "incomplete"}
    listing = {"results": [
        {"id": 9, "version": "0.1.0", "channel": "unlisted", "reviewed": None,
         "file": {"id": 1, "status": "unreviewed"}}]}
    with patch.object(S, "_amo_get", side_effect=[addon, listing]):
        r = get_status("g", "0.1.0", api_key="K" + "0" * 31, api_secret="S" + "0" * 31)
    assert r["overall"] == "awaiting"
    v = r["versions"][0]
    assert v["state"] == "awaiting"
    assert v["review_url"] == "https://addons.mozilla.org/en-US/developers/addon/123/versions/9"


def test_get_status_approved(tmp_path):
    """Test status reports approved when reviewed (mocked)."""
    from chrome2fox import signer as S
    from chrome2fox.signer import get_status
    addon = {"id": 123, "status": "incomplete"}
    listing = {"results": [
        {"id": 9, "version": "0.1.0", "channel": "unlisted", "reviewed": "2026-09-23T00:00:00Z",
         "file": {"id": 1, "status": "public"}}]}
    with patch.object(S, "_amo_get", side_effect=[addon, listing]):
        r = get_status("g", api_key="K" + "0" * 31, api_secret="S" + "0" * 31)
    assert r["overall"] == "approved"
    assert r["versions"][0]["state"] == "approved"


def test_get_status_no_creds():
    """Test status fails closed without keys."""
    from chrome2fox.signer import get_status
    import os
    with patch.dict("os.environ", {}, clear=False):
        os.environ.pop("AMO_API_KEY", None)
        os.environ.pop("AMO_API_SECRET", None)
        r = get_status("g")
    assert r["overall"] == "error"


def test_ledger_record_and_load(tmp_path, monkeypatch):
    """Test ledger roundtrip (usa dir temporal, no toca ~/.config)."""
    from chrome2fox import ledger
    monkeypatch.setenv("CHROME2FOX_CONFIG", str(tmp_path))
    assert ledger.load_ledger() == []
    ledger.record_submission({"guid": "g1", "version": "1.0", "channel": "unlisted"})
    ledger.record_submission({"guid": "g1", "version": "1.0", "channel": "unlisted"})
    items = ledger.load_ledger()
    assert len(items) == 1  # misma guid+version actualiza, no duplica
    assert items[0]["channel"] == "unlisted"


def test_my_addons_no_creds(tmp_path, monkeypatch):
    """Test my-addons sin claves: solo registro, sin red."""
    from chrome2fox import ledger
    from chrome2fox.signer import my_addons
    monkeypatch.setenv("CHROME2FOX_CONFIG", str(tmp_path))
    monkeypatch.delenv("AMO_API_KEY", raising=False)
    monkeypatch.delenv("AMO_API_SECRET", raising=False)
    ledger.record_submission({"guid": "g1", "version": "1.0"})
    r = my_addons()
    assert len(r["submissions"]) == 1
    assert r["submissions"][0]["state"] == "unknown"


def test_my_addons_live_mocked(tmp_path, monkeypatch):
    """Test my-addons con AMO mockeado (cuenta + estado vivo)."""
    from unittest.mock import patch
    from chrome2fox import ledger
    from chrome2fox import signer as S
    from chrome2fox.signer import my_addons
    monkeypatch.setenv("CHROME2FOX_CONFIG", str(tmp_path))
    ledger.record_submission({"guid": "g1", "version": "1.0", "channel": "unlisted"})
    me = {"username": "u", "is_addon_developer": True, "num_addons_listed": 0}
    listing = {"results": []}
    status = {"overall": "awaiting", "versions": [{"review_url": "http://x"}]}
    with patch.object(S, "_amo_get", side_effect=[me, listing]):
        with patch.object(S, "get_status", return_value=status):
            r = my_addons(api_key="K" + "0" * 31, api_secret="S" + "0" * 31)
    assert r["account"]["username"] == "u"
    assert r["submissions"][0]["state"] == "awaiting"
    assert r["submissions"][0]["review_url"] == "http://x"


def test_search_public_mocked():
    """Test buscador publico con red mockeada."""
    from unittest.mock import patch
    import io
    from chrome2fox.signer import search_addons
    payload = {"count": 1, "results": [
        {"name": {"en": "Foo"}, "slug": "foo", "guid": "g",
         "average_daily_users": 5, "current_version": {"version": "2.0"}}]}
    import urllib.request as urlreq
    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, n=-1): return b""
    with patch.object(urlreq, "urlopen", return_value=Resp()):
        with patch("json.load", return_value=payload):
            r = search_addons("foo")
    assert r["count"] == 1
    assert r["results"][0]["name"] == "Foo"
    assert r["results"][0]["url"].endswith("/firefox/addon/foo/")

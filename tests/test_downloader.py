"""Tests del downloader URL/id -> carpeta (red mockeada, sin Google)."""

import io
import struct
import zipfile
from unittest.mock import patch

from chrome2fox import downloader as D
from chrome2fox.downloader import extract_id, fetch_extension, looks_like_url_or_id, unpack_crx


def _fake_crx3(manifest: bytes = b'{"manifest_version":3,"name":"T","version":"1.0"}',
               extra: dict | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", manifest)
        for name, data in (extra or {}).items():
            zf.writestr(name, data)
    blob = buf.getvalue()
    header = b"\x00" * 8
    return b"Cr24" + struct.pack("<II", 3, len(header)) + header + blob


def test_extract_id_variants():
    assert extract_id("https://chromewebstore.google.com/detail/x/cjpalhdlnbpafiamejdnhcphjbkeiagm") == "cjpalhdlnbpafiamejdnhcphjbkeiagm"
    assert extract_id("cjpalhdlnbpafiamejdnhcphjbkeiagm") == "cjpalhdlnbpafiamejdnhcphjbkeiagm"
    assert extract_id("basura") is None


def test_looks_like_url_or_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ext").mkdir()
    assert not looks_like_url_or_id("ext")
    assert looks_like_url_or_id("cjpalhdlnbpafiamejdnhcphjbkeiagm")
    assert looks_like_url_or_id("https://chromewebstore.google.com/detail/x/cjpalhdlnbpafiamejdnhcphjbkeiagm")


def test_unpack_crx3(tmp_path):
    n = unpack_crx_bytes(_fake_crx3(), tmp_path / "out")
    assert n >= 1
    assert (tmp_path / "out" / "manifest.json").exists()


def unpack_crx_bytes(blob: bytes, out):
    p = out.parent / "_t.crx"
    p.write_bytes(blob)
    try:
        return unpack_crx(p, out)
    finally:
        p.unlink(missing_ok=True)


def test_unpack_rejects_bad_magic(tmp_path):
    import pytest
    p = tmp_path / "x.crx"
    p.write_bytes(b"NOPE" + b"0" * 20)
    with pytest.raises(ValueError):
        unpack_crx(p, tmp_path / "o")


def test_unpack_blocks_zipslip(tmp_path):
    import pytest
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil.js", b"x")
    blob = buf.getvalue()
    header = b"\x00" * 8
    crx = b"Cr24" + struct.pack("<II", 3, len(header)) + header + blob
    p = tmp_path / "x.crx"
    p.write_bytes(crx)
    with pytest.raises(ValueError, match="zip-slip"):
        unpack_crx(p, tmp_path / "o")


def test_fetch_mocked(tmp_path):
    blob = _fake_crx3(extra={"bg.js": b"chrome.tabs.query()"})
    class Resp:
        def __init__(self, data): self._d = io.BytesIO(data)
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, n=-1): return self._d.read(n)
    import urllib.request as urlreq
    with patch.object(urlreq, "urlopen", return_value=Resp(blob)):
        r = fetch_extension("cjpalhdlnbpafiamejdnhcphjbkeiagm", tmp_path / "ext")
    assert r["status"] == "success"
    assert r["name"] == "T" and r["files"] == 2
    assert (tmp_path / "ext" / "bg.js").exists()


def test_fetch_bad_id(tmp_path):
    r = fetch_extension("basura", tmp_path / "ext")
    assert r["status"] == "error"

"""Signer — Submit a Firefox extension to AMO for signing via web-ext.

Uses `web-ext sign` so the .xpi can be installed permanently (Mozilla
signature required since Firefox 48). Default channel is "unlisted":
signed without public listing, ideal for self-distribution pipelines.

Credentials NEVER appear on the command line or in results: they travel
to web-ext through the child-process environment (WEB_EXT_API_KEY /
WEB_EXT_API_SECRET), read from explicit args or AMO_API_KEY /
AMO_API_SECRET. Live signing needs real AMO keys, so it is covered by
mocked unit tests, not by network tests.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

CHANNELS = ("unlisted", "listed")


def _find_webext() -> list[str] | None:
    """Locate web-ext: installed binary first, npx fallback."""
    if shutil.which("web-ext"):
        return ["web-ext"]
    if shutil.which("npx"):
        return ["npx", "-y", "web-ext"]
    return None


def sign_extension(
    ext_dir: Path,
    api_key: str | None = None,
    api_secret: str | None = None,
    channel: str = "unlisted",
    artifacts_dir: Path | None = None,
    timeout_seconds: int = 300,
    amo_base_url: str | None = None,
) -> dict[str, Any]:
    """Submit an extension to AMO and retrieve the signed .xpi.

    Args:
        ext_dir: Converted Firefox extension directory (source-dir).
        api_key: AMO JWT issuer. Defaults to AMO_API_KEY env var.
        api_secret: AMO JWT secret. Defaults to AMO_API_SECRET env var.
        channel: "unlisted" (signed, not listed) or "listed" (public).
        artifacts_dir: Where web-ext saves the signed .xpi.
        timeout_seconds: Give up waiting for AMO after this long.
        amo_base_url: Override submission API (e.g. staging server).

    Returns:
        Result dict. The secret is NEVER included.
    """
    ext_dir = Path(ext_dir)
    result: dict[str, Any] = {
        "input": str(ext_dir),
        "channel": channel,
        "status": "error",
        "signed_xpi": None,
        "artifacts_dir": None,
        "errors": [],
    }

    if channel not in CHANNELS:
        result["errors"].append(f"Invalid channel: {channel} (use unlisted|listed)")
        return result

    manifest = ext_dir / "manifest.json"
    if not manifest.exists():
        result["errors"].append(f"manifest.json not found in {ext_dir}")
        return result

    key = api_key or os.environ.get("AMO_API_KEY", "")
    secret = api_secret or os.environ.get("AMO_API_SECRET", "")
    if not key or not secret:
        result["errors"].append(
            "Missing AMO credentials. Set AMO_API_KEY + AMO_API_SECRET "
            "(from https://addons.mozilla.org/developers/addon/api/key/) "
            "or pass --api-key/--api-secret."
        )
        return result

    runner = _find_webext()
    if runner is None:
        result["errors"].append("web-ext not found (need `npm i -g web-ext` or npx)")
        return result

    out_dir = Path(artifacts_dir) if artifacts_dir else ext_dir.parent / "signed"
    out_dir.mkdir(parents=True, exist_ok=True)
    result["artifacts_dir"] = str(out_dir)

    before = {f.name for f in out_dir.glob("*.xpi")}
    cmd = [
        *runner, "sign",
        "--source-dir", str(ext_dir),
        "--artifacts-dir", str(out_dir),
        "--channel", channel,
        "--timeout", str(int(timeout_seconds * 1000)),
        "--no-input",
    ]
    if amo_base_url:
        cmd += ["--amo-base-url", amo_base_url]

    env = dict(os.environ)
    env["WEB_EXT_API_KEY"] = key
    env["WEB_EXT_API_SECRET"] = secret

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds + 60, env=env)
    except subprocess.TimeoutExpired:
        result["errors"].append(f"web-ext sign timed out after {timeout_seconds}s")
        return result
    except Exception as e:
        result["errors"].append(f"Could not run web-ext: {e}")
        return result

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
        result["errors"].append("web-ext sign failed: " + " | ".join(tail))
        return result

    new_files = [f for f in out_dir.glob("*.xpi") if f.name not in before]
    if not new_files:
        # web-ext reuses names on re-sign: take the newest .xpi instead.
        all_xpi = sorted(out_dir.glob("*.xpi"), key=lambda f: f.stat().st_mtime)
        if all_xpi:
            new_files = [all_xpi[-1]]
    if not new_files:
        result["errors"].append("web-ext reported success but no .xpi in artifacts dir")
        return result

    signed = max(new_files, key=lambda f: f.stat().st_mtime)
    result["status"] = "success"
    result["signed_xpi"] = str(signed)
    return result

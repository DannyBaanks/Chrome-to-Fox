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
    try:
        from .ledger import record_submission
        import json as _json
        m = _json.loads((ext_dir / "manifest.json").read_text(encoding="utf-8"))
        record_submission({
            "name": m.get("name"), "guid": (m.get("browser_specific_settings", {}) or {}).get("gecko", {}).get("id", ""),
            "version": m.get("version"), "channel": channel, "signed_xpi": str(signed),
        })
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# Wait + download: completa el pipeline cuando AMO termina la revision.
# ---------------------------------------------------------------------------

def _amo_get(path: str, api_key: str, api_secret: str, amo_base_url: str | None) -> Any:
    """GET autenticado (JWT) a la API v5 de AMO. Sin secretos en el retorno."""
    import json as _json
    import time as _time
    import urllib.request as _url
    import jwt as _jwt

    base = (amo_base_url or "https://addons.mozilla.org/api/v5/").rstrip("/") + "/"
    now = int(_time.time())
    token = _jwt.encode({"iss": api_key, "iat": now, "exp": now + 300}, api_secret, algorithm="HS256")
    req = _url.Request(base + path.lstrip("/"), headers={"Authorization": f"JWT {token}"})
    with _url.urlopen(req, timeout=30) as res:
        return _json.load(res)


def wait_signed(
    guid_or_id: str,
    version: str,
    api_key: str | None = None,
    api_secret: str | None = None,
    artifacts_dir: Path | None = None,
    poll_seconds: int = 120,
    max_waits: int = 15,
    amo_base_url: str | None = None,
) -> dict[str, Any]:
    """Espera la revision de AMO y descarga el .xpi firmado.

    Sondea versions/ hasta que file.status salga de la cola de revision
    (unreviewed/awaiting_review) y descarga el fichero firmado con el JWT.
    Las credenciales solo viajan en el header Authorization, nunca en disco.
    """
    import time as _time
    import urllib.request as _url

    result: dict[str, Any] = {
        "guid": guid_or_id, "version": version,
        "status": "pending", "signed_xpi": None, "errors": [],
    }
    key = api_key or os.environ.get("AMO_API_KEY", "")
    secret = api_secret or os.environ.get("AMO_API_SECRET", "")
    if not key or not secret:
        result["status"] = "error"
        result["errors"].append("Missing AMO credentials (AMO_API_KEY + AMO_API_SECRET).")
        return result

    out_dir = Path(artifacts_dir) if artifacts_dir else Path.cwd() / "signed"
    out_dir.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, int(max_waits) + 1):
        try:
            data = _amo_get(f"addons/addon/{guid_or_id}/versions/", key, secret, amo_base_url)
        except Exception as e:
            result["errors"].append(f"poll {attempt}: {type(e).__name__}: {str(e)[:150]}")
            _time.sleep(poll_seconds)
            continue
        match = next((v for v in data.get("results", []) if str(v.get("version")) == str(version)), None)
        if match is None and str(version).isdigit():
            # Algunas respuestas vienen por id de version en vez de lista.
            try:
                match = _amo_get(f"addons/addon/{guid_or_id}/versions/{version}/", key, secret, amo_base_url)
            except Exception:
                match = None
        f = (match or {}).get("file") or {}
        state = f.get("status")
        result["attempts"] = attempt
        if match and (match.get("reviewed") or (state and state not in ("unreviewed", "awaiting_review"))):
            url = f.get("url")
            if not url:
                result["status"] = "error"
                result["errors"].append("AMO approved but gave no download url")
                return result
            try:
                now = int(_time.time())
                import jwt as _jwt
                token = _jwt.encode({"iss": key, "iat": now, "exp": now + 300}, secret, algorithm="HS256")
                req = _url.Request(url, headers={"Authorization": f"JWT {token}"})
                dest = out_dir / f"{guid_or_id}-{version}-signed.xpi"
                with _url.urlopen(req, timeout=120) as res, open(dest, "wb") as fh:
                    while True:
                        chunk = res.read(65536)
                        if not chunk:
                            break
                        fh.write(chunk)
            except Exception as e:
                result["status"] = "error"
                result["errors"].append(f"download failed: {type(e).__name__}: {str(e)[:150]}")
                return result
            result["status"] = "success"
            result["signed_xpi"] = str(dest)
            result["file_status"] = state
            try:
                from .ledger import record_submission
                record_submission({"guid": guid_or_id, "version": str(version),
                                   "signed_xpi": str(dest), "downloaded": True})
            except Exception:
                pass
            return result
        if attempt < int(max_waits):
            _time.sleep(poll_seconds)
    result["errors"].append(f"still in review after {max_waits} polls")
    return result


# ---------------------------------------------------------------------------
# Status: pregunta a AMO como va la revision (awaiting con link / aprobada).
# ---------------------------------------------------------------------------

def get_status(
    guid_or_id: str,
    version: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    amo_base_url: str | None = None,
) -> dict[str, Any]:
    """Consulta el estado de revision en AMO.

    Args:
        guid_or_id: guid de la extension o id numerico del addon en AMO.
        version: version concreta ("0.1.0") o id de version ("6509541").
            Si se omite, reporta todas las versiones encontradas.

    Returns:
        Dict con overall ("approved" | "awaiting" | "not_found" | "error"),
        review_url por version y detalle de fichero. Sin secretos.
        Exit-code sugerido: approved -> 0, lo demas -> 1.
    """
    result: dict[str, Any] = {
        "guid": guid_or_id, "overall": "error",
        "addon_id": None, "addon_status": None,
        "versions": [], "errors": [],
    }
    key = api_key or os.environ.get("AMO_API_KEY", "")
    secret = api_secret or os.environ.get("AMO_API_SECRET", "")
    if not key or not secret:
        result["errors"].append("Missing AMO credentials (AMO_API_KEY + AMO_API_SECRET).")
        return result

    try:
        addon = _amo_get(f"addons/addon/{guid_or_id}/", key, secret, amo_base_url)
    except Exception as e:
        result["errors"].append(f"addon lookup failed: {type(e).__name__}: {str(e)[:150]}")
        return result
    addon_id = addon.get("id")
    result["addon_id"] = addon_id
    result["addon_status"] = addon.get("status")

    wanted = str(version) if version is not None else None
    found: list[dict[str, Any]] = []
    try:
        listing = _amo_get(f"addons/addon/{guid_or_id}/versions/", key, secret, amo_base_url)
        found = listing.get("results", []) or []
    except Exception:
        found = []
    picks: list[dict[str, Any]] = []
    if wanted and wanted.isdigit():
        try:
            picks = [_amo_get(f"addons/addon/{guid_or_id}/versions/{wanted}/", key, secret, amo_base_url)]
        except Exception as e:
            result["errors"].append(f"version lookup failed: {type(e).__name__}: {str(e)[:150]}")
    else:
        picks = [v for v in found if wanted is None or str(v.get("version")) == wanted]
        # Las versiones unlisted no siempre listan: intenta detalle directo.
        if wanted and not picks and addon_id:
            try:
                maybe = _amo_get(f"addons/addon/{addon_id}/versions/{wanted}/", key, secret, amo_base_url)
                if str(maybe.get("version")) == wanted:
                    picks = [maybe]
            except Exception:
                pass

    if not picks:
        result["overall"] = "not_found"
        result["errors"].append(f"version {wanted or '(any)'} not found on AMO")
        return result

    states = set()
    for v in picks:
        f = v.get("file") or {}
        state = f.get("status")
        reviewed = bool(v.get("reviewed"))
        done = reviewed or (state and state not in ("unreviewed", "awaiting_review"))
        states.add("approved" if done else "awaiting")
        vid = v.get("id")
        result["versions"].append({
            "version": v.get("version"),
            "version_id": vid,
            "channel": v.get("channel"),
            "reviewed": v.get("reviewed"),
            "file_status": state,
            "state": "approved" if done else "awaiting",
            "review_url": (
                f"https://addons.mozilla.org/en-US/developers/addon/{addon_id}/versions/{vid}"
                if addon_id and vid else None
            ),
        })
    result["overall"] = "approved" if states == {"approved"} else "awaiting"
    return result


# ---------------------------------------------------------------------------
# my-addons: lo tuyo (registro local + estado vivo) y lo publico (buscador).
# ---------------------------------------------------------------------------

def my_addons(api_key=None, api_secret=None, amo_base_url=None, refresh=True) -> dict[str, Any]:
    """Tus envios: registro local cruzado con el estado vivo de AMO.

    Incluye tu ficha (username, es developer?) y tus addons listed visibles
    en el buscador por autor. Sin credenciales muestra solo el registro.
    """
    from .ledger import load_ledger
    result: dict[str, Any] = {"account": {}, "submissions": [], "listed": [], "errors": []}
    key = api_key or os.environ.get("AMO_API_KEY", "")
    secret = api_secret or os.environ.get("AMO_API_SECRET", "")
    entries = load_ledger()
    if not key or not secret:
        result["submissions"] = [{**e, "state": "unknown"} for e in entries]
        result["errors"].append("Sin credenciales: solo registro local (pon AMO_API_KEY + AMO_API_SECRET para estado vivo).")
        return result
    try:
        me = _amo_get("accounts/profile/", key, secret, amo_base_url)
        result["account"] = {
            "username": me.get("username"),
            "is_addon_developer": me.get("is_addon_developer"),
            "num_addons_listed": me.get("num_addons_listed"),
        }
        username = me.get("username") or ""
    except Exception as e:
        result["errors"].append(f"profile failed: {type(e).__name__}: {str(e)[:120]}")
        result["submissions"] = [{**e, "state": "unknown"} for e in entries]
        return result
    if username:
        try:
            import urllib.parse as _up
            found = _amo_get(f"addons/search/?author={_up.quote(str(username))}&page_size=25",
                             key, secret, amo_base_url)
            for a in found.get("results", []):
                cv = a.get("current_version") or {}
                result["listed"].append({
                    "name": a.get("name"), "slug": a.get("slug"), "guid": a.get("guid"),
                    "version": cv.get("version"), "reviewed": cv.get("reviewed"),
                    "url": f"https://addons.mozilla.org/firefox/addon/{a.get('slug')}/",
                })
        except Exception as e:
            result["errors"].append(f"author search failed: {type(e).__name__}: {str(e)[:120]}")
    for e in entries:
        item = dict(e)
        if refresh:
            try:
                st = get_status(e.get("guid", ""), e.get("version"), key, secret, amo_base_url)
                item["state"] = st.get("overall")
                item["review_url"] = (st.get("versions") or [{}])[0].get("review_url")
            except Exception as ex:
                item["state"] = "unknown"
                result["errors"].append(f"status {e.get('guid')}: {type(ex).__name__}")
        else:
            item["state"] = item.get("state", "unknown")
        result["submissions"].append(item)
    return result


def search_addons(query: str, page_size: int = 10, amo_base_url: str | None = None) -> dict[str, Any]:
    """Busca addons PUBLICOS en AMO (sin credenciales)."""
    import json as _json
    import urllib.parse as _up
    import urllib.request as _url
    base = (amo_base_url or "https://addons.mozilla.org/api/v5/").rstrip("/") + "/"
    url = base + "addons/search/?" + _up.urlencode({"q": query, "page_size": max(1, min(page_size, 25))})
    try:
        with _url.urlopen(url, timeout=30) as res:
            data = _json.load(res)
    except Exception as e:
        return {"query": query, "count": 0, "results": [],
                "errors": [f"search failed: {type(e).__name__}: {str(e)[:150]}"]}
    out = []
    for a in data.get("results", []):
        cv = a.get("current_version") or {}
        name = a.get("name")
        out.append({
            "name": next(iter(name.values())) if isinstance(name, dict) and name else name,
            "slug": a.get("slug"), "guid": a.get("guid"),
            "users": a.get("average_daily_users"),
            "version": cv.get("version"),
            "url": f"https://addons.mozilla.org/firefox/addon/{a.get('slug')}/",
        })
    return {"query": query, "count": data.get("count"), "results": out, "errors": []}

"""Downloader — Baja una extension desde Chrome Web Store por URL o id.

Acepta lo mismo que fox-convert (URL completa del store o id suelto),
pero el .crx se desempaqueta para pasarlo por EL MOTOR de chrome2fox
(analyze/convert/validate/package...). Solo stdlib: urllib + zipfile.

CRX3: b"Cr24" + u32 version(3) + u32 header_size + header + zip.
CRX2: b"Cr24" + u32 version(2) + u32 pubkey_len + u32 sig_len + zip.
"""

import re
import struct
import urllib.parse as _up
import urllib.request as _url
import zipfile
from pathlib import Path
from typing import Any

STORE_URL = (
    "https://clients2.google.com/service/update2/crx"
    "?response=redirect&prodversion=120.0&acceptformat=crx2,crx3&x=id%3D{id}%26uc"
)
CHROME_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_ID_RE = re.compile(r"\b[a-p]{32}\b")


def looks_like_url_or_id(source: str) -> bool:
    """True si parece URL del store o id (y NO una carpeta existente)."""
    if Path(source).exists():
        return False
    s = source.strip()
    return s.startswith("http") or bool(_ID_RE.fullmatch(s))


def extract_id(source: str) -> str | None:
    """Extrae el id de 32 letras de una URL del store o lo valida suelto."""
    s = source.strip().rstrip("/")
    m = _ID_RE.search(s)
    return m.group(0) if m else None


def download_crx(ext_id: str, dest: Path, timeout_seconds: int = 120) -> Path:
    """Descarga el .crx desde Google. Lanza en caso de fallo de red."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = _url.Request(STORE_URL.format(id=_up.quote(ext_id)),
                       headers={"User-Agent": CHROME_UA})
    with _url.urlopen(req, timeout=timeout_seconds) as res, open(dest, "wb") as fh:
        head = res.read(4)
        fh.write(head)
        while True:
            chunk = res.read(65536)
            if not chunk:
                break
            fh.write(chunk)
    size = dest.stat().st_size
    if size == 0:
        raise ValueError("Google devolvio respuesta vacia (HTTP 204): id invalido o descarga bloqueada")
    if dest.read_bytes()[:4] != b"Cr24":
        raise ValueError("Google no devolvio un .crx (respuesta no-CRX: posible bloqueo anti-scraping)")
    return dest


def _zip_offset(data: bytes) -> int:
    """Offset donde empieza el zip dentro del .crx (CRX2 y CRX3)."""
    if len(data) < 12 or data[:4] != b"Cr24":
        raise ValueError("no es un .crx valido (magic)")
    (version,) = struct.unpack("<I", data[4:8])
    if version == 3:
        (header_size,) = struct.unpack("<I", data[8:12])
        return 12 + header_size
    if version == 2:
        pubkey_len, sig_len = struct.unpack("<II", data[8:16])
        return 16 + pubkey_len + sig_len
    raise ValueError(f"version CRX no soportada: {version}")


def unpack_crx(crx_path: Path, out_dir: Path) -> int:
    """Extrae el zip del .crx con guardia anti zip-slip. Devuelve n archivos."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = Path(crx_path).read_bytes()
    offset = _zip_offset(data)
    tmp = out_dir / "_payload.zip"
    tmp.write_bytes(data[offset:])
    count = 0
    try:
        with zipfile.ZipFile(tmp) as zf:
            for info in zf.infolist():
                target = (out_dir / info.filename).resolve()
                if target != out_dir.resolve() and out_dir.resolve() not in target.parents:
                    raise ValueError(f"zip-slip bloqueado: {info.filename}")
                zf.extract(info, out_dir)
                count += 1
    finally:
        tmp.unlink(missing_ok=True)
    return count


def fetch_extension(source: str, out_dir: Path,
                    timeout_seconds: int = 120) -> dict[str, Any]:
    """URL/id -> carpeta con la extension desempaquetada. Reporte dict."""
    import json as _json
    out_dir = Path(out_dir)
    result: dict[str, Any] = {
        "input": source, "status": "error",
        "id": None, "name": None, "version": None,
        "files": 0, "output": str(out_dir), "errors": [],
    }
    ext_id = extract_id(source)
    if not ext_id:
        result["errors"].append("no es URL del Chrome Web Store ni id (32 letras a-p)")
        return result
    result["id"] = ext_id
    try:
        crx = download_crx(ext_id, out_dir / "_download.crx", timeout_seconds)
    except Exception as e:
        result["errors"].append(f"descarga fallo: {type(e).__name__}: {str(e)[:150]}")
        return result
    try:
        result["files"] = unpack_crx(crx, out_dir)
    except Exception as e:
        result["errors"].append(f"desempaquetado fallo: {e}")
        return result
    finally:
        crx.unlink(missing_ok=True)
    try:
        m = _json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        result["name"] = m.get("name")
        result["version"] = m.get("version")
    except Exception:
        pass
    if not (out_dir / "manifest.json").exists():
        result["errors"].append("el .crx no trae manifest.json")
        return result
    result["status"] = "success"
    return result

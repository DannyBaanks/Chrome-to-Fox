"""Ledger — Registro local de envios a AMO hechos con chrome2fox.

AMO no lista tus versiones unlisted en el buscador, asi que cada `sign`
exitoso (o cada descarga via wait) se anota aqui:
~/.config/chrome2fox/submissions.json (o $CHROME2FOX_CONFIG).
`my-addons` cruza este registro con el estado vivo de AMO.
Solo metadata (guid, version, canal, fechas): jamas secretos.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def ledger_path() -> Path:
    """Ruta del registro (XDG o override para tests)."""
    override = os.environ.get("CHROME2FOX_CONFIG")
    base = Path(override) if override else Path(
        os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    ) / "chrome2fox"
    return base / "submissions.json"


def load_ledger() -> list[dict[str, Any]]:
    """Lee el registro (lista vacia si no existe o esta corrupto)."""
    path = ledger_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def record_submission(entry: dict[str, Any]) -> dict[str, Any]:
    """Anota/actualiza un envio (clave: guid + version). Devuelve la entrada."""
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    items = load_ledger()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = dict(entry)
    entry.setdefault("signed_at", now)
    entry["updated_at"] = now
    for i, old in enumerate(items):
        if old.get("guid") == entry.get("guid") and old.get("version") == entry.get("version"):
            items[i] = {**old, **entry}
            break
    else:
        items.append(entry)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return entry

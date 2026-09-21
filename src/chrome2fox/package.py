"""Package — Create .xpi from Firefox extension directory."""

import hashlib
import zipfile
from pathlib import Path
from typing import Any


def package_extension(ext_path: Path, output_xpi: Path) -> dict[str, Any]:
    """Package a Firefox extension directory as .xpi file.

    Args:
        ext_path: Path to Firefox extension directory
        output_xpi: Output .xpi file path

    Returns:
        Package result with path, size, sha256
    """
    ext_path = Path(ext_path)
    output_xpi = Path(output_xpi)

    # Ensure output has .xpi extension
    if not output_xpi.suffix:
        output_xpi = output_xpi.with_suffix(".xpi")

    result = {
        "input": str(ext_path),
        "output": str(output_xpi),
        "status": "success",
        "files_included": 0,
        "size_bytes": 0,
        "sha256": "",
        "errors": [],
    }

    # Create .xpi (which is just a .zip)
    try:
        with zipfile.ZipFile(output_xpi, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in ext_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(ext_path)
                    zf.write(file_path, arcname)
                    result["files_included"] += 1
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(f"Failed to create .xpi: {e}")
        return result

    # Get file size
    result["size_bytes"] = output_xpi.stat().st_size

    # Calculate SHA256
    sha256_hash = hashlib.sha256()
    with open(output_xpi, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    result["sha256"] = sha256_hash.hexdigest()

    return result

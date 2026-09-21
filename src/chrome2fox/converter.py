"""Converter — Pipeline to convert Chrome extension to Firefox."""

import json
import shutil
from pathlib import Path
from typing import Any

from .analyzer import analyze_extension
from .manifest_transform import transform_manifest
from .patcher import patch_js
from .shims import generate_shims_content, get_required_shims


def convert_extension(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Convert a Chrome extension to Firefox format.

    Args:
        input_path: Path to Chrome extension directory
        output_path: Path to output Firefox extension directory

    Returns:
        Conversion report
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    report = {
        "input": str(input_path),
        "output": str(output_path),
        "status": "success",
        "manifest_version": 0,
        "files_processed": 0,
        "js_files_patched": 0,
        "total_changes": 0,
        "changes": [],
        "warnings": [],
        "errors": [],
    }

    # Step 1: Analyze the extension
    analysis = analyze_extension(input_path)
    if "error" in analysis:
        report["status"] = "error"
        report["errors"].append(analysis["error"])
        return report

    report["manifest_version"] = analysis["manifest_version"]
    report["analysis"] = {
        "compatibility_score": analysis["compatibility_score"],
        "chrome_only_apis": analysis["chrome_only_apis"],
        "compatible_apis": analysis["compatible_apis"],
    }

    # Step 2: Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Step 3: Transform manifest
    manifest_path = input_path / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        chrome_manifest = json.load(f)

    try:
        firefox_manifest = transform_manifest(chrome_manifest)
    except Exception as e:
        report["status"] = "error"
        report["errors"].append(f"Manifest transform failed: {e}")
        return report

    # Write transformed manifest
    manifest_output = output_path / "manifest.json"
    with open(manifest_output, "w", encoding="utf-8") as f:
        json.dump(firefox_manifest, f, indent=2, ensure_ascii=False)

    report["files_processed"] += 1

    # Step 4: Patch JS files
    js_files = list(input_path.rglob("*.js"))
    for js_file in js_files:
        relative_path = js_file.relative_to(input_path)
        output_file = output_path / relative_path
        output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            content = js_file.read_text(encoding="utf-8")
            patched, changes = patch_js(content)

            output_file.write_text(patched, encoding="utf-8")
            report["files_processed"] += 1
            report["js_files_patched"] += 1
            report["total_changes"] += len(changes)
            report["changes"].extend(changes)
        except Exception as e:
            report["warnings"].append(f"Could not patch {relative_path}: {e}")
            # Copy original file
            shutil.copy2(js_file, output_file)
            report["files_processed"] += 1

    # Step 5: Copy non-JS files (icons, HTML, CSS, etc.)
    for file_path in input_path.rglob("*"):
        if file_path.is_file() and file_path.suffix != ".js" and file_path.name != "manifest.json":
            relative_path = file_path.relative_to(input_path)
            output_file = output_path / relative_path
            output_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, output_file)
            report["files_processed"] += 1

    # Step 6: Inject shims for Chrome-only APIs
    chrome_only_apis = analysis.get("chrome_only_apis", [])
    if chrome_only_apis:
        shim_content = generate_shims_content(chrome_only_apis)
        if shim_content:
            shim_path = output_path / "chrome2fox_shims.js"
            shim_path.write_text(shim_content, encoding="utf-8")
            report["files_processed"] += 1
            report["shims_injected"] = len(get_required_shims(chrome_only_apis))
            report["warnings"].append(f"Injected {report['shims_injected']} polyfill shims for Chrome-only APIs")
            
            # Inject shims into manifest content_scripts
            _inject_shims_into_manifest(firefox_manifest, shim_path.name)
            
            # Re-write manifest with shims injected
            with open(manifest_output, "w", encoding="utf-8") as f:
                json.dump(firefox_manifest, f, indent=2, ensure_ascii=False)

    return report


def _inject_shims_into_manifest(manifest: dict, shim_filename: str) -> None:
    """Inject shims script into manifest's content_scripts.
    
    This ensures the polyfill shims are loaded before any other scripts.
    
    Args:
        manifest: The manifest dictionary to modify
        shim_filename: Name of the shims file (e.g., 'chrome2fox_shims.js')
    """
    # Ensure content_scripts exists
    if "content_scripts" not in manifest:
        manifest["content_scripts"] = []
    
    # Find existing content_scripts entry that matches all URLs or inject new one
    all_urls_entry = None
    for entry in manifest["content_scripts"]:
        if "<all_urls>" in entry.get("matches", []):
            all_urls_entry = entry
            break
    
    if all_urls_entry:
        # Add shims to existing entry
        js_files = all_urls_entry.get("js", [])
        if shim_filename not in js_files:
            # Prepend shims so they load first
            all_urls_entry["js"] = [shim_filename] + js_files
    else:
        # Create new content_scripts entry for shims
        manifest["content_scripts"].insert(0, {
            "matches": ["<all_urls>"],
            "js": [shim_filename],
            "run_at": "document_start",
            "all_frames": True
        })

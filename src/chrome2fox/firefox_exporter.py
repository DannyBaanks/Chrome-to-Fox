"""
Firefox Exporter — Batch convert Chrome extensions to Firefox.

Provides a streamlined workflow for converting multiple
Chrome extensions to Firefox format.
"""

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .chrome_scanner import ChromeExtension
from .converter import convert_extension
from .analyzer import analyze_extension


@dataclass
class ExportResult:
    """Result of exporting a single extension."""
    extension_id: str
    extension_name: str
    status: str  # success, partial, failed
    output_path: Path
    compatibility_score: float
    files_processed: int = 0
    js_files_patched: int = 0
    total_changes: int = 0
    shims_injected: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class BatchExportResult:
    """Result of batch exporting multiple extensions."""
    total_extensions: int
    successful: int
    partial: int
    failed: int
    results: list[ExportResult] = field(default_factory=list)
    total_duration_ms: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_extensions == 0:
            return 0.0
        return self.successful / self.total_extensions


class FirefoxExporter:
    """
    Batch convert Chrome extensions to Firefox.
    
    Provides a streamlined workflow for:
    1. Selecting extensions to convert
    2. Converting each extension
    3. Generating a summary report
    
    Usage:
        exporter = FirefoxExporter()
        
        # Export single extension
        result = exporter.export_extension(chrome_ext)
        
        # Export multiple extensions
        batch_result = exporter.export_batch(extensions)
    """
    
    def __init__(
        self,
        output_dir: Path,
        auto_shim: bool = True,
        overwrite: bool = False
    ):
        """
        Initialize exporter.
        
        Args:
            output_dir: Base output directory
            auto_shim: Automatically inject shims
            overwrite: Overwrite existing conversions
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.auto_shim = auto_shim
        self.overwrite = overwrite
        
        # Subdirectories
        self.extensions_dir = self.output_dir / "extensions"
        self.extensions_dir.mkdir(exist_ok=True)
        
        self.reports_dir = self.output_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        self.xpi_dir = self.output_dir / "xpi"
        self.xpi_dir.mkdir(exist_ok=True)
    
    def export_extension(
        self,
        extension: ChromeExtension,
        package_xpi: bool = False
    ) -> ExportResult:
        """
        Export a single Chrome extension to Firefox.
        
        Args:
            extension: ChromeExtension to convert
            package_xpi: Also create .xpi package
            
        Returns:
            ExportResult with conversion details
        """
        start_time = time.time()
        
        # Create output directory for this extension
        ext_dir = self.extensions_dir / extension.id
        ext_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if already converted
        if not self.overwrite and (ext_dir / "manifest.json").exists():
            return ExportResult(
                extension_id=extension.id,
                extension_name=extension.name,
                status="skipped",
                output_path=ext_dir,
                compatibility_score=0.0,
                warnings=["Extension already converted, use --overwrite to reconvert"]
            )
        
        try:
            # Convert extension
            report = convert_extension(extension.path, ext_dir)
            
            # Extract metrics
            errors = report.get("errors", [])
            warnings = report.get("warnings", [])
            
            # Calculate compatibility score
            analysis = analyze_extension(extension.path)
            compatibility_score = analysis.get("compatibility_score", 0.0)
            
            # Package XPI if requested
            if package_xpi and not errors:
                try:
                    from .package import package_extension
                    xpi_path = self.xpi_dir / f"{extension.id}.xpi"
                    package_extension(ext_dir, xpi_path)
                except Exception as e:
                    warnings.append(f"XPI packaging failed: {e}")
            
            # Determine status
            if errors:
                status = "failed"
            elif warnings:
                status = "partial"
            else:
                status = "success"
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return ExportResult(
                extension_id=extension.id,
                extension_name=extension.name,
                status=status,
                output_path=ext_dir,
                compatibility_score=compatibility_score,
                files_processed=report.get("files_processed", 0),
                js_files_patched=report.get("js_files_patched", 0),
                total_changes=report.get("total_changes", 0),
                shims_injected=report.get("shims_injected", 0),
                errors=errors,
                warnings=warnings,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            return ExportResult(
                extension_id=extension.id,
                extension_name=extension.name,
                status="failed",
                output_path=ext_dir,
                compatibility_score=0.0,
                errors=[str(e)],
                duration_ms=duration_ms
            )
    
    def export_batch(
        self,
        extensions: list[ChromeExtension],
        package_xpi: bool = False,
        progress_callback: Any = None
    ) -> BatchExportResult:
        """
        Export multiple Chrome extensions to Firefox.
        
        Args:
            extensions: List of ChromeExtension objects
            package_xpi: Also create .xpi packages
            progress_callback: Callback for progress updates
            
        Returns:
            BatchExportResult with all results
        """
        start_time = time.time()
        
        results = []
        successful = 0
        partial = 0
        failed = 0
        
        for i, ext in enumerate(extensions):
            # Report progress
            if progress_callback:
                progress_callback(i + 1, len(extensions), ext.name)
            
            # Export extension
            result = self.export_extension(ext, package_xpi)
            results.append(result)
            
            # Count by status
            if result.status == "success":
                successful += 1
            elif result.status == "partial":
                partial += 1
            elif result.status == "failed":
                failed += 1
        
        total_duration_ms = int((time.time() - start_time) * 1000)
        
        # Generate summary report
        batch_result = BatchExportResult(
            total_extensions=len(extensions),
            successful=successful,
            partial=partial,
            failed=failed,
            results=results,
            total_duration_ms=total_duration_ms
        )
        
        # Save report
        self._save_batch_report(batch_result)
        
        return batch_result
    
    def _save_batch_report(self, result: BatchExportResult) -> None:
        """Save batch export report."""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": result.total_extensions,
                "successful": result.successful,
                "partial": result.partial,
                "failed": result.failed,
                "success_rate": f"{result.success_rate:.1%}",
                "duration_ms": result.total_duration_ms
            },
            "extensions": [
                {
                    "id": r.extension_id,
                    "name": r.extension_name,
                    "status": r.status,
                    "compatibility_score": r.compatibility_score,
                    "files_processed": r.files_processed,
                    "js_files_patched": r.js_files_patched,
                    "shims_injected": r.shims_injected,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "duration_ms": r.duration_ms
                }
                for r in result.results
            ]
        }
        
        report_path = self.reports_dir / "batch_export.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def get_extension_path(self, extension_id: str) -> Path | None:
        """Get the output path for a converted extension."""
        ext_path = self.extensions_dir / extension_id
        if ext_path.exists():
            return ext_path
        return None
    
    def list_converted(self) -> list[dict[str, Any]]:
        """List all converted extensions."""
        converted = []
        
        for ext_dir in self.extensions_dir.iterdir():
            if not ext_dir.is_dir():
                continue
            
            manifest_path = ext_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        manifest = json.load(f)
                    
                    converted.append({
                        "id": ext_dir.name,
                        "name": manifest.get("name", "Unknown"),
                        "version": manifest.get("version", "0.0.0"),
                        "path": str(ext_dir)
                    })
                except Exception:
                    pass
        
        return converted


def export_single_extension(
    extension_path: Path,
    output_dir: Path,
    package_xpi: bool = False
) -> ExportResult:
    """
    Convenience function to export a single extension.
    
    Args:
        extension_path: Path to Chrome extension directory
        output_dir: Output directory
        package_xpi: Also create .xpi package
        
    Returns:
        ExportResult
    """
    # Create a temporary ChromeExtension object
    manifest_path = extension_path / "manifest.json"
    if not manifest_path.exists():
        return ExportResult(
            extension_id="unknown",
            extension_name="Unknown",
            status="failed",
            output_path=output_dir,
            compatibility_score=0.0,
            errors=["No manifest.json found"]
        )
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    ext = ChromeExtension(
        id=extension_path.name,
        name=manifest.get("name", "Unknown"),
        version=manifest.get("version", "0.0.0"),
        description=manifest.get("description", ""),
        manifest_version=manifest.get("manifest_version", 2),
        permissions=manifest.get("permissions", []),
        path=extension_path
    )
    
    exporter = FirefoxExporter(output_dir)
    return exporter.export_extension(ext, package_xpi)


def export_from_chrome(
    output_dir: Path,
    extension_ids: list[str] | None = None,
    package_xpi: bool = False
) -> BatchExportResult:
    """
    Export extensions directly from Chrome installation.
    
    Args:
        output_dir: Output directory
        extension_ids: Specific extension IDs to export (None = all)
        package_xpi: Also create .xpi packages
        
    Returns:
        BatchExportResult
    """
    from .chrome_scanner import ChromeScanner
    
    # Scan Chrome extensions
    scanner = ChromeScanner()
    extensions = scanner.scan()
    
    # Filter by IDs if specified
    if extension_ids:
        extensions = [e for e in extensions if e.id in extension_ids]
    
    # Export
    exporter = FirefoxExporter(output_dir)
    return exporter.export_batch(extensions, package_xpi)


if __name__ == "__main__":
    print("Firefox Exporter")
    print("=" * 60)
    print("Batch convert Chrome extensions to Firefox")
    print("\nUsage:")
    print("  from chrome2fox.firefox_exporter import FirefoxExporter")
    print("  exporter = FirefoxExporter('./output')")
    print("  result = exporter.export_batch(extensions)")

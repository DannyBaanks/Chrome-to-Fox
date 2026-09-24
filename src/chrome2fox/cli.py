"""Chrome-to-Fox CLI — Convert Chrome extensions to Firefox format."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__


def cmd_analyze(args):
    """Analyze a Chrome extension for Firefox compatibility."""
    from .analyzer import analyze_extension
    report = analyze_extension(Path(args.input))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("errors") else 1


def cmd_convert(args):
    """Convert a Chrome extension to Firefox format."""
    from .converter import convert_extension
    report = convert_extension(Path(args.input), Path(args.output))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not report.get("errors") else 1


def cmd_validate(args):
    """Validate a converted Firefox extension."""
    from .validator import validate_extension
    result = validate_extension(Path(args.input))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("valid") else 1


def cmd_package(args):
    """Package a Firefox extension as .xpi."""
    from .package import package_extension
    xpi_path = package_extension(Path(args.input), Path(args.output))
    print(f"Created: {xpi_path}")
    return 0


def cmd_sign(args):
    """Sign a Firefox extension via AMO (web-ext sign)."""
    from .signer import sign_extension, wait_signed
    result = sign_extension(
        Path(args.input),
        api_key=args.api_key,
        api_secret=args.api_secret,
        channel=args.channel,
        artifacts_dir=Path(args.output) if args.output else None,
        timeout_seconds=args.timeout,
    )
    # Redacted by construction: signer never returns the secret.
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("status") != "success" or not args.wait_download:
        return 0 if result.get("status") == "success" else 1
    import json as _json

    def _guid():
        try:
            with open(Path(args.input) / "manifest.json", encoding="utf-8") as f:
                m = _json.load(f)
            return m.get("browser_specific_settings", {}).get("gecko", {}).get("id", "")
        except Exception:
            return ""
    guid = args.guid or _guid()
    version = args.version or _json.load(open(Path(args.input) / "manifest.json", encoding="utf-8")).get("version", "")
    waited = wait_signed(guid, version, api_key=args.api_key, api_secret=args.api_secret,
                         artifacts_dir=Path(args.output) if args.output else None,
                         poll_seconds=args.poll, max_waits=args.max_waits)
    print(json.dumps(waited, indent=2, ensure_ascii=False))
    return 0 if waited.get("status") == "success" else 1


def cmd_status(args):
    """Show AMO review status (awaiting with link / approved)."""
    from .signer import get_status
    target = args.input
    version = args.version
    # Acepta un directorio de extension: lee guid+version del manifest.
    maybe_manifest = Path(target) / "manifest.json"
    if maybe_manifest.exists():
        try:
            with open(maybe_manifest, encoding="utf-8") as f:
                m = json.load(f)
            g = m.get("browser_specific_settings", {}).get("gecko", {}).get("id", "")
            if g:
                target = g
            if not version:
                version = m.get("version")
        except Exception:
            pass
    result = get_status(target, version, api_key=args.api_key,
                        api_secret=args.api_secret)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("overall") == "approved" else 1


def cmd_my_addons(args):
    """Tus envios a AMO (registro + estado vivo) y tus listed."""
    from .signer import my_addons
    result = my_addons(api_key=args.api_key, api_secret=args.api_secret,
                       refresh=not args.no_refresh)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_search(args):
    """Busca addons publicos en AMO (sin credenciales)."""
    from .signer import search_addons
    result = search_addons(args.query, page_size=args.limit)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not result.get("errors") else 1


def cmd_repair(args):
    """Convert and repair a Chrome extension with LLM-powered fixes."""
    from .converter import convert_extension
    from .repair_engine import RepairEngine
    from .llm_client import LLMConfig
    from .test_harness import test_extension
    
    print(f"\n{'='*60}")
    print(f"Chrome-to-Fox Repair")
    print(f"{'='*60}\n")
    
    # Step 1: Convert
    print(f"[1/4] Converting extension...")
    report = convert_extension(Path(args.input), Path(args.output))
    
    if report.get("errors"):
        print(f"❌ Conversion failed: {report['errors']}")
        return 1
    
    print(f"✅ Converted: {report['files_processed']} files, {report['js_files_patched']} JS patched")
    
    # Step 2: Test
    print(f"\n[2/4] Testing in Firefox...")
    test_result = test_extension(Path(args.output), Path(args.input).name)
    
    if test_result.overall_status == "pass":
        print(f"✅ All tests pass!")
        
        if args.package_output:
            from .package import package_extension
            xpi_path = package_extension(Path(args.output), Path(args.package_output))
            print(f"\n📦 Created: {xpi_path}")
        
        return 0
    
    print(f"❌ Tests failed: {test_result.overall_status}")
    print(f"   Probes: {len(test_result.probes)} total")
    print(f"   Errors: {len(test_result.runtime_errors)} runtime")
    print(f"   Permissions: {len(test_result.permission_errors)}")
    
    # Step 3: Repair with LLM
    print(f"\n[3/4] Repairing with LLM...")
    
    if not args.llm_base_url:
        print(f"⚠️  No LLM configured. Use --llm-base-url to enable repair.")
        print(f"   Example: --llm-base-url https://integrate.api.nvidia.com/v1")
        return 1
    
    # Create LLM config
    llm_config = LLMConfig(
        base_url=args.llm_base_url,
        api_key=args.api_key or "",
        model=args.model or "meta/llama-3.1-70b-instruct"
    )
    
    # Create repair engine
    engine = RepairEngine(
        llm_config=llm_config,
        firefox_binary=args.firefox_binary
    )
    
    # Run repair
    receipt = engine.repair(
        extension_path=Path(args.output),
        max_attempts=args.max_attempts,
        verbose=True
    )
    
    # Step 4: Final result
    print(f"\n[4/4] Final Result")
    print(f"{'='*60}")
    print(f"Verdict: {receipt.verdict}")
    print(f"Attempts: {len(receipt.attempts)}")
    print(f"Duration: {receipt.total_duration_ms}ms")
    
    # Save receipt
    receipt_path = Path(args.output) / "repair_receipt.json"
    with open(receipt_path, "w", encoding="utf-8") as f:
        f.write(receipt.to_json())
    print(f"\n📄 Receipt: {receipt_path}")
    
    # Package if requested and successful
    if args.package_output and receipt.verdict in ("PASS", "DEGRADED"):
        from .package import package_extension
        xpi_path = package_extension(Path(args.output), Path(args.package_output))
        print(f"📦 Created: {xpi_path}")
    
    return 0 if receipt.verdict == "PASS" else 1


def cmd_corpus(args):
    """Build extension corpus."""
    from .corpus_builder import CorpusBuilder
    
    print(f"\n{'='*60}")
    print(f"Chrome-to-Fox Corpus Builder")
    print(f"{'='*60}\n")
    
    builder = CorpusBuilder(Path(args.output))
    
    # Add extensions
    source = args.source_url or "local"
    count = builder.add_extensions(Path(args.input), source)
    
    print(f"Added {count} extensions to corpus")
    
    # Get stats
    stats = builder.get_stats()
    
    print(f"\n{'='*60}")
    print(f"Corpus Statistics")
    print(f"{'='*60}")
    print(f"Total Extensions: {stats['total_extensions']}")
    print(f"Average Compatibility: {stats['average_compatibility']:.1f}%")
    print(f"Source Counts: {stats['source_counts']}")
    
    return 0


def cmd_patterns(args):
    """Detect repair patterns."""
    from .pattern_detector import PatternDetector
    
    print(f"\n{'='*60}")
    print(f"Chrome-to-Fox Pattern Detector")
    print(f"{'='*60}\n")
    
    detector = PatternDetector(Path(args.input))
    count = detector.load_corpus()
    
    print(f"Loaded {count} repair receipts")
    
    # Get stats
    stats = detector.get_stats()
    
    print(f"\n{'='*60}")
    print(f"Pattern Statistics")
    print(f"{'='*60}")
    print(f"Total repairs: {stats.total_repairs}")
    print(f"Successful repairs: {stats.successful_repairs}")
    print(f"Patterns detected: {stats.patterns_detected}")
    print(f"Rules generated: {stats.rules_generated}")
    
    # Get suggested rules
    rules = detector.get_suggested_rules(min_confidence=args.min_confidence)
    
    if rules:
        print(f"\nSuggested Rules (confidence >= {args.min_confidence}):")
        for rule in rules:
            print(f"  {rule.chrome_api} -> {rule.firefox_equivalent}")
            print(f"    Evidence: {rule.evidence_count}, Confidence: {rule.confidence:.2f}")
    
    # Export rules if output specified
    if args.output:
        count = detector.export_rules(Path(args.output))
        print(f"\nExported {count} rules to: {args.output}")
    
    return 0


def cmd_scan(args):
    """Scan installed Chrome extensions."""
    from .chrome_scanner import ChromeScanner
    
    print(f"\n{'='*60}")
    print(f"Chrome Extension Scanner")
    print(f"{'='*60}\n")
    
    # Add custom paths if specified
    custom_paths = []
    if args.chrome_path:
        custom_paths.append(Path(args.chrome_path))
    
    scanner = ChromeScanner(custom_paths)
    extensions = scanner.scan(include_disabled=args.include_disabled)
    
    print(f"Found {len(extensions)} extensions\n")
    
    # Display extensions
    for i, ext in enumerate(extensions[:args.limit], 1):
        print(f"{i:2d}. {ext.name[:40]:<40}")
        print(f"    ID: {ext.id}")
        print(f"    Version: {ext.version} | MV{ext.manifest_version}")
        if ext.permissions:
            print(f"    Permissions: {', '.join(ext.permissions[:3])}...")
        print()
    
    # Show stats
    stats = scanner.get_stats()
    
    print(f"{'='*60}")
    print(f"Statistics")
    print(f"{'='*60}")
    print(f"Total: {stats['total']}")
    print(f"Manifest V2: {stats['manifest_v2']}")
    print(f"Manifest V3: {stats['manifest_v3']}")
    
    if stats['top_permissions']:
        print(f"\nTop Permissions:")
        for perm, count in stats['top_permissions'][:5]:
            print(f"  {perm}: {count}")
    
    # Export if requested
    if args.output:
        count = scanner.export_list(Path(args.output))
        print(f"\nExported {count} extensions to: {args.output}")
    
    return 0


def cmd_bridge(args):
    """Bridge: Scan Chrome and export to Firefox."""
    from .chrome_scanner import ChromeScanner
    from .firefox_exporter import FirefoxExporter
    
    print(f"\n{'='*60}")
    print(f"Chrome-to-Fox Bridge")
    print(f"{'='*60}\n")
    
    # Step 1: Scan Chrome
    print(f"[1/3] Scanning Chrome extensions...")
    
    custom_paths = []
    if args.chrome_path:
        custom_paths.append(Path(args.chrome_path))
    
    scanner = ChromeScanner(custom_paths)
    extensions = scanner.scan()
    
    # Filter by IDs if specified
    if args.extensions:
        ext_ids = [id.strip() for id in args.extensions.split(",")]
        extensions = [e for e in extensions if e.id in ext_ids]
        print(f"  Filtered to {len(extensions)} extensions")
    
    print(f"  Found {len(extensions)} extensions to convert")
    
    if not extensions:
        print(f"\nNo extensions found to convert")
        return 0
    
    # Step 2: Export to Firefox
    print(f"\n[2/3] Converting to Firefox...")
    
    exporter = FirefoxExporter(
        output_dir=Path(args.output),
        auto_shim=True,
        overwrite=args.overwrite
    )
    
    def progress_callback(current, total, name):
        print(f"  [{current}/{total}] Converting: {name[:40]}")
    
    result = exporter.export_batch(
        extensions,
        package_xpi=args.package_xpi,
        progress_callback=progress_callback
    )
    
    # Step 3: Summary
    print(f"\n[3/3] Summary")
    print(f"{'='*60}")
    print(f"Total Extensions: {result.total_extensions}")
    print(f"Successful: {result.successful}")
    print(f"Partial: {result.partial}")
    print(f"Failed: {result.failed}")
    print(f"Success Rate: {result.success_rate:.1%}")
    print(f"Duration: {result.total_duration_ms/1000:.1f}s")
    
    # Show failed extensions
    failed = [r for r in result.results if r.status == "failed"]
    if failed:
        print(f"\nFailed Extensions:")
        for r in failed:
            print(f"  - {r.extension_name}: {', '.join(r.errors[:2])}")
    
    # Show output location
    print(f"\nOutput: {args.output}")
    print(f"  Extensions: {args.output}/extensions/")
    if args.package_xpi:
        print(f"  XPI Files: {args.output}/xpi/")
    print(f"  Report: {args.output}/reports/batch_export.json")
    
    return 0 if result.failed == 0 else 1


def cmd_up(args):
    """Flujo completo: analyze + convert + validate + package (+ sign si hay claves)."""
    import sys
    from argparse import Namespace
    from pathlib import Path as _P
    from .ui import log, dash

    src, out = _P(args.input), _P(args.output)
    log(f"flujo completo sobre {src}")
    from .analyzer import analyze_extension
    a = analyze_extension(src)
    if "error" in a:
        print(dash(False, "▚ CHROME2FOX UP", [("error", a["error"])]))
        return 1
    score = a.get("compatibility_score", "?")
    log(f"compatibilidad: {score}")

    import contextlib as _cl, io as _io
    conv = Namespace(input=str(src), output=str(out))
    with _cl.redirect_stdout(_io.StringIO()):
        rc = cmd_convert(conv)
    log("conversion OK (detalle con `convert` si lo quieres en JSON)")
    if rc != 0:
        print(dash(False, "▚ CHROME2FOX UP", [("fase", "convert")]))
        return 1
    from .validator import validate_extension
    v = validate_extension(out)
    log(f"validacion: {'OK' if v.get('valid') else 'FALLO'}")
    if not v.get("valid"):
        print(dash(False, "▚ CHROME2FOX UP", [("fase", "validate"), ("", "; ".join(v.get("errors", []))[:70])]))
        return 1
    from .package import package_extension
    xpi = out.parent / (out.name + ".xpi")
    pkg = package_extension(out, xpi)
    log(f"xpi: {xpi} ({pkg.get('size_bytes', 0)} bytes)")

    import os
    fila_firma = ("firma", "temporal (sin claves AMO: exporta AMO_API_KEY + AMO_API_SECRET)")
    review = ""
    if os.environ.get("AMO_API_KEY") or args.api_key:
        sargs = Namespace(input=str(out), output=str(out.parent / "signed"),
                          channel="unlisted", api_key=args.api_key,
                          api_secret=args.api_secret, timeout=args.timeout,
                          wait_download=False, guid=None, version=None,
                          poll=120, max_waits=15)
        if cmd_sign(sargs) == 0:
            fila_firma = ("firma", "enviada a AMO (unlisted): `chrome2fox status` para verla")
        else:
            fila_firma = ("firma", "AMO rechazo el envio (mira el JSON de arriba)")

    import json as _json
    m = _json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    print(dash(True, "▚ CHROME2FOX", [
        ("extension", f"{m.get('name')} {m.get('version')}"),
        ("compat", str(score)),
        ("archivos", str(pkg.get("files_included", "?"))),
        ("xpi", f"{xpi.name}  sha:{str(pkg.get('sha256', ''))[:12]}"),
        fila_firma,
        ("", "prueba: about:debugging -> Load Temporary Add-on -> manifest.json"),
    ]))
    return 0


def run_menu() -> int:
    """Menu interactivo sin args (solo TTY)."""
    from argparse import Namespace
    from .ui import menu
    opts = [
        ("up", "★ FLUJO COMPLETO sobre una extension", "input->output"),
        ("convert", "convierte Chrome -> Firefox", None),
        ("status", "estado AMO de un envio", None),
        ("my-addons", "tus envios + estado vivo", None),
        ("search", "addons publicos que ya existen", None),
    ]
    idx = menu([(n, d) for n, d, _ in opts])
    if idx is None:
        return 0
    name = opts[idx][0]
    if name == "up":
        src = input("carpeta de la extension Chrome: ").strip()
        out = input("carpeta de salida [./fox-out]: ").strip() or "./fox-out"
        return cmd_up(Namespace(input=src, output=out, api_key=None, api_secret=None, timeout=300))
    if name == "convert":
        src = input("carpeta de la extension Chrome: ").strip()
        out = input("carpeta de salida [./fox-out]: ").strip() or "./fox-out"
        return cmd_convert(Namespace(input=src, output=out))
    if name == "status":
        tgt = input("carpeta, guid o id de AMO: ").strip()
        return cmd_status(Namespace(input=tgt, version=None, api_key=None, api_secret=None))
    if name == "my-addons":
        return cmd_my_addons(Namespace(api_key=None, api_secret=None, no_refresh=False))
    if name == "search":
        q = input("buscar: ").strip()
        return cmd_search(Namespace(query=q, limit=10))
    return 0


def main():
    from .ui import HELP_EPILOG
    parser = argparse.ArgumentParser(
        prog="chrome2fox",
        description="▚ CHROME2FOX  port control (Chrome -> Firefox)",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze Chrome extension compatibility")
    p_analyze.add_argument("input", help="Path to Chrome extension (dir/zip/crx)")
    p_analyze.set_defaults(func=cmd_analyze)

    # convert
    p_convert = subparsers.add_parser("convert", help="Convert Chrome extension to Firefox")
    p_convert.add_argument("input", help="Path to Chrome extension")
    p_convert.add_argument("-o", "--output", required=True, help="Output directory")
    p_convert.set_defaults(func=cmd_convert)

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate Firefox extension")
    p_validate.add_argument("input", help="Path to Firefox extension directory")
    p_validate.set_defaults(func=cmd_validate)

    # package
    p_package = subparsers.add_parser("package", help="Package as .xpi")
    p_package.add_argument("input", help="Path to Firefox extension directory")
    p_package.add_argument("-o", "--output", required=True, help="Output .xpi path")
    p_package.set_defaults(func=cmd_package)

    # up (flujo completo estrella)
    p_up = subparsers.add_parser("up", help="★ FLUJO COMPLETO: analyze+convert+validate+package(+sign) y dashboard")
    p_up.add_argument("input", help="Carpeta de la extension Chrome")
    p_up.add_argument("-o", "--output", required=True, help="Carpeta de salida Firefox")
    p_up.add_argument("--api-key", help="AMO JWT issuer (or AMO_API_KEY env)")
    p_up.add_argument("--api-secret", help="AMO JWT secret (or AMO_API_SECRET env)")
    p_up.add_argument("--timeout", type=int, default=300, help="Segundos de espera a AMO (def. 300)")
    p_up.set_defaults(func=cmd_up)

    # sign
    p_sign = subparsers.add_parser("sign", help="Sign via AMO so Firefox installs it permanently")
    p_sign.add_argument("input", help="Path to Firefox extension directory")
    p_sign.add_argument("-o", "--output", help="Artifacts dir for the signed .xpi")
    p_sign.add_argument("--channel", default="unlisted", choices=["unlisted", "listed"],
                        help="AMO channel (default: unlisted)")
    p_sign.add_argument("--api-key", help="AMO JWT issuer (or AMO_API_KEY env)")
    p_sign.add_argument("--api-secret", help="AMO JWT secret (or AMO_API_SECRET env)")
    p_sign.add_argument("--timeout", type=int, default=300, help="Seconds to wait for AMO (default: 300)")
    p_sign.add_argument("--wait-download", action="store_true", help="Poll AMO until review finishes and download the signed .xpi")
    p_sign.add_argument("--guid", help="AMO guid (default: read from manifest gecko.id)")
    p_sign.add_argument("--version", help="Version to wait for (default: read from manifest)")
    p_sign.add_argument("--poll", type=int, default=120, help="Seconds between AMO polls (default: 120)")
    p_sign.add_argument("--max-waits", type=int, default=15, help="Max AMO polls (default: 15)")
    p_sign.set_defaults(func=cmd_sign)

    # status
    p_status = subparsers.add_parser("status", help="Show AMO review status for a signed submission")
    p_status.add_argument("input", help="Extension dir, AMO guid or numeric addon id")
    p_status.add_argument("--version", help="Version (default: from manifest, or all)")
    p_status.add_argument("--api-key", help="AMO JWT issuer (or AMO_API_KEY env)")
    p_status.add_argument("--api-secret", help="AMO JWT secret (or AMO_API_SECRET env)")
    p_status.set_defaults(func=cmd_status)

    # my-addons
    p_mine = subparsers.add_parser("my-addons", help="Tus envios a AMO con estado vivo")
    p_mine.add_argument("--api-key", help="AMO JWT issuer (or AMO_API_KEY env)")
    p_mine.add_argument("--api-secret", help="AMO JWT secret (or AMO_API_SECRET env)")
    p_mine.add_argument("--no-refresh", action="store_true", help="Solo registro local, sin preguntar a AMO")
    p_mine.set_defaults(func=cmd_my_addons)

    # search
    p_search = subparsers.add_parser("search", help="Busca addons publicos en AMO")
    p_search.add_argument("query", help="Texto a buscar")
    p_search.add_argument("--limit", type=int, default=10, help="Max resultados (default: 10)")
    p_search.set_defaults(func=cmd_search)

    # repair
    p_repair = subparsers.add_parser("repair", help="Convert and repair with LLM")
    p_repair.add_argument("input", help="Path to Chrome extension")
    p_repair.add_argument("-o", "--output", required=True, help="Output directory")
    p_repair.add_argument("--llm-base-url", help="LLM API endpoint (e.g., https://integrate.api.nvidia.com/v1)")
    p_repair.add_argument("--api-key", help="API key (or use NVIDIA_API_KEY env var)")
    p_repair.add_argument("--model", help="LLM model name (default: meta/llama-3.1-70b-instruct)")
    p_repair.add_argument("--max-attempts", type=int, default=3, help="Max repair attempts (default: 3)")
    p_repair.add_argument("--firefox-binary", help="Path to Firefox binary")
    p_repair.add_argument("--package-output", help="Package as .xpi if repair succeeds")
    p_repair.set_defaults(func=cmd_repair)

    # corpus
    p_corpus = subparsers.add_parser("corpus", help="Build extension corpus")
    p_corpus.add_argument("input", help="Directory containing Chrome extensions")
    p_corpus.add_argument("-o", "--output", required=True, help="Corpus output directory")
    p_corpus.add_argument("--source-url", help="Source URL for extensions")
    p_corpus.set_defaults(func=cmd_corpus)

    # patterns
    p_patterns = subparsers.add_parser("patterns", help="Detect repair patterns")
    p_patterns.add_argument("input", help="Corpus directory with repair receipts")
    p_patterns.add_argument("-o", "--output", help="Output file for rules")
    p_patterns.add_argument("--min-confidence", type=float, default=0.6, help="Minimum confidence (default: 0.6)")
    p_patterns.set_defaults(func=cmd_patterns)

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan installed Chrome extensions")
    p_scan.add_argument("--chrome-path", help="Custom Chrome extensions path")
    p_scan.add_argument("--include-disabled", action="store_true", help="Include disabled extensions")
    p_scan.add_argument("--limit", type=int, default=25, help="Max extensions to show (default: 25)")
    p_scan.add_argument("-o", "--output", help="Export list to JSON")
    p_scan.set_defaults(func=cmd_scan)

    # bridge
    p_bridge = subparsers.add_parser("bridge", help="Scan Chrome and export to Firefox")
    p_bridge.add_argument("-o", "--output", required=True, help="Output directory")
    p_bridge.add_argument("--chrome-path", help="Custom Chrome extensions path")
    p_bridge.add_argument("--extensions", help="Comma-separated extension IDs to convert")
    p_bridge.add_argument("--min-score", type=float, help="Minimum compatibility score")
    p_bridge.add_argument("--package-xpi", action="store_true", help="Create .xpi packages")
    p_bridge.add_argument("--overwrite", action="store_true", help="Overwrite existing conversions")
    p_bridge.set_defaults(func=cmd_bridge)

    args = parser.parse_args()
    if not args.command:
        import sys as _sys
        if _sys.stdin.isatty():
            return run_menu()
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

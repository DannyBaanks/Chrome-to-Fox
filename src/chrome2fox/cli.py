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


def main():
    parser = argparse.ArgumentParser(
        prog="chrome2fox",
        description="Chrome extension to Firefox extension converter",
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

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

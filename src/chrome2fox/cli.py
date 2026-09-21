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

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

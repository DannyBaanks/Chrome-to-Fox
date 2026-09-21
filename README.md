<div align="center">

# Chrome-to-Fox

### Chrome extensions, running in Firefox.

Convert, test, and repair Chromium extensions for Firefox — automatically.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22C55E?style=flat-square)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-F97316?style=flat-square)](CHANGELOG.md)

</div>

<p align="center">
  <img src="assets/chrome-to-fox-hero.png" alt="A fox carrying browser tabs across a bridge from Chrome to Firefox" width="100%" />
</p>

> Stop waiting for official Firefox ports. Chrome-to-Fox turns Chrome extensions into Firefox-ready packages, then tells you how well they actually work.

## The short version

Chrome-to-Fox is a developer tool for moving extensions across the Chromium → Firefox compatibility gap.

It does more than rename APIs:

1. **Analyze** the extension and score its compatibility.
2. **Convert** the manifest and JavaScript into Firefox-friendly code.
3. **Validate** the result and report remaining gaps.
4. **Repair** runtime failures with targeted, evidence-based patches.
5. **Package** the result as an installable `.xpi`.

```text
Chrome extension  →  Analyze  →  Convert  →  Test  →  Repair  →  Firefox .xpi
```

## A real conversion

The Claude Chrome extension has already been converted through the pipeline:

```text
Files processed       498
JavaScript files      369 patched
Compatibility score   83%
Shims injected        4
Result                warnings only — no errors
```

That score is not a guess. It comes from the APIs, manifest fields, and runtime failures Chrome-to-Fox can observe while working with the extension.

## Quick start

### Install

```bash
git clone https://github.com/DannyBaanks/Chrome-to-Fox.git
cd Chrome-to-Fox

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Convert one extension

```bash
# Inspect compatibility first
chrome2fox analyze /path/to/chrome-extension/

# Convert it to a Firefox-ready directory
chrome2fox convert /path/to/chrome-extension/ -o ./output/

# Validate and package it as an XPI
chrome2fox validate ./output/
chrome2fox package ./output/ -o extension.xpi
```

### Convert everything in your Chrome profile

```bash
chrome2fox bridge -o ./converted/ --package-xpi
```

Use `--extensions id1,id2,id3` when you only want selected extensions.

## What gets converted?

| Chrome | Firefox | How |
| --- | --- | --- |
| `chrome.tabs.query()` | `browser.tabs.query()` | API patch |
| `chrome.storage` | `browser.storage` | Native compatibility |
| `service_worker` | `background.scripts` | Manifest transform |
| `host_permissions` | `permissions` | Manifest transform |
| `action.default_popup` | `browser_action.default_popup` | Manifest transform |
| `chrome.sidePanel` | `browser.sidebarAction` | Shim / mapping |

When an API does not have a direct Firefox equivalent, Chrome-to-Fox can inject a focused shim and report exactly what happened.

### Native APIs

`tabs`, `storage`, `runtime`, `alarms`, `cookies`, `downloads`, `scripting`, and most common extension APIs are handled through direct compatibility mappings.

### APIs that need a bridge

The project includes bridges or fallbacks for `debugger`, `usb`, `serial`, `hid`, `tts`, `tabCapture`, `offscreen`, `tabGroups`, `declarativeContent`, and `sidePanel`.

Some of these are full bridges. Others are intentionally transparent fallbacks that preserve as much behavior as Firefox allows while leaving a useful warning in the output.

## Commands

| Command | Purpose |
| --- | --- |
| `chrome2fox scan` | Discover installed Chrome extensions |
| `chrome2fox analyze ./ext/` | Score API and manifest compatibility |
| `chrome2fox convert ./ext/ -o ./out/` | Convert an extension |
| `chrome2fox validate ./out/` | Check the Firefox package |
| `chrome2fox package ./out/ -o ext.xpi` | Create an installable XPI |
| `chrome2fox repair ./ext/ -o ./out/` | Convert, test, and repair failures |
| `chrome2fox bridge -o ./out/` | Scan and convert extensions in bulk |
| `chrome2fox corpus ./exts/ -o ./corpus/` | Build a conversion corpus |
| `chrome2fox patterns ./corpus/ -o rules.json` | Detect repeatable repair patterns |

Run `chrome2fox --help` for options and provider configuration.

## The repair loop

For extensions that need more than deterministic transforms, the repair engine can work with any OpenAI-compatible provider — hosted or local:

```text
1. Convert the extension
2. Run it in a disposable Firefox profile
3. Capture failures with their manifest and runtime context
4. Generate a targeted patch
5. Retest until the result passes or needs human review
```

Supported provider shapes include OpenAI, OpenRouter, NVIDIA, and local Ollama-compatible endpoints. The repair receipt records hashes, attempts, verdict, model, and duration so changes stay auditable.

## Project shape

```text
src/chrome2fox/
├── analyzer.py             # API detection and compatibility scoring
├── converter.py            # Conversion pipeline
├── manifest_transform.py   # Chrome manifest → Firefox manifest
├── patcher.py              # JavaScript API patching
├── validator.py            # Firefox package validation
├── test_harness.py         # Disposable Firefox testing
├── repair_engine.py        # Evidence-based repair loop
├── pattern_detector.py     # Turn repairs into deterministic rules
└── shims/                  # Compatibility bridges and fallbacks
```

For the full Spanish usage guide and implementation notes, see [GUIA.md](GUIA.md). Release history lives in [CHANGELOG.md](CHANGELOG.md).

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
python -m pytest tests/ --cov=chrome2fox
```

## Compatibility notes

Chrome-to-Fox is designed to make porting practical, not to pretend that every Chrome-only capability has a perfect Firefox equivalent. Review the analyzer output before shipping a converted extension, especially when it uses privileged hardware APIs, deep DevTools integration, or Chrome-specific UI surfaces.

Firefox and extension APIs evolve. If a conversion breaks, please [open an issue](https://github.com/DannyBaanks/Chrome-to-Fox/issues) with the analyzer output and the source extension's relevant manifest/API usage.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Add or update tests for the behavior you changed.
4. Open a pull request with the compatibility impact explained.

## License

MIT — see [LICENSE](LICENSE).

<div align="center">

Built for the Firefox extension ecosystem.

</div>

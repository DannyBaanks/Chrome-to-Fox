# Chrome-to-Fox 🔥🦊

Convert Chrome extensions to Firefox format automatically.

## Features

- **Manifest Transform**: Chrome MV2/MV3 → Firefox compatible
- **API Detection**: Scan JS for `chrome.*` APIs, identify Chrome-only ones
- **JS Patcher**: Replace `chrome.*` with `browser.*` selectively
- **Validator**: Check Firefox extension for submission readiness
- **Package**: Create `.xpi` files ready for AMO
- **Shims**: Polyfills for 10 Chrome-only APIs

## Installation

```bash
cd "/home/danny/Development/ISyCo Git/Chrome-to-Fox"
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### Analyze a Chrome extension

```bash
chrome2fox analyze /path/to/chrome-extension/
```

Output:
```json
{
  "manifest_version": 3,
  "name": "My Extension",
  "compatibility_score": 1.0,
  "used_apis": ["chrome.storage.local", "chrome.tabs.query"],
  "chrome_only_apis": [],
  "compatible_apis": ["chrome.storage.local", "chrome.tabs.query"],
  "manifest_issues": ["Missing browser_specific_settings.gecko.id"]
}
```

### Convert to Firefox

```bash
chrome2fox convert /path/to/chrome-extension/ -o /path/to/output/
```

Output:
```json
{
  "status": "success",
  "files_processed": 4,
  "js_files_patched": 2,
  "total_changes": 6,
  "changes": [
    {"line": 5, "old": "chrome.storage.local", "new": "browser.storage.local"}
  ],
  "shims_injected": 0
}
```

### Validate Firefox extension

```bash
chrome2fox validate /path/to/firefox-extension/
```

Output:
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Missing browser_specific_settings.gecko.id"],
  "checks": {"manifest_valid": true, "files_exist": true, "no_chrome_apis": true}
}
```

### Package as .xpi

```bash
chrome2fox package /path/to/firefox-extension/ -o extension.xpi
```

Output:
```
Created: extension.xpi (1330 bytes, SHA256: 9687a7b9...)
```

## Chrome API Compatibility

| API | Firefox Support | Polyfill | Notes |
|-----|-----------------|----------|-------|
| chrome.tabs | ✅ Full | No | |
| chrome.storage | ✅ Full | No | |
| chrome.runtime | ✅ Full | No | |
| chrome.alarms | ✅ Full | No | |
| chrome.cookies | ✅ Full | No | |
| chrome.offscreen | ⚠️ Partial | Yes | Mock with warnings |
| chrome.tabGroups | ⚠️ Partial | Yes | Storage-based simulation |
| chrome.declarativeContent | ⚠️ Partial | Yes | Rule storage only |
| chrome.sidePanel | ⚠️ Partial | Yes | Maps to sidebarAction |
| chrome.debugger | ❌ Incompatible | Yes | No-op with warnings |
| chrome.tabCapture | ❌ Incompatible | Yes | No-op with warnings |
| chrome.tts | ⚠️ Partial | Yes | Web Speech API fallback |
| chrome.usb | ❌ Incompatible | Yes | No-op with warnings |
| chrome.serial | ❌ Incompatible | Yes | No-op with warnings |
| chrome.hid | ❌ Incompatible | Yes | No-op with warnings |

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Install in development mode
pip install -e .
```

## Project Structure

```
Chrome-to-Fox/
├── src/chrome2fox/
│   ├── __init__.py          # Package init
│   ├── cli.py               # CLI interface
│   ├── analyzer.py          # API detection & compatibility scoring
│   ├── manifest_transform.py # Chrome → Firefox manifest conversion
│   ├── patcher.py           # JS chrome.* → browser.* replacement
│   ├── converter.py         # Full conversion pipeline
│   ├── validator.py         # Firefox extension validation
│   ├── package.py           # .xpi packaging
│   └── shims/               # Chrome-only API polyfills
│       ├── __init__.py      # Shim registry
│       ├── offscreen_polyfill.js
│       ├── tabgroups_polyfill.js
│       ├── declarativecontent_polyfill.js
│       ├── sidepanel_polyfill.js
│       ├── debugger_polyfill.js
│       ├── tabcapture_polyfill.js
│       ├── tts_polyfill.js
│       ├── usb_polyfill.js
│       ├── serial_polyfill.js
│       └── hid_polyfill.js
├── tests/                   # Unit tests (18 tests)
├── corpus/                  # Test extensions
├── evidence/                # Benchmarks & hashes
├── pyproject.toml
├── README.md
├── GUIA.md                  # Spanish guide
└── CHANGELOG.md
```

## License

MIT

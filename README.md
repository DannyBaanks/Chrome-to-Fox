# Chrome-to-Fox 🔥🦊

Convert Chrome extensions to Firefox format automatically.

## Features

- **Manifest Transform**: Chrome MV2/MV3 → Firefox compatible
- **API Detection**: Scan JS for `chrome.*` APIs, identify Chrome-only ones
- **JS Patcher**: Replace `chrome.*` with `browser.*` selectively
- **Validator**: Check Firefox extension for submission readiness
- **Package**: Create `.xpi` files ready for AMO

## Installation

```bash
cd "/home/danny/Development/ISyCo Git/Chrome-to-Fox"
pip install -e .
```

## Usage

### Analyze a Chrome extension

```bash
chrome2fox analyze /path/to/chrome-extension/
```

### Convert to Firefox

```bash
chrome2fox convert /path/to/chrome-extension/ -o /path/to/output/
```

### Validate Firefox extension

```bash
chrome2fox validate /path/to/firefox-extension/
```

### Package as .xpi

```bash
chrome2fox package /path/to/firefox-extension/ -o extension.xpi
```

## Chrome API Compatibility

| API | Firefox Support | Notes |
|-----|-----------------|-------|
| chrome.tabs | ✅ Full | |
| chrome.storage | ✅ Full | |
| chrome.runtime | ✅ Full | |
| chrome.alarms | ✅ Full | |
| chrome.cookies | ✅ Full | |
| chrome.offscreen | ⚠️ Partial | Polyfill available |
| chrome.tabGroups | ⚠️ Partial | Polyfill available |
| chrome.debugger | ❌ Incompatible | No Firefox equivalent |
| chrome.usb | ❌ Incompatible | No Firefox equivalent |

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Install in development mode
pip install -e .
```

## License

MIT

# Chrome-to-Fox 🔥🦊

Convert Chrome extensions to Firefox format automatically.

## Features

- **Manifest Transform**: Chrome MV2/MV3 → Firefox compatible
  - `service_worker` → `background.scripts`
  - `side_panel` → `sidebar_action`
  - `host_permissions` → `permissions`
- **API Detection**: Scan JS for `chrome.*` APIs, identify Chrome-only ones
- **JS Patcher**: Replace `chrome.*` with `browser.*` selectively (28+ API mappings)
- **Validator**: Check Firefox extension for submission readiness
- **Package**: Create `.xpi` files ready for AMO
- **Shims**: Polyfills for 10 Chrome-only APIs with automatic injection

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
  "compatibility_score": 0.67,
  "used_apis": ["chrome.debugger.attach", "chrome.storage.local"],
  "chrome_only_apis": ["chrome.debugger.attach"],
  "compatible_apis": ["chrome.storage.local"],
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
  "files_processed": 8,
  "js_files_patched": 4,
  "total_changes": 25,
  "changes": [
    {"line": 5, "old": "chrome.storage.local", "new": "browser.storage.local"}
  ],
  "shims_injected": 1,
  "warnings": ["Injected 1 polyfill shims for Chrome-only APIs"]
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
| chrome.action | ✅ Full | No | Maps to browser_action in MV2 |
| chrome.downloads | ✅ Full | No | |
| chrome.offscreen | ⚠️ Partial | Yes | Mock with warnings |
| chrome.tabGroups | ⚠️ Partial | Yes | Storage-based simulation |
| chrome.declarativeContent | ⚠️ Partial | Yes | Rule storage only |
| chrome.sidePanel | ⚠️ Partial | Yes | Maps to sidebarAction |
| chrome.debugger | ⚠️ Partial | Yes | **Full CDP bridge** (see below) |
| chrome.tabCapture | ⚠️ Partial | Yes | Firefox limited support |
| chrome.tts | ⚠️ Partial | Yes | Web Speech API fallback |
| chrome.usb | ⚠️ Partial | Yes | **Full WebUSB bridge** (see below) |
| chrome.serial | ⚠️ Partial | Yes | **Full Web Serial bridge** (see below) |
| chrome.hid | ⚠️ Partial | Yes | **Full WebHID bridge** (see below) |

## Debugger Polyfill — Full CDP Bridge

The `chrome.debugger` polyfill provides a **complete Chrome DevTools Protocol (CDP) bridge** to Firefox via `browser.scripting.executeScript`.

### Supported CDP Domains

| Domain | Commands | Status |
|--------|----------|--------|
| **DOM** | getDocument, getBoxModel, querySelector, querySelectorAll, getOuterHTML, setOuterHTML, getAttributes, setAttribute, removeAttribute, describeNode, getNodeForLocation | ✅ Full |
| **CSS** | getComputedStyleForNode, getMatchedStylesForNode, getInlineStylesForNode, getStyleSheetText | ✅ Full |
| **Runtime** | evaluate, getProperties, callFunctionOn, releaseObject | ✅ Full |
| **Page** | getLayoutMetrics, navigate, reload, captureScreenshot | ✅ Full |
| **Network** | getResponseBody, getRequestPostData | ⚠️ Partial |
| **Emulation** | setDeviceMetricsOverride, clearDeviceMetricsOverride, setUserAgentOverride, setTouchEmulationEnabled | ✅ Full |
| **Debugger** | enable, disable, stepOver, stepInto, stepOut, resume, pause, setBreakpoint, removeBreakpoint, setPauseOnExceptions | ✅ Full |

### API Methods

| Method | Description |
|--------|-------------|
| `attach(target, version)` | Attach debugger to tab |
| `detach(target)` | Detach debugger |
| `sendCommand(target, method, params)` | Send CDP command |
| `getTargets()` | List debuggable targets |
| `onEvent` | Debugger events |
| `onDetach` | Detach events |

### Limitations

- **Real debugging** (pause/step) requires DevTools to be open
- **Network interception** limited (Firefox restriction)
- **Performance**: Each `sendCommand` executes in page context

## USB Polyfill — Full WebUSB Bridge

The `chrome.usb` polyfill provides a **complete WebUSB bridge** to Firefox via `navigator.usb`.

### Supported Methods

| Method | Description |
|--------|-------------|
| `getDevices(options)` | List USB devices |
| `openDevice(device)` | Open USB device |
| `closeDevice(handle)` | Close USB device |
| `claimInterface(handle, interfaceNumber)` | Claim USB interface |
| `releaseInterface(handle, interfaceNumber)` | Release USB interface |
| `controlTransfer(handle, transferInfo)` | Control transfer |
| `bulkTransfer(handle, transferInfo)` | Bulk transfer |
| `interruptTransfer(handle, transferInfo)` | Interrupt transfer |
| `isochronousTransfer(handle, transferInfo)` | Isochronous transfer |
| `resetDevice(handle)` | Reset USB device |

### Events

| Event | Description |
|-------|-------------|
| `onConnect` | Device connected |
| `onDisconnect` | Device disconnected |

## Serial Polyfill — Full Web Serial Bridge

The `chrome.serial` polyfill provides a **complete Web Serial bridge** to Firefox via `navigator.serial`.

### Supported Methods

| Method | Description |
|--------|-------------|
| `getDevices()` | List serial ports |
| `connect(path, options, callback)` | Connect to serial port |
| `disconnect(connectionId, callback)` | Disconnect from serial port |
| `send(connectionId, data, callback)` | Send data |
| `getInfo()` | Get connection info |
| `update(connectionId, options, callback)` | Update connection options |
| `getControlSignals(connectionId)` | Get control signals |
| `setControlSignals(connectionId, signals)` | Set control signals |
| `flush(connectionId, callback)` | Flush serial port |

### Events

| Event | Description |
|-------|-------------|
| `onReceive` | Data received |
| `onReceiveError` | Receive error |
| `onConnect` | Port connected |
| `onDisconnect` | Port disconnected |

## HID Polyfill — Full WebHID Bridge

The `chrome.hid` polyfill provides a **complete WebHID bridge** to Firefox via `navigator.hid`.

### Supported Methods

| Method | Description |
|--------|-------------|
| `getDevices(options)` | List HID devices |
| `connect(vendorId, productId)` | Connect to HID device |
| `disconnect(connectionId)` | Disconnect from HID device |
| `send(connectionId, reportId, data)` | Send HID report |
| `receive(connectionId)` | Receive HID report |
| `sendFeatureReport(connectionId, reportId, data)` | Send feature report |
| `receiveFeatureReport(connectionId, reportId)` | Receive feature report |

### Events

| Event | Description |
|-------|-------------|
| `onConnect` | Device connected |
| `onDisconnect` | Device disconnected |

## TTS Polyfill — Full Web Speech Bridge

The `chrome.tts` polyfill provides a **complete Web Speech API bridge** to Firefox.

### Supported Methods

| Method | Description |
|--------|-------------|
| `speak(text, options, callback)` | Speak text with options |
| `stop()` | Stop speaking |
| `pause()` | Pause speaking |
| `resume()` | Resume speaking |
| `isSpeaking(callback)` | Check if speaking |
| `getVoices(callback)` | Get available voices |
| `getStream(streamId)` | Get captured stream (extension) |
| `stopCapture(streamId)` | Stop capture (extension) |

### Options

| Option | Description |
|--------|-------------|
| `rate` | Speech rate (0.1 to 10, default 1) |
| `pitch` | Speech pitch (0 to 2, default 1) |
| `volume` | Speech volume (0 to 1, default 1) |
| `lang` | Language code (e.g., 'en-US') |
| `voiceName` | Voice name to use |

### Events

| Event | Description |
|-------|-------------|
| `onPause` | Speech paused |
| `onResume` | Speech resumed |
| `onStart` | Speech started |
| `onEnd` | Speech ended |
| `onError` | Speech error |
| `onVoiceUpdate` | Voices loaded |

## TabCapture Polyfill — Firefox Tab Capture Bridge

The `chrome.tabCapture` polyfill provides **tab capture functionality** via Firefox's `browser.tabCapture` or `getUserMedia` fallback.

### Supported Methods

| Method | Description |
|--------|-------------|
| `capture(options, callback)` | Capture tab content |
| `getCapturedTabs()` | Get list of captured tabs |
| `getStream(streamId)` | Get stream by ID (extension) |
| `stopCapture(streamId)` | Stop capture (extension) |

### Capture Options

| Option | Description |
|--------|-------------|
| `audio` | Capture audio (default true) |
| `video` | Capture video (default true) |
| `videoConstraints` | Video constraints |

### Events

| Event | Description |
|-------|-------------|
| `onStatusChanged` | Capture status changed |

### Usage Example

```javascript
// Capture tab
chrome.tabCapture.capture({ audio: true, video: true }, (streamId) => {
  if (streamId) {
    // Get the stream
    const stream = chrome.tabCapture.getStream(streamId);
    
    // Use with video element
    const video = document.createElement('video');
    video.srcObject = stream;
    video.play();
    
    // Stop later
    chrome.tabCapture.stopCapture(streamId);
  }
});
```

## Manifest Transform Details

### MV3 Transformations

| Chrome | Firefox |
|--------|---------|
| `background.service_worker` | `background.scripts` |
| `side_panel.default_path` | `sidebar_action.default_panel` |
| `host_permissions` | Merged into `permissions` |

### Automatic Injects

- `browser_specific_settings.gecko.id` (if missing)
- `chrome2fox_shims.js` in `content_scripts` (if Chrome-only APIs detected)

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Install in development mode
pip install -e .

# Convert test extension
chrome2fox convert corpus/html-to-design/ -o output/html-to-design/
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
│       ├── __init__.py      # Shim registry + injection
│       ├── offscreen_polyfill.js
│       ├── tabgroups_polyfill.js
│       ├── declarativecontent_polyfill.js
│       ├── sidepanel_polyfill.js
│       ├── debugger_polyfill.js    # Full CDP bridge (~1100 lines)
│       ├── tabcapture_polyfill.js
│       ├── tts_polyfill.js
│       ├── usb_polyfill.js
│       ├── serial_polyfill.js
│       └── hid_polyfill.js
├── tests/                   # Unit tests (18 tests)
├── corpus/                  # Test extensions
├── output/                  # Converted extensions
├── evidence/                # Benchmarks & hashes
├── pyproject.toml
├── README.md
├── GUIA.md                  # Spanish guide
└── CHANGELOG.md
```

## Test Results

```
18 passed in 0.04s
```

## License

MIT

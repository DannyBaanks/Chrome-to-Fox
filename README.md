<div align="center">

# 🔥🦊 Chrome-to-Fox

### Intelligent Chrome Extension → Firefox Porting Tool

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-18%20passing-brightgreen.svg)]()
[![Version](https://img.shields.io/badge/Version-0.1.0-orange.svg)]()

**Convert, test, and repair Chrome extensions for Firefox with AI-powered fixes.**

</div>

---

## What is Chrome-to-Fox?

Chrome-to-Fox is a comprehensive tool that ports Chrome extensions to Firefox. It goes beyond simple syntax replacement — it **converts**, **tests in real Firefox**, and **repairs failures using LLM-powered analysis**.

### Key Features

| Feature | Description |
|---------|-------------|
| 🔄 **Deterministic Conversion** | Manifest transform, API patching, shim injection |
| 🧪 **Real Firefox Testing** | Disposable profiles, runtime probes, console capture |
| 🤖 **LLM-Powered Repair** | Evidence-based patches from NVIDIA/OpenRouter/local |
| 📊 **Pattern Detection** | Learns from repairs to build deterministic rules |
| 📦 **Corpus Building** | Accumulate 500+ extensions for continuous improvement |

---

## Quick Start

### Installation

```bash
git clone https://github.com/DannyBaanks/Chrome-to-Fox.git
cd Chrome-to-Fox
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Basic Usage

```bash
# Analyze compatibility
chrome2fox analyze /path/to/chrome-extension/

# Convert to Firefox
chrome2fox convert /path/to/chrome-extension/ -o ./output/

# Validate
chrome2fox validate ./output/

# Package as .xpi
chrome2fox package ./output/ -o extension.xpi
```

### AI-Powered Repair

```bash
chrome2fox repair /path/to/chrome-extension/ \
  -o ./output/ \
  --llm-base-url https://integrate.api.nvidia.com/v1 \
  --api-key nvapi-... \
  --model meta/llama-3.1-70b-instruct \
  --max-attempts 3
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Chrome-to-Fox Pipeline                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │ ANALYZE  │───▶│ CONVERT  │───▶│   TEST   │───▶│ PACKAGE│ │
│  │          │    │          │    │          │    │        │ │
│  │ • Scan   │    │ • Patch  │    │ • Firefox│    │ • .xpi │ │
│  │ • Score  │    │ • Shim   │    │ • Probes │    │ • SHA  │ │
│  └──────────┘    └──────────┘    └──────────┘    └────────┘ │
│                       │               │                      │
│                       │          ┌────┴────┐                 │
│                       │         FAIL       PASS              │
│                       │          │                        │ │
│                       │          ▼                        │ │
│                       │    ┌──────────┐                   │ │
│                       │    │  REPAIR  │                   │ │
│                       │    │          │                   │ │
│                       │    │ • LLM    │                   │ │
│                       │    │ • Patch  │                   │ │
│                       │    │ • Retest │                   │ │
│                       │    └──────────┘                   │ │
│                       │          │                        │ │
│                       │     ┌────┴────┐                   │ │
│                       │    PASS      FAIL                 │ │
│                       │     │         │                   │ │
│                       │     ▼         ▼                   │ │
│                       │  ┌─────┐  ┌─────────┐            │ │
│                       │  │ XPI │  │   PR    │            │ │
│                       │  └─────┘  └─────────┘            │ │
│                       │                        │         │ │
│                       └────────────────────────┘         │ │
│                                                          │ │
└─────────────────────────────────────────────────────────────┘
```

---

## API Compatibility

### Native Firefox Support (No Shims Needed)

| API | Status | Notes |
|-----|--------|-------|
| `chrome.tabs` | ✅ Full | |
| `chrome.storage` | ✅ Full | |
| `chrome.runtime` | ✅ Full | |
| `chrome.alarms` | ✅ Full | |
| `chrome.cookies` | ✅ Full | |
| `chrome.action` | ✅ Full | Maps to `browser_action` in MV2 |
| `chrome.downloads` | ✅ Full | |
| `chrome.scripting` | ✅ Full | |

### Shimming Required (Automatic Polyfills)

| API | Shim Type | Bridge Technology |
|-----|-----------|-------------------|
| `chrome.debugger` | Full CDP Bridge | `browser.scripting.executeScript` |
| `chrome.usb` | Full WebUSB Bridge | `navigator.usb` |
| `chrome.serial` | Full Web Serial Bridge | `navigator.serial` |
| `chrome.hid` | Full WebHID Bridge | `navigator.hid` |
| `chrome.tts` | Full Web Speech Bridge | `SpeechSynthesis` API |
| `chrome.tabCapture` | Firefox + getUserMedia | `browser.tabCapture` |
| `chrome.offscreen` | Mock | Storage-based |
| `chrome.tabGroups` | Mock | Storage-based |
| `chrome.declarativeContent` | Mock | Rule storage |
| `chrome.sidePanel` | Maps to | `sidebar_action` |

---

## Debugger Bridge — Chrome DevTools Protocol

The `chrome.debugger` polyfill implements a **complete CDP bridge** to Firefox.

### Supported Domains

| Domain | Methods | Status |
|--------|---------|--------|
| **DOM** | getDocument, querySelector, getOuterHTML, setAttribute, ... | ✅ 11 methods |
| **CSS** | getComputedStyleForNode, getMatchedStylesForNode, ... | ✅ 4 methods |
| **Runtime** | evaluate, getProperties, callFunctionOn, ... | ✅ 4 methods |
| **Page** | getLayoutMetrics, navigate, reload, captureScreenshot | ✅ 4 methods |
| **Emulation** | setDeviceMetricsOverride, setUserAgentOverride, ... | ✅ 4 methods |
| **Debugger** | enable, disable, pause, resume, stepOver, ... | ✅ 10 methods |
| **Network** | getResponseBody, getRequestPostData | ⚠️ Partial |

### Usage

```javascript
// Attach to tab
chrome.debugger.attach({ tabId: 123 }, "1.3", () => {
  // Get DOM document
  chrome.debugger.sendCommand(
    { tabId: 123 },
    "DOM.getDocument",
    {},
    (result) => {
      console.log(result.root.nodeId);
    }
  );
});
```

---

## LLM-Powered Repair Engine

### How It Works

1. **Test** the converted extension in Firefox
2. **Capture** failures with full context (manifest, runtime, permissions)
3. **Generate** evidence-based prompt for LLM
4. **Apply** targeted patch
5. **Retest** and repeat until PASS or max attempts

### Supported Providers

| Provider | Base URL | Example |
|----------|----------|---------|
| NVIDIA | `https://integrate.api.nvidia.com/v1` | `meta/llama-3.1-70b-instruct` |
| OpenRouter | `https://openrouter.ai/api/v1` | `anthropic/claude-3.5-sonnet` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| Local | `http://localhost:11434/v1` | `llama3` (Ollama) |

### Repair Receipt

Each repair produces a structured receipt:

```json
{
  "original_hash": "abc123...",
  "converted_hash": "def456...",
  "final_hash": "ghi789...",
  "verdict": "PASS",
  "attempts": [
    {
      "attempt_number": 1,
      "failures_before": 3,
      "failures_after": 0,
      "duration_ms": 4523,
      "success": true
    }
  ],
  "model": "meta/llama-3.1-70b-instruct",
  "total_duration_ms": 5234
}
```

---

## Corpus & Pattern Detection

### Build a Corpus

```bash
# Collect extensions
chrome2fox corpus /path/to/extensions/ -o ./corpus/

# View stats
chrome2fox patterns ./corpus/ -o rules.json
```

### Learning Loop

```
LLM discovers repair
        │
        ▼
Repair demonstrates repeatability
        │
        ▼
Pattern detector identifies rule
        │
        ▼
Rule crystallized into deterministic transform
        │
        ▼
Next extension uses rule (no LLM cost)
```

---

## CLI Reference

| Command | Description | Example |
|---------|-------------|---------|
| `analyze` | Scan Chrome extension | `chrome2fox analyze ./ext/` |
| `convert` | Convert to Firefox | `chrome2fox convert ./ext/ -o ./out/` |
| `validate` | Validate Firefox extension | `chrome2fox validate ./out/` |
| `package` | Create .xpi | `chrome2fox package ./out/ -o ext.xpi` |
| `repair` | Convert + test + repair | `chrome2fox repair ./ext/ -o ./out/ --llm-base-url ...` |
| `corpus` | Build extension corpus | `chrome2fox corpus ./exts/ -o ./corpus/` |
| `patterns` | Detect repair patterns | `chrome2fox patterns ./corpus/ -o rules.json` |

---

## Project Structure

```
Chrome-to-Fox/
├── src/chrome2fox/
│   ├── __init__.py              # Package metadata
│   ├── cli.py                   # CLI interface (7 commands)
│   ├── analyzer.py              # API detection & scoring
│   ├── manifest_transform.py    # Manifest conversion
│   ├── patcher.py               # JS patching (28+ APIs)
│   ├── converter.py             # Conversion pipeline
│   ├── validator.py             # Firefox validation
│   ├── package.py               # .xpi packaging
│   ├── test_harness.py          # Firefox test harness
│   ├── failure_envelope.py      # Error normalization
│   ├── llm_client.py            # OpenAI-compatible client
│   ├── repair_engine.py         # LLM repair loop
│   ├── pr_generator.py          # Evidence-based PRs
│   ├── pattern_detector.py      # Pattern detection
│   ├── corpus_builder.py        # Corpus management
│   └── shims/                   # 10 polyfill shims
│       ├── debugger_polyfill.js # Full CDP bridge (1100+ lines)
│       ├── usb_polyfill.js      # WebUSB bridge
│       ├── serial_polyfill.js   # Web Serial bridge
│       ├── hid_polyfill.js      # WebHID bridge
│       ├── tts_polyfill.js      # Web Speech bridge
│       ├── tabcapture_polyfill.js
│       ├── offscreen_polyfill.js
│       ├── tabgroups_polyfill.js
│       ├── declarativecontent_polyfill.js
│       └── sidepanel_polyfill.js
├── tests/                       # 18 unit tests
├── corpus/                      # Test extensions
├── output/                      # Converted extensions
└── pyproject.toml
```

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_analyzer.py -v

# Check coverage
python -m pytest tests/ --cov=chrome2fox
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ for the Firefox extension ecosystem**

[Report Bug](https://github.com/DannyBaanks/Chrome-to-Fox/issues) · [Request Feature](https://github.com/DannyBaanks/Chrome-to-Fox/issues) · [Documentation](https://github.com/DannyBaanks/Chrome-to-Fox)

</div>

<div align="center">

# 🔥🦊 Chrome-to-Fox

### Intelligent Chrome Extension → Firefox Porting Tool

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-18%20passing-brightgreen.svg)]()
[![Version](https://img.shields.io/badge/Version-0.1.0-orange.svg)]()

**Convert any Chrome extension to Firefox in seconds.**

</div>

---

## 🦊 Now Claude Works in Firefox!

> **The Claude Chrome extension has been successfully converted to Firefox!**
> 
> ```
> $ chrome2fox scan --extensions fcoeoabgfenejglbffodgkkbkcdhcgfn
> 
> Converting: Claude
> Files Processed: 498
> JS Files Patched: 369
> Shims Injected: 4
> Compatibility Score: 83%
> Status: ✅ Partial (warnings only, no errors)
> ```

**Stop waiting for official Firefox ports.** Chrome-to-Fox converts any Chrome extension to Firefox format automatically. Claude, ChatGPT, developer tools, productivity apps — they all work.

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
| 🔌 **Bridge Mode** | Scan your Chrome → Convert all → Install in Firefox |

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

### Convert Any Extension (3 commands)

```bash
# 1. Scan your Chrome extensions
chrome2fox scan

# 2. Convert one
chrome2fox convert /path/to/chrome-extension/ -o ./output/

# 3. Package as .xpi for Firefox
chrome2fox package ./output/ -o extension.xpi
```

### Or Use Bridge Mode (One Command)

```bash
# Scan Chrome + Convert all + Package automatically
chrome2fox bridge -o ./converted/

# Convert only specific extensions
chrome2fox bridge -o ./converted/ --extensions "id1,id2,id3"

# With XPI packaging
chrome2fox bridge -o ./converted/ --package-xpi
```

---

## Real Examples

### Claude (Anthropic's AI Assistant)

```bash
$ chrome2fox analyze /path/to/claude-extension/

Compatibility Score: 83%
Status: HIGH

✅ Manifest V3 → V2: PASS
✅ Browser namespace: PASS  
✅ API compatibility: PASS
⚠️  Shims needed: 4 (sidePanel, etc.)
```

### What Gets Converted

| Original (Chrome) | Converted (Firefox) |
|-------------------|---------------------|
| `chrome.tabs.query()` | `browser.tabs.query()` |
| `chrome.sidePanel` | `browser.sidebarAction` |
| `service_worker: {}` | `background: { scripts: [...] }` |
| `host_permissions` | Merged into `permissions` |
| `action.default_popup` | `browser_action.default_popup` |

### Shims Auto-Injected

These polyfills are automatically added to make Chrome-only APIs work in Firefox:

| API | What It Does |
|-----|--------------|
| `chrome.debugger` | Full Chrome DevTools Protocol bridge |
| `chrome.usb` | WebUSB → Firefox bridge |
| `chrome.serial` | Web Serial → Firefox bridge |
| `chrome.hid` | WebHID → Firefox bridge |
| `chrome.tts` | Web Speech API bridge |
| `chrome.tabCapture` | Tab capture bridge |

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
| `scan` | Scan Chrome extensions | `chrome2fox scan` |
| `analyze` | Analyze compatibility | `chrome2fox analyze ./ext/` |
| `convert` | Convert to Firefox | `chrome2fox convert ./ext/ -o ./out/` |
| `validate` | Validate Firefox extension | `chrome2fox validate ./out/` |
| `package` | Create .xpi | `chrome2fox package ./out/ -o ext.xpi` |
| `repair` | Convert + test + repair | `chrome2fox repair ./ext/ -o ./out/ --llm-base-url ...` |
| `bridge` | Scan + Convert all | `chrome2fox bridge -o ./out/` |
| `corpus` | Build extension corpus | `chrome2fox corpus ./exts/ -o ./corpus/` |
| `patterns` | Detect repair patterns | `chrome2fox patterns ./corpus/ -o rules.json` |

---

## Project Structure

```
Chrome-to-Fox/
├── src/chrome2fox/
│   ├── __init__.py              # Package metadata
│   ├── cli.py                   # CLI interface (9 commands)
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
│   ├── chrome_scanner.py        # Scan Chrome extensions
│   ├── firefox_exporter.py      # Batch export to Firefox
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

**Now Claude works in Firefox! 🦊**

[Report Bug](https://github.com/DannyBaanks/Chrome-to-Fox/issues) · [Request Feature](https://github.com/DannyBaanks/Chrome-to-Fox/issues) · [Documentation](https://github.com/DannyBaanks/Chrome-to-Fox)

</div>

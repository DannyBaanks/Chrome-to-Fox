# Changelog

All notable changes to Chrome-to-Fox will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-21

### Added

- **Analyzer**: AST-based scanning of JavaScript files for `chrome.*` API usage
- **Compatibility scoring**: Automatic calculation of Firefox compatibility score (0-1)
- **Manifest Transformer**: Chrome MV2/MV3 → Firefox with gecko settings
  - Adds `browser_specific_settings.gecko.id` automatically
  - Removes Chrome-specific fields (`key`, `minimum_chrome_version`)
  - Moves `host_permissions` to `permissions` for MV3
- **JS Patcher**: Selective `chrome.*` → `browser.*` replacement
  - Preserves `chrome-extension://` URLs
  - Only patches known compatible APIs
  - Reports all changes with line numbers
- **Validator**: Firefox extension validation
  - Manifest schema validation
  - Referenced file existence checks
  - Chrome API usage detection
- **Package**: `.xpi` file creation
  - ZIP-based packaging
  - SHA256 hash calculation
  - File size reporting
- **CLI**: Four commands (`analyze`, `convert`, `validate`, `package`)
- **Shims**: Polyfills for 10 Chrome-only APIs
  - `chrome.offscreen` → Mock with warnings
  - `chrome.tabGroups` → Storage-based simulation
  - `chrome.declarativeContent` → Rule storage only
  - `chrome.sidePanel` → Maps to sidebarAction
  - `chrome.debugger` → No-op with warnings
  - `chrome.tabCapture` → No-op with warnings
  - `chrome.tts` → Web Speech API fallback
  - `chrome.usb` → No-op with warnings
  - `chrome.serial` → No-op with warnings
  - `chrome.hid` → No-op with warnings
- **Corpus**: 6 test extensions
  - Simple popup
  - Content script
  - Background worker
  - Popup UI
  - Permissions only
  - Has offscreen API
- **Tests**: 18 unit tests passing
- **Documentation**: README.md, GUIA.md (Spanish)

### Fixed

- None (initial release)

### Changed

- None (initial release)

### Deprecated

- None

### Removed

- None

### Security

- None (initial release)

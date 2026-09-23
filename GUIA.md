# Chrome-to-Fox

Chrome extension to Firefox extension converter.

## Quick Start

```bash
# Install
cd "/home/danny/Development/ISyCo Git/Chrome-to-Fox"
pip install -e .

# Analyze
chrome2fox analyze /path/to/extension/

# Convert
chrome2fox convert /path/to/extension/ -o output/

# Validate
chrome2fox validate output/

# Package
chrome2fox package output/ -o extension.xpi
```

## Commands

| Command | Description |
|---------|-------------|
| `analyze` | Scan Chrome extension for Firefox compatibility |
| `convert` | Transform Chrome extension to Firefox format |
| `validate` | Check Firefox extension for errors |
| `package` | Create .xpi file for AMO submission |
| `sign` | Submit to AMO and fetch the signed .xpi (needs AMO_API_KEY + AMO_API_SECRET) |

## Examples

### Simple Extension

```bash
chrome2fox convert corpus/simple-popup/ -o output/simple-popup/
# Output: manifest.json patched with gecko settings, JS patched
```

### Extension with Chrome-only APIs

```bash
chrome2fox analyze corpus/has-offscreen/
# Output: warnings about chrome.offscreen (Chrome-only API)
```

## Signing (pipeline automatico)

```bash
# 1. Claves (una vez): https://addons.mozilla.org/developers/addon/api/key/
export AMO_API_KEY="jwt-issuer..."
export AMO_API_SECRET="jwt-secret..."

# 2. Pipeline completo
chrome2fox convert corpus/foxblock-adblock -o output/foxblock-adblock-firefox
chrome2fox validate output/foxblock-adblock-firefox
chrome2fox sign output/foxblock-adblock-firefox -o output/signed --channel unlisted --wait-download  # espera la revision y descarga el .xpi solo
# El .xpi firmado cae en output/signed/ y se instala PERMANENTE (doble clic o about:addons)
```

- `unlisted` = firmado sin publicar (para ti / tu gente). `listed` = tienda publica.
- Las claves viajan por entorno al proceso hijo, nunca en argv ni en logs.
- AMO tarda 1-5 min la primera vez; sube `--timeout` si corta antes.

## Traps

1. **Missing gecko.id**: Firefox requires `browser_specific_settings.gecko.id` — the converter adds it automatically
2. **chrome-extension:// URLs**: These are preserved (not patched) as they're part of the extension's identity
3. **Service Workers**: Firefox MV3 supports both `service_worker` and `background.scripts`
4. **host_permissions**: Firefox MV3 supports `host_permissions` natively — the converter keeps them as-is (merging into `permissions` is invalid per `web-ext lint`)

## Limitations

- Does not convert Native Messaging extensions (requires separate native app)
- Does not support remotely hosted code (prohibited in MV3)
- Chrome-only APIs get polyfills but may not work identically
- Does not modify extension behavior — only format conversion

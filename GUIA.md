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

## Instalacion (comando `chrome2fox` en tu PATH)

```bash
cd "/home/danny/Development/ISyCo Git/Chrome-to-Fox"
pipx install --editable .   # una vez; crea ~/.local/bin/chrome2fox
chrome2fox --version        # desde cualquier carpeta
chrome2fox                  # menu interactivo (con TTY)
chrome2fox up ./mi-ext/ -o ./out/  # ★ flujo completo + dashboard
```

Tus envios se anotan solos en `~/.config/chrome2fox/submissions.json`:
`chrome2fox my-addons` = tu cuenta + tus envios con estado vivo + link.
`chrome2fox search <texto>` = addons publicos que ya existen (sin claves).

## Bajar por link (estilo fox-convert)

```bash
chrome2fox fetch "https://chromewebstore.google.com/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm" -o ./ublock-src/
chrome2fox up "https://chromewebstore.google.com/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm" -o ./ublock-fox/
# con claves AMO exportadas, el up ADEMAS la firma: link -> .xpi firmado
```

Trampas:
- `web-ext lint` siempre mostrara 2 warnings KEY_FIREFOX_UNSUPPORTED_BY_MIN_VERSION
  (`data_collection_permissions` pide FF140+/142, sellamos 113 por DNR). Son informativos:
  Firefox viejo ignora la clave y AMO no bloquea por warnings. NO subas el minimo a 140
  o le cierras la puerta a FF113-139.
- Google limita descargas automaticas (HTTP 204 / `noupdate` fantasma). Si el fetch falla,
  baja el .crx a mano (modo desarrollador de Chrome) y usa la carpeta local.
- Firmar extensiones AJENAS: solo canal `unlisted` y para uso propio. `listed`
  seria republicar trabajo ajeno (violacion de politicas AMO).

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
- Para ver como va la revision sin abrir el navegador:
  `chrome2fox status output/foxblock-adblock-firefox` (exit 0 = aprobada, 1 = en cola; trae `review_url`).

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

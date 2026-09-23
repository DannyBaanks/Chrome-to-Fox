# FoxBlock Minimal Adblocker (fuente Chrome MV3)

Ejemplo minimo para probar `chrome2fox`: DNR (`rules.json`, 12 reglas) + filtro
cosmetico (`content.js`) + popup con toggle.

```bash
chrome2fox analyze corpus/foxblock-adblock
chrome2fox convert corpus/foxblock-adblock -o output/foxblock-adblock-firefox
chrome2fox validate output/foxblock-adblock-firefox
chrome2fox package output/foxblock-adblock-firefox -o output/foxblock-adblock.xpi
```

Carga manual: `chrome://extensions` (modo desarrollador) o `about:debugging#/runtime/this-firefox`.

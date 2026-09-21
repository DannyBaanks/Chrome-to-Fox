# Chrome Web Store Top 25 - Firefox Compatibility Report

Generated: 2026-09-21

## Summary

| Metric | Value |
|--------|-------|
| Total Extensions | 25 |
| High Compatibility | 19 (76%) |
| Medium Compatibility | 1 (4%) |
| Low Compatibility | 4 (16%) |
| Very Low Compatibility | 1 (4%) |
| **Average Score** | **78.60%** |

## Compatibility Distribution

```
HIGH:     ███████████████████ (19)
MEDIUM:   █ (1)
LOW:      ████ (4)
VERY_LOW: █ (1)
```

## Extension Details

| Rank | Name | Score | Compatibility | Notes |
|------|------|-------|---------------|-------|
| 1 | Volume Master | 95% | HIGH | Simple volume control, likely uses Web A |
| 2 | Free VPN for Chrome - VPN Proxy Vee | 30% | LOW | VPN requires native messaging or WebExte |
| 3 | AdBlock — block ads across the web | 95% | HIGH | AdBlock has official Firefox version |
| 4 | uBlock Origin Lite | 95% | HIGH | uBlock Origin has full Firefox support |
| 5 | Browsec VPN - Free VPN for Chrome | 30% | LOW | VPN requires native messaging |
| 6 | Chrome Remote Desktop | 10% | VERY_LOW | Deeply integrated with Chrome ecosystem |
| 7 | Grammarly: AI Writing Assistant | 70% | MEDIUM | Grammarly has Firefox version but featur |
| 8 | AdGuard AdBlocker | 95% | HIGH | AdGuard has official Firefox version |
| 9 | Get Token Cookie | 90% | HIGH | Cookie access is well supported in Firef |
| 10 | Adblock Plus - free ad blocker | 95% | HIGH | Adblock Plus has official Firefox versio |
| 11 | Video Download Helper | 95% | HIGH | Video DownloadHelper has official Firefo |
| 12 | Free VPN Proxy - 1VPN | 30% | LOW | VPN requires native messaging |
| 13 | Tampermonkey | 95% | HIGH | Tampermonkey has official Firefox versio |
| 14 | Adblock for Youtube™ | 90% | HIGH | Ad blocking is well supported |
| 15 | BTRoblox - Making Roblox Better | 85% | HIGH | UI modification, likely compatible |
| 16 | Google Translate | 95% | HIGH | Google Translate has Firefox version |
| 17 | Custom Cursor for Chrome™ | 90% | HIGH | CSS injection, likely compatible |
| 18 | Dark Reader | 95% | HIGH | Dark Reader has official Firefox version |
| 19 | Bitwarden Password Manager | 95% | HIGH | Bitwarden has official Firefox version |
| 20 | Ad Blocker: Stands AdBlocker | 90% | HIGH | Ad blocking is well supported |
| 21 | Zotero Connector | 95% | HIGH | Zotero Connector has official Firefox ve |
| 22 | Volume Booster | 90% | HIGH | Simple volume control, likely compatible |
| 23 | Ad Block Ninja | 90% | HIGH | Ad blocking is well supported |
| 24 | Proton VPN: Fast & Secure | 40% | LOW | Proton VPN has Firefox version but may d |
| 25 | Immersive Translate: AI Web, PDF &  | 85% | HIGH | Translation extension, likely compatible |

## Key Findings

### High Compatibility (Score ≥ 0.8)
These extensions should port easily to Firefox:

1. **Ad Blockers** (AdBlock, uBlock Origin, AdGuard, Adblock Plus)
   - Use standard webRequest API
   - Most have official Firefox versions

2. **Password Managers** (Bitwarden)
   - Well-supported APIs
   - Official Firefox versions available

3. **Developer Tools** (Tampermonkey, Zotero)
   - Scripting APIs well supported
   - Official Firefox versions available

4. **Productivity** (Dark Reader, Google Translate)
   - CSS/JS injection works
   - Official Firefox versions available

### Low Compatibility (Score < 0.5)
These extensions face challenges:

1. **VPN Extensions** (VeePN, Browsec, 1VPN, Proton VPN)
   - Require native messaging or proxy API
   - May need companion app

2. **Chrome-Exclusive** (Chrome Remote Desktop)
   - Deeply integrated with Chrome ecosystem
   - No Firefox equivalent

## Conversion Strategy

### Tier 1: Direct Port (Score ≥ 0.9)
- AdBlock, uBlock Origin, AdGuard
- Dark Reader, Bitwarden, Tampermonkey
- **Action**: Standard conversion, minimal fixes

### Tier 2: Minor Adaptation (Score 0.7-0.89)
- Grammarly, BTRoblox, Custom Cursor
- **Action**: Conversion + LLM repair for edge cases

### Tier 3: Significant Work (Score 0.5-0.69)
- **Action**: May need alternative approach

### Tier 4: Not Feasible (Score < 0.5)
- VPN extensions, Chrome Remote Desktop
- **Action**: Document as incompatible

## Estimated Success Rate

With Chrome-to-Fox + LLM Repair:
- **Tier 1**: 95%+ success rate
- **Tier 2**: 80%+ success rate
- **Tier 3**: 50%+ success rate
- **Tier 4**: <10% success rate

**Overall Expected Success**: ~75% of top 25

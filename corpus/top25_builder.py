#!/usr/bin/env python3
"""
Chrome Web Store Top 25 Corpus Builder

Fetches the top 25 Chrome extensions and builds a corpus
for Chrome-to-Fox compatibility testing.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Top 25 Chrome Extensions (September 2026)
TOP_25_EXTENSIONS = [
    {
        "rank": 1,
        "name": "Volume Master",
        "id": "jghecgabfgfdldnmbfkhmffcabddioke",
        "rating": 4.8,
        "category": "utilities",
        "description": "Up to 600% volume boost",
        "url": "https://chromewebstore.google.com/detail/volume-master/jghecgabfgfdldnmbfkhmffcabddioke"
    },
    {
        "rank": 2,
        "name": "Free VPN for Chrome - VPN Proxy VeePN",
        "id": "majdfhpaihoncoakbjgbdhglocklcgno",
        "rating": 4.5,
        "category": "privacy",
        "description": "Fast, ultra secure, and easy to use VPN service",
        "url": "https://chromewebstore.google.com/detail/free-vpn-for-chrome-vpn-p/majdfhpaihoncoakbjgbdhglocklcgno"
    },
    {
        "rank": 3,
        "name": "AdBlock — block ads across the web",
        "id": "gighmmpiobklfepjocnamgkkbiglidom",
        "rating": 4.5,
        "category": "productivity",
        "description": "Block ads on YouTube and your favorite sites",
        "url": "https://chromewebstore.google.com/detail/adblock-%E2%80%94-block-ads-acros/gighmmpiobklfepjocnamgkkbiglidom"
    },
    {
        "rank": 4,
        "name": "uBlock Origin Lite",
        "id": "ddkjiahejlhfcafbddmgiahcphecmpfh",
        "rating": 4.5,
        "category": "productivity",
        "description": "An efficient content blocker",
        "url": "https://chromewebstore.google.com/detail/ublock-origin-lite/ddkjiahejlhfcafbddmgiahcphecmpfh"
    },
    {
        "rank": 5,
        "name": "Browsec VPN - Free VPN for Chrome",
        "id": "omghfjlpggmjjaagoclmmobgdodcjboh",
        "rating": 4.5,
        "category": "privacy",
        "description": "Protects your IP from Internet threats",
        "url": "https://chromewebstore.google.com/detail/browsec-vpn-free-vpn-for/omghfjlpggmjjaagoclmmobgdodcjboh"
    },
    {
        "rank": 6,
        "name": "Chrome Remote Desktop",
        "id": "inomeogfingihgjfjlpeplalcfajhgai",
        "rating": 3.1,
        "category": "productivity",
        "description": "Chrome Remote Desktop extension",
        "url": "https://chromewebstore.google.com/detail/chrome-remote-desktop/inomeogfingihgjfjlpeplalcfajhgai"
    },
    {
        "rank": 7,
        "name": "Grammarly: AI Writing Assistant",
        "id": "kbfnbcaeplbcioakkpcpgfkobkghlhen",
        "rating": 4.5,
        "category": "productivity",
        "description": "AI support for grammar, clarity, and tone",
        "url": "https://chromewebstore.google.com/detail/grammarly-ai-writing-assi/kbfnbcaeplbcioakkpcpgfkobkghlhen"
    },
    {
        "rank": 8,
        "name": "AdGuard AdBlocker",
        "id": "bgnkhhnnamicmpeenaelnjfhikgbkllg",
        "rating": 4.7,
        "category": "productivity",
        "description": "Unmatched adblock extension",
        "url": "https://chromewebstore.google.com/detail/adguard-adblocker/bgnkhhnnamicmpeenaelnjfhikgbkllg"
    },
    {
        "rank": 9,
        "name": "Get Token Cookie",
        "id": "naciaagbkifhpnoodlkhbejjldaiffcm",
        "rating": 4.3,
        "category": "developer",
        "description": "Công cụ hỗ trợ lấy token, cookie",
        "url": "https://chromewebstore.google.com/detail/get-token-cookie/naciaagbkifhpnoodlkhbejjldaiffcm"
    },
    {
        "rank": 10,
        "name": "Adblock Plus - free ad blocker",
        "id": "cfhdojbkjhnklbpkdaibdccddilifddb",
        "rating": 4.4,
        "category": "productivity",
        "description": "Remove ads on YouTube and everywhere else",
        "url": "https://chromewebstore.google.com/detail/adblock-plus-free-ad-bloc/cfhdojbkjhnklbpkdaibdccddilifddb"
    },
    {
        "rank": 11,
        "name": "Video Download Helper",
        "id": "lmjnegcaeklhafolokijcfjliaokphfk",
        "rating": 4.5,
        "category": "utilities",
        "description": "Download Videos from the Web",
        "url": "https://chromewebstore.google.com/detail/video-download-helper/lmjnegcaeklhafolokijcfjliaokphfk"
    },
    {
        "rank": 12,
        "name": "Free VPN Proxy - 1VPN",
        "id": "akcocjjpkmlniicdeemdceeajlmoabhg",
        "rating": 4.7,
        "category": "privacy",
        "description": "Free VPN Proxy, Unlimited Data, Fast Speeds",
        "url": "https://chromewebstore.google.com/detail/free-vpn-proxy-1vpn/akcocjjpkmlniicdeemdceeajlmoabhg"
    },
    {
        "rank": 13,
        "name": "Tampermonkey",
        "id": "dhdgffkkebhmkfjojejmpbldmpobfkfo",
        "rating": 4.7,
        "category": "developer",
        "description": "Change the web at will with userscripts",
        "url": "https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo"
    },
    {
        "rank": 14,
        "name": "Adblock for Youtube™",
        "id": "cmedhionkhpnakcndndgjdbohmhepckk",
        "rating": 4.4,
        "category": "productivity",
        "description": "Removes ads from Youtube™",
        "url": "https://chromewebstore.google.com/detail/adblock-for-youtube/cmedhionkhpnakcndndgjdbohmhepckk"
    },
    {
        "rank": 15,
        "name": "BTRoblox - Making Roblox Better",
        "id": "hbkpclpemjeibhioopcebchdmohaieln",
        "rating": 4.1,
        "category": "entertainment",
        "description": "Enhance your Roblox experience!",
        "url": "https://chromewebstore.google.com/detail/btroblox-making-roblox-be/hbkpclpemjeibhioopcebchdmohaieln"
    },
    {
        "rank": 16,
        "name": "Google Translate",
        "id": "aapbdbdomjkkjkaonfhkkikfgjllcleb",
        "rating": 4.2,
        "category": "productivity",
        "description": "View translations easily as you browse the web",
        "url": "https://chromewebstore.google.com/detail/google-translate/aapbdbdomjkkjkaonfhkkikfgjllcleb"
    },
    {
        "rank": 17,
        "name": "Custom Cursor for Chrome™",
        "id": "ogdlpmhglpejoiomcodnpjnfgcpmgale",
        "rating": 4.7,
        "category": "appearance",
        "description": "Fun custom cursors for Chrome™",
        "url": "https://chromewebstore.google.com/detail/custom-cursor-for-chrome/ogdlpmhglpejoiomcodnpjnfgcpmgale"
    },
    {
        "rank": 18,
        "name": "Dark Reader",
        "id": "eimadpbcbfnmbkopoojfekhnkhdbieeh",
        "rating": 4.7,
        "category": "appearance",
        "description": "Dark mode for every website",
        "url": "https://chromewebstore.google.com/detail/dark-reader/eimadpbcbfnmbkopoojfekhnkhdbieeh"
    },
    {
        "rank": 19,
        "name": "Bitwarden Password Manager",
        "id": "nngceckbapebfimnlniiiahkandclblb",
        "rating": 4.3,
        "category": "productivity",
        "description": "Easily secures all your passwords, passkeys",
        "url": "https://chromewebstore.google.com/detail/bitwarden-password-manage/nngceckbapebfimnlniiiahkandclblb"
    },
    {
        "rank": 20,
        "name": "Ad Blocker: Stands AdBlocker",
        "id": "lgblnfidahcdcjddiepkckcfdhpknnjh",
        "rating": 4.8,
        "category": "productivity",
        "description": "Free ad blocker for YouTube, Twitch, Pop-Ups",
        "url": "https://chromewebstore.google.com/detail/ad-blocker-stands-adblock/lgblnfidahcdcjddiepkckcfdhpknnjh"
    },
    {
        "rank": 21,
        "name": "Zotero Connector",
        "id": "ekhagklcjbdpajgpjgmbionohlpdbjgc",
        "rating": 4.0,
        "category": "productivity",
        "description": "Save references to Zotero from your web browser",
        "url": "https://chromewebstore.google.com/detail/zotero-connector/ekhagklcjbdpajgpjgmbionohlpdbjgc"
    },
    {
        "rank": 22,
        "name": "Volume Booster",
        "id": "ejkiikneibegknkgimmihdpcbcedgmpo",
        "rating": 4.2,
        "category": "utilities",
        "description": "Chrome Extension for Boosting Volume Past Max Settings",
        "url": "https://chromewebstore.google.com/detail/volume-booster/ejkiikneibegknkgimmihdpcbcedgmpo"
    },
    {
        "rank": 23,
        "name": "Ad Block Ninja",
        "id": "ppfadpgpccljindldolejmgkhgaficka",
        "rating": 4.3,
        "category": "productivity",
        "description": "Blocks Ads and Popups",
        "url": "https://chromewebstore.google.com/detail/ad-block-ninja/ppfadpgpccljindldolejmgkhgaficka"
    },
    {
        "rank": 24,
        "name": "Proton VPN: Fast & Secure",
        "id": "jplgfhpmjnbigmhklmmbgecoobifkmpa",
        "rating": 4.3,
        "category": "privacy",
        "description": "Secure your internet and protect your online privacy",
        "url": "https://chromewebstore.google.com/detail/proton-vpn-fast-secure/jplgfhpmjnbigmhklmmbgecoobifkmpa"
    },
    {
        "rank": 25,
        "name": "Immersive Translate: AI Web, PDF & Video Translator",
        "id": "bpoadfkcbjbfhfodiogcnhhhpibjhbnh",
        "rating": 3.9,
        "category": "productivity",
        "description": "Free Translate Website, Translate PDF & Epub eBook",
        "url": "https://chromewebstore.google.com/detail/immersive-translate-ai-we/bpoadfkcbjbfhfodiogcnhhhpibjhbnh"
    }
]


def create_corpus_metadata(output_dir: Path) -> None:
    """Create corpus metadata file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        "name": "Chrome Web Store Top 25",
        "source": "https://chromewebstore.google.com/top-charts/popular",
        "date": "2026-09-21",
        "total_extensions": len(TOP_25_EXTENSIONS),
        "extensions": TOP_25_EXTENSIONS
    }
    
    metadata_path = output_dir / "corpus_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created corpus metadata: {metadata_path}")
    print(f"   Total extensions: {len(TOP_25_EXTENSIONS)}")


def analyze_categories() -> dict[str, int]:
    """Analyze extension categories."""
    categories = {}
    for ext in TOP_25_EXTENSIONS:
        cat = ext.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    return categories


def analyze_ratings() -> dict[str, int]:
    """Analyze rating distribution."""
    ratings = {"4.7-5.0": 0, "4.4-4.6": 0, "4.0-4.3": 0, "3.0-3.9": 0}
    
    for ext in TOP_25_EXTENSIONS:
        rating = ext.get("rating", 0)
        if rating >= 4.7:
            ratings["4.7-5.0"] += 1
        elif rating >= 4.4:
            ratings["4.4-4.6"] += 1
        elif rating >= 4.0:
            ratings["4.0-4.3"] += 1
        else:
            ratings["3.0-3.9"] += 1
    
    return ratings


def generate_report(output_dir: Path) -> None:
    """Generate analysis report."""
    categories = analyze_categories()
    ratings = analyze_ratings()
    
    report = f"""# Chrome Web Store Top 25 - Analysis Report

Generated: 2026-09-21

## Summary

- **Total Extensions**: {len(TOP_25_EXTENSIONS)}
- **Source**: Chrome Web Store Top Charts (Popular)

## Categories

"""
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        report += f"- **{cat}**: {count} extensions\n"
    
    report += "\n## Rating Distribution\n\n"
    for rating, count in ratings.items():
        report += f"- **{rating}**: {count} extensions\n"
    
    report += "\n## Extension List\n\n"
    report += "| Rank | Name | Rating | Category |\n"
    report += "|------|------|--------|----------|\n"
    
    for ext in TOP_25_EXTENSIONS:
        report += f"| {ext['rank']} | {ext['name'][:30]} | {ext['rating']} | {ext['category']} |\n"
    
    report += "\n## Firefox Compatibility Estimate\n\n"
    
    # Estimate compatibility based on common patterns
    vpn_count = sum(1 for e in TOP_25_EXTENSIONS if "vpn" in e["name"].lower())
    adblock_count = sum(1 for e in TOP_25_EXTENSIONS if "ad" in e["name"].lower() and "block" in e["name"].lower())
    
    report += f"- **VPN Extensions**: {vpn_count} (may need native messaging)\n"
    report += f"- **Ad Blockers**: {adblock_count} (usually compatible via webRequest)\n"
    report += f"- **Utility Extensions**: High compatibility expected\n"
    report += f"- **Productivity Extensions**: Medium compatibility (may use Chrome-only APIs)\n"
    
    report_path = output_dir / "ANALYSIS_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"✅ Generated analysis report: {report_path}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("Chrome Web Store Top 25 - Corpus Builder")
    print("=" * 60)
    
    # Create output directory
    output_dir = Path("./corpus/top25")
    
    # Create metadata
    create_corpus_metadata(output_dir)
    
    # Generate report
    generate_report(output_dir)
    
    print("\n" + "=" * 60)
    print("Top 25 Extensions:")
    print("=" * 60)
    
    for ext in TOP_25_EXTENSIONS:
        print(f"  {ext['rank']:2d}. {ext['name'][:40]:<40} ({ext['rating']})")
    
    print("\n" + "=" * 60)
    print(f"Corpus created at: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()

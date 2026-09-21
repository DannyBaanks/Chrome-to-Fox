"""
Chrome Extension Scanner — Detect installed Chrome extensions.

Scans Chrome's extension directories and provides
a list of installed extensions ready for conversion.
"""

import json
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ChromeExtension:
    """Represents an installed Chrome extension."""
    id: str
    name: str
    version: str
    description: str = ""
    manifest_version: int = 2
    permissions: list[str] = field(default_factory=list)
    path: Path = field(default_factory=Path)
    enabled: bool = True
    install_type: str = "normal"  # normal, development, unpacked
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "manifest_version": self.manifest_version,
            "permissions": self.permissions,
            "path": str(self.path),
            "enabled": self.enabled,
            "install_type": self.install_type
        }


class ChromeScanner:
    """
    Scan Chrome's extension directories.
    
    Detects installed extensions from:
    - Chrome (Windows/macOS/Linux)
    - Chromium
    - Edge (Chromium-based)
    
    Usage:
        scanner = ChromeScanner()
        extensions = scanner.scan()
        
        for ext in extensions:
            print(f"Found: {ext.name} ({ext.id})")
    """
    
    # Chrome data directory paths by platform
    CHROME_PATHS = {
        "Windows": [
            Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Extensions",
            Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Profile 1" / "Extensions",
            Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Profile 2" / "Extensions",
        ],
        "Darwin": [
            Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "Extensions",
            Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "Profile 1" / "Extensions",
            Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "Profile 2" / "Extensions",
        ],
        "Linux": [
            Path.home() / ".config" / "google-chrome" / "Default" / "Extensions",
            Path.home() / ".config" / "google-chrome" / "Profile 1" / "Extensions",
            Path.home() / ".config" / "google-chrome" / "Profile 2" / "Extensions",
            Path.home() / ".config" / "chromium" / "Default" / "Extensions",
        ]
    }
    
    # Edge paths (Chromium-based)
    EDGE_PATHS = {
        "Windows": [
            Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Extensions",
        ],
        "Darwin": [
            Path.home() / "Library" / "Application Support" / "Microsoft Edge" / "Default" / "Extensions",
        ],
        "Linux": [
            Path.home() / ".config" / "microsoft-edge" / "Default" / "Extensions",
        ]
    }
    
    def __init__(self, custom_paths: list[Path] | None = None):
        """
        Initialize scanner.
        
        Args:
            custom_paths: Custom paths to scan (overrides platform defaults)
        """
        self.custom_paths = custom_paths or []
        self._extensions: list[ChromeExtension] = []
    
    def scan(self, include_disabled: bool = False) -> list[ChromeExtension]:
        """
        Scan for installed Chrome extensions.
        
        Args:
            include_disabled: Include disabled extensions
            
        Returns:
            List of found ChromeExtension objects
        """
        self._extensions = []
        
        # Get platform-specific paths
        platform_name = platform.system()
        
        # Scan Chrome paths
        chrome_paths = self.CHROME_PATHS.get(platform_name, [])
        for ext_dir in chrome_paths:
            self._scan_directory(ext_dir, include_disabled)
        
        # Scan Edge paths
        edge_paths = self.EDGE_PATHS.get(platform_name, [])
        for ext_dir in edge_paths:
            self._scan_directory(ext_dir, include_disabled)
        
        # Scan custom paths
        for ext_dir in self.custom_paths:
            self._scan_directory(ext_dir, include_disabled)
        
        # Deduplicate by extension ID
        seen_ids = set()
        unique_extensions = []
        for ext in self._extensions:
            if ext.id not in seen_ids:
                seen_ids.add(ext.id)
                unique_extensions.append(ext)
        
        self._extensions = unique_extensions
        
        return self._extensions
    
    def _scan_directory(self, directory: Path, include_disabled: bool) -> None:
        """Scan a directory for Chrome extensions."""
        if not directory.exists():
            return
        
        # Chrome extensions are stored in directories named by their ID
        # Each ID directory contains version directories
        for ext_id_dir in directory.iterdir():
            if not ext_id_dir.is_dir():
                continue
            
            ext_id = ext_id_dir.name
            
            # Skip Chrome Web Store internal extensions
            if ext_id.startswith("aapb") or ext_id.startswith("ghbmnnjooekpmoecnnnilnnbdlolhkhi"):
                continue
            
            # Look for manifest.json in version directories
            for version_dir in ext_id_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                
                manifest_path = version_dir / "manifest.json"
                if manifest_path.exists():
                    ext = self._load_extension(ext_id, version_dir, manifest_path)
                    if ext:
                        if include_disabled or ext.enabled:
                            self._extensions.append(ext)
    
    def _load_extension(self, ext_id: str, version_dir: Path, manifest_path: Path) -> ChromeExtension | None:
        """Load extension from manifest.json."""
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            return None
        
        # Extract info
        name = manifest.get("name", "Unknown Extension")
        
        # Handle localized names
        if isinstance(name, dict):
            name = name.get("en", name.get("default", "Unknown Extension"))
        
        version = manifest.get("version", "0.0.0")
        description = manifest.get("description", "")
        
        # Handle localized descriptions
        if isinstance(description, dict):
            description = description.get("en", description.get("default", ""))
        
        manifest_version = manifest.get("manifest_version", 2)
        permissions = manifest.get("permissions", [])
        
        # Determine install type
        install_type = "normal"
        if (version_dir / "_metadata").exists():
            install_type = "development"
        
        return ChromeExtension(
            id=ext_id,
            name=name,
            version=version,
            description=description[:200],  # Truncate long descriptions
            manifest_version=manifest_version,
            permissions=permissions,
            path=version_dir,
            enabled=True,
            install_type=install_type
        )
    
    def get_extension(self, ext_id: str) -> ChromeExtension | None:
        """Get a specific extension by ID."""
        for ext in self._extensions:
            if ext.id == ext_id:
                return ext
        return None
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about scanned extensions."""
        if not self._extensions:
            self.scan()
        
        total = len(self._extensions)
        mv2 = sum(1 for e in self._extensions if e.manifest_version == 2)
        mv3 = sum(1 for e in self._extensions if e.manifest_version == 3)
        
        # Count permissions
        all_permissions = []
        for ext in self._extensions:
            all_permissions.extend(ext.permissions)
        
        permission_counts = {}
        for perm in all_permissions:
            permission_counts[perm] = permission_counts.get(perm, 0) + 1
        
        # Top permissions
        top_permissions = sorted(permission_counts.items(), key=lambda x: -x[1])[:10]
        
        return {
            "total": total,
            "manifest_v2": mv2,
            "manifest_v3": mv3,
            "top_permissions": top_permissions
        }
    
    def export_list(self, output_path: Path) -> int:
        """Export extension list to JSON."""
        extensions_data = [ext.to_dict() for ext in self._extensions]
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(extensions_data, f, indent=2, ensure_ascii=False)
        
        return len(extensions_data)


def scan_chrome_extensions(
    custom_paths: list[Path] | None = None,
    include_disabled: bool = False
) -> list[ChromeExtension]:
    """
    Convenience function to scan Chrome extensions.
    
    Args:
        custom_paths: Custom paths to scan
        include_disabled: Include disabled extensions
        
    Returns:
        List of ChromeExtension objects
    """
    scanner = ChromeScanner(custom_paths)
    return scanner.scan(include_disabled)


def get_chrome_extension_path() -> Path | None:
    """
    Get the default Chrome extensions directory for this platform.
    
    Returns:
        Path to Chrome extensions directory or None
    """
    platform_name = platform.system()
    
    # Try Chrome first
    chrome_paths = ChromeScanner.CHROME_PATHS.get(platform_name, [])
    for path in chrome_paths:
        if path.exists():
            return path.parent.parent.parent  # Go up to User Data
    
    # Try Edge
    edge_paths = ChromeScanner.EDGE_PATHS.get(platform_name, [])
    for path in edge_paths:
        if path.exists():
            return path.parent.parent.parent  # Go up to User Data
    
    return None


if __name__ == "__main__":
    print("Chrome Extension Scanner")
    print("=" * 60)
    
    scanner = ChromeScanner()
    extensions = scanner.scan()
    
    print(f"\nFound {len(extensions)} extensions\n")
    
    for i, ext in enumerate(extensions[:25], 1):
        print(f"{i:2d}. {ext.name[:40]:<40} (v{ext.version})")
        print(f"    ID: {ext.id}")
        print(f"    MV: {ext.manifest_version}")
        print()
    
    stats = scanner.get_stats()
    print(f"\nStats:")
    print(f"  Total: {stats['total']}")
    print(f"  MV2: {stats['manifest_v2']}")
    print(f"  MV3: {stats['manifest_v3']}")
    
    if stats['top_permissions']:
        print(f"\nTop Permissions:")
        for perm, count in stats['top_permissions'][:5]:
            print(f"  {perm}: {count}")

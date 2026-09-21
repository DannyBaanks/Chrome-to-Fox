"""
Corpus Builder — Build and manage a corpus of Chrome extensions.

Collects Chrome extensions, converts them, and builds
a corpus for pattern detection and training.
"""

import json
import hashlib
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CorpusEntry:
    """A single entry in the corpus."""
    entry_id: str
    extension_name: str
    extension_version: str
    source_url: str
    source_hash: str
    chrome_manifest_version: int
    compatibility_score: float
    conversion_status: str  # success, partial, failed
    test_status: str  # pass, fail, error
    repair_status: str  # not_needed, pass, degraded, not_repaired
    verdict: str  # PASS, DEGRADED, NOT_REPAIRED
    api_used: list[str] = field(default_factory=list)
    failed_apis: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CorpusStats:
    """Corpus statistics."""
    total_entries: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    pass_count: int = 0
    degraded_count: int = 0
    not_repaired_count: int = 0
    api_distribution: dict[str, int] = field(default_factory=dict)
    manifest_version_distribution: dict[int, int] = field(default_factory=dict)


class CorpusBuilder:
    """
    Build and manage a corpus of Chrome extensions.
    
    Collects extensions from various sources, converts them,
    and tracks results for pattern detection.
    
    Usage:
        builder = CorpusBuilder("./corpus")
        
        # Add an extension
        entry = builder.add_extension(
            source_path=Path("./extensions/my-extension"),
            source_url="https://chrome.google.com/webstore/..."
        )
        
        # Get stats
        stats = builder.get_stats()
        
        # Export for analysis
        builder.export_corpus("./corpus_export")
    """
    
    def __init__(self, corpus_dir: Path):
        """
        Initialize corpus builder.
        
        Args:
            corpus_dir: Directory to store corpus
        """
        self.corpus_dir = Path(corpus_dir)
        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        
        self.entries_dir = self.corpus_dir / "entries"
        self.entries_dir.mkdir(exist_ok=True)
        
        self.index_path = self.corpus_dir / "index.json"
        self._index: dict[str, dict[str, Any]] = self._load_index()
    
    def _load_index(self) -> dict[str, dict[str, Any]]:
        """Load corpus index."""
        if self.index_path.exists():
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_index(self) -> None:
        """Save corpus index."""
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2, ensure_ascii=False)
    
    def add_extension(
        self,
        source_path: Path,
        source_url: str = "",
        tags: list[str] | None = None
    ) -> CorpusEntry:
        """
        Add an extension to the corpus.
        
        Args:
            source_path: Path to Chrome extension
            source_url: Source URL (Chrome Web Store, GitHub, etc.)
            tags: Optional tags for categorization
            
        Returns:
            CorpusEntry with results
        """
        # Read manifest
        manifest = self._read_manifest(source_path)
        
        # Generate entry ID
        source_hash = self._hash_directory(source_path)
        entry_id = f"{manifest.get('name', 'unknown')}_{source_hash[:8]}"
        
        # Create entry directory
        entry_dir = self.entries_dir / entry_id
        entry_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy source extension
        source_dir = entry_dir / "source"
        if source_dir.exists():
            shutil.rmtree(source_dir)
        shutil.copytree(source_path, source_dir)
        
        # Create entry
        entry = CorpusEntry(
            entry_id=entry_id,
            extension_name=manifest.get("name", "unknown"),
            extension_version=manifest.get("version", "unknown"),
            source_url=source_url,
            source_hash=source_hash,
            chrome_manifest_version=manifest.get("manifest_version", 2),
            compatibility_score=0.0,
            conversion_status="pending",
            test_status="pending",
            repair_status="not_needed",
            verdict="UNKNOWN",
            api_used=self._extract_apis(source_path),
            failed_apis=[],
            tags=tags or []
        )
        
        # Save entry metadata
        self._save_entry(entry, entry_dir)
        
        # Update index
        self._index[entry_id] = {
            "extension_name": entry.extension_name,
            "extension_version": entry.extension_version,
            "source_url": entry.source_url,
            "source_hash": entry.source_hash,
            "timestamp": entry.timestamp
        }
        self._save_index()
        
        return entry
    
    def update_entry(
        self,
        entry_id: str,
        **kwargs
    ) -> CorpusEntry | None:
        """
        Update an existing entry.
        
        Args:
            entry_id: Entry ID to update
            **kwargs: Fields to update
            
        Returns:
            Updated CorpusEntry or None
        """
        entry_dir = self.entries_dir / entry_id
        if not entry_dir.exists():
            return None
        
        # Load existing entry
        entry = self._load_entry(entry_id)
        if not entry:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        # Save updated entry
        self._save_entry(entry, entry_dir)
        
        return entry
    
    def get_entry(self, entry_id: str) -> CorpusEntry | None:
        """Get an entry by ID."""
        return self._load_entry(entry_id)
    
    def list_entries(
        self,
        status: str | None = None,
        tags: list[str] | None = None
    ) -> list[CorpusEntry]:
        """
        List entries with optional filters.
        
        Args:
            status: Filter by conversion/test/repair status
            tags: Filter by tags
            
        Returns:
            List of matching entries
        """
        entries = []
        
        for entry_id in self._index.keys():
            entry = self._load_entry(entry_id)
            if not entry:
                continue
            
            # Apply filters
            if status:
                if entry.conversion_status != status and \
                   entry.test_status != status and \
                   entry.repair_status != status:
                    continue
            
            if tags:
                if not any(tag in entry.tags for tag in tags):
                    continue
            
            entries.append(entry)
        
        return entries
    
    def get_stats(self) -> CorpusStats:
        """Get corpus statistics."""
        stats = CorpusStats()
        
        api_counts: dict[str, int] = {}
        mv_counts: dict[int, int] = {}
        
        for entry_id in self._index.keys():
            entry = self._load_entry(entry_id)
            if not entry:
                continue
            
            stats.total_entries += 1
            
            # Conversion status
            if entry.conversion_status == "success":
                stats.successful_conversions += 1
            elif entry.conversion_status == "failed":
                stats.failed_conversions += 1
            
            # Verdict
            if entry.verdict == "PASS":
                stats.pass_count += 1
            elif entry.verdict == "DEGRADED":
                stats.degraded_count += 1
            elif entry.verdict == "NOT_REPAIRED":
                stats.not_repaired_count += 1
            
            # API distribution
            for api in entry.api_used:
                api_counts[api] = api_counts.get(api, 0) + 1
            
            # Manifest version distribution
            mv = entry.chrome_manifest_version
            mv_counts[mv] = mv_counts.get(mv, 0) + 1
        
        stats.api_distribution = api_counts
        stats.manifest_version_distribution = mv_counts
        
        return stats
    
    def export_corpus(self, output_dir: Path) -> int:
        """
        Export corpus for analysis.
        
        Args:
            output_dir: Output directory
            
        Returns:
            Number of entries exported
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        count = 0
        
        for entry_id in self._index.keys():
            entry_dir = self.entries_dir / entry_id
            if not entry_dir.exists():
                continue
            
            # Copy source extension
            source_dir = entry_dir / "source"
            if source_dir.exists():
                export_dir = output_dir / entry_id
                if export_dir.exists():
                    shutil.rmtree(export_dir)
                shutil.copytree(source_dir, export_dir)
                count += 1
        
        # Export index
        index_output = output_dir / "index.json"
        with open(index_output, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2, ensure_ascii=False)
        
        return count
    
    def _read_manifest(self, extension_path: Path) -> dict[str, Any]:
        """Read manifest file."""
        manifest_path = extension_path / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _hash_directory(self, directory: Path) -> str:
        """Calculate hash of directory contents."""
        hasher = hashlib.sha256()
        
        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file():
                try:
                    content = file_path.read_bytes()
                    hasher.update(content)
                except Exception:
                    pass
        
        return hasher.hexdigest()[:16]
    
    def _extract_apis(self, extension_path: Path) -> list[str]:
        """Extract Chrome APIs used in extension."""
        apis = set()
        
        for js_file in extension_path.rglob("*.js"):
            try:
                content = js_file.read_text(encoding="utf-8")
                
                # Find chrome.* APIs
                import re
                found = re.findall(r'chrome\.(\w+)', content)
                apis.update(found)
                
            except Exception:
                pass
        
        return sorted(apis)
    
    def _save_entry(self, entry: CorpusEntry, entry_dir: Path) -> None:
        """Save entry metadata."""
        entry_data = {
            "entry_id": entry.entry_id,
            "extension_name": entry.extension_name,
            "extension_version": entry.extension_version,
            "source_url": entry.source_url,
            "source_hash": entry.source_hash,
            "chrome_manifest_version": entry.chrome_manifest_version,
            "compatibility_score": entry.compatibility_score,
            "conversion_status": entry.conversion_status,
            "test_status": entry.test_status,
            "repair_status": entry.repair_status,
            "verdict": entry.verdict,
            "api_used": entry.api_used,
            "failed_apis": entry.failed_apis,
            "tags": entry.tags,
            "timestamp": entry.timestamp
        }
        
        entry_file = entry_dir / "entry.json"
        with open(entry_file, "w", encoding="utf-8") as f:
            json.dump(entry_data, f, indent=2, ensure_ascii=False)
    
    def _load_entry(self, entry_id: str) -> CorpusEntry | None:
        """Load entry from disk."""
        entry_dir = self.entries_dir / entry_id
        entry_file = entry_dir / "entry.json"
        
        if not entry_file.exists():
            return None
        
        try:
            with open(entry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return CorpusEntry(**data)
        except Exception:
            return None


def build_corpus(
    extensions_dir: Path,
    corpus_dir: Path,
    source_url: str = ""
) -> CorpusStats:
    """
    Convenience function to build a corpus from a directory of extensions.
    
    Args:
        extensions_dir: Directory containing Chrome extensions
        corpus_dir: Output corpus directory
        source_url: Source URL for all extensions
        
    Returns:
        Corpus statistics
    """
    builder = CorpusBuilder(corpus_dir)
    
    # Find all extensions
    for ext_path in extensions_dir.iterdir():
        if ext_path.is_dir():
            manifest_path = ext_path / "manifest.json"
            if manifest_path.exists():
                builder.add_extension(ext_path, source_url)
    
    return builder.get_stats()


if __name__ == "__main__":
    print("Corpus Builder for Chrome-to-Fox")
    print("=" * 60)
    print("Build and manage a corpus of Chrome extensions")
    print("\nUsage:")
    print("  from chrome2fox.corpus_builder import CorpusBuilder")
    print("  builder = CorpusBuilder('./corpus')")
    print("  entry = builder.add_extension(ext_path)")
    print("  stats = builder.get_stats()")

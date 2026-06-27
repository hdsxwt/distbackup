"""Save and load named directory snapshots as JSON files."""

import json
import os
from datetime import datetime, timezone

from ._win32 import hide_dir


class SnapshotManager:
    """Manages named snapshots stored under .backup/snapshots/."""

    def __init__(self, root: str):
        self._backup_root = os.path.join(root, ".backup")
        self._snap_dir = os.path.join(self._backup_root, "snapshots")
        os.makedirs(self._snap_dir, exist_ok=True)
        hide_dir(self._backup_root)

    def save(self, name: str, files: dict[str, str], directory: str) -> str:
        """Save a snapshot and return its file path."""
        snapshot = {
            "created": datetime.now(timezone.utc).isoformat(),
            "root": os.path.abspath(directory),
            "files": files,
        }
        path = self._path_for(name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        return path

    def load(self, name: str) -> dict:
        """Load a snapshot. Returns {"created", "root", "files": {path: hash}}."""
        path = self._path_for(name)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_snapshots(self) -> list[str]:
        """Return names of all saved snapshots (without .json extension)."""
        names = []
        try:
            for entry in os.scandir(self._snap_dir):
                if entry.is_file() and entry.name.endswith(".json"):
                    names.append(entry.name[:-5])
        except FileNotFoundError:
            pass
        return sorted(names)

    def _path_for(self, name: str) -> str:
        safe = name.replace("/", "_").replace("\\", "_")
        return os.path.join(self._snap_dir, f"{safe}.json")

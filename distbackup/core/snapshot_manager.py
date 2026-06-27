"""Save and load named directory snapshots as JSON files."""

import json
import os
import tempfile
import logging
from datetime import datetime, timezone
from typing import Literal

from ._win32 import hide_dir

logger = logging.getLogger(__name__)

RepoType = Literal["Source", "Target"]


class SnapshotManager:
    """Manages named snapshots stored under .backup/snapshots/.

    Each .backup directory carries a ``config.json`` that records the
    repository type:

    - ``"Source"``: this directory is the origin of truth.  It may never be
      used as a sync *target* (i.e. data is never written into it).
    - ``"Target"``: this directory can be used as either a source or a
      target.

    The default type is ``"Target"`` when no config exists yet.
    """

    def __init__(self, root: str):
        self._backup_root = os.path.join(root, ".backup")
        self._snap_dir = os.path.join(self._backup_root, "snapshots")
        os.makedirs(self._snap_dir, exist_ok=True)
        hide_dir(self._backup_root)
        self._ensure_config()

    # -- config ---------------------------------------------------------

    @property
    def _config_path(self) -> str:
        return os.path.join(self._backup_root, "config.json")

    def _ensure_config(self) -> None:
        if not os.path.isfile(self._config_path):
            self._write_config({"type": "Target"})

    def _read_config(self) -> dict:
        with open(self._config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_config(self, data: dict) -> None:
        fd, tmp = tempfile.mkstemp(
            suffix=".json", prefix=".tmp-", dir=self._backup_root
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._config_path)
        except Exception:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise

    def get_repo_type(self) -> RepoType:
        """Return the repository type: ``"Source"`` or ``"Target"``."""
        return self._read_config().get("type", "Target")

    def set_repo_type(self, value: RepoType) -> None:
        """Set the repository type."""
        if value not in ("Source", "Target"):
            raise ValueError(f"Invalid repo type: {value!r}")
        self._write_config({"type": value})

    # -- snapshots ------------------------------------------------------

    def save(self, name: str, files: dict[str, str], directory: str) -> str:
        """Save a snapshot atomically and return its file path.

        Writes to a temporary file first, then atomically renames it to the
        final path so a crash cannot leave a truncated JSON behind.
        """
        snapshot = {
            "created": datetime.now(timezone.utc).isoformat(),
            "root": os.path.abspath(directory),
            "files": files,
        }
        path = self._path_for(name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json", prefix=".tmp-", dir=self._snap_dir
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise
        return path

    def load(self, name: str) -> dict:
        """Load a snapshot. Returns {"created", "root", "files": {path: hash}}.

        Raises FileNotFoundError if the snapshot does not exist.
        Raises ValueError if the JSON is corrupted or unreadable.
        """
        path = self._path_for(name)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Snapshot '{name}' not found at {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Snapshot '{name}' is corrupted (invalid JSON): {exc}"
            ) from exc

    def validate_root(self, name: str, expected_directory: str) -> None:
        """Raise ValueError if the snapshot root does not match *expected_directory*.

        This prevents using a snapshot from one directory with another
        directory during sync / diff operations.
        """
        snap = self.load(name)
        snap_root = os.path.abspath(snap.get("root", ""))
        expected = os.path.abspath(expected_directory)
        if snap_root != expected:
            raise ValueError(
                f"Snapshot '{name}' root mismatch: "
                f"snapshot was created for '{snap_root}' "
                f"but expected '{expected}'"
            )

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

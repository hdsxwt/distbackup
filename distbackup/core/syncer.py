"""Copy new and changed files from source directory to target directory."""

import os
import shutil
from collections.abc import Callable

from .differ import DiffResult


class Syncer:
    """Applies a diff by copying files from source to target.

    Only copies *added* and *modified* files.  *removed* files on the target
    side are left untouched (safe-by-default semantics).
    """

    def __init__(self, progress_callback: Callable[[int, int], None] | None = None):
        self._on_progress = progress_callback

    def sync(
        self,
        source_dir: str,
        target_dir: str,
        diff: DiffResult,
    ) -> dict:
        """Copy added/modified files. Returns stats dict."""
        to_copy = diff.added + diff.modified
        total = len(to_copy)
        stats = {"copied": 0, "skipped": 0, "errors": 0}

        if total == 0:
            return stats

        for idx, relpath in enumerate(to_copy):
            src = os.path.join(source_dir, relpath)
            dst = os.path.join(target_dir, relpath)
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                stats["copied"] += 1
            except (OSError, PermissionError):
                stats["errors"] += 1

            if self._on_progress:
                self._on_progress(idx + 1, total)

        return stats

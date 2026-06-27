"""Copy new and changed files from source directory to target directory."""

import os
import shutil
import logging
from collections.abc import Callable

from .differ import DiffResult

logger = logging.getLogger(__name__)


def _is_safe_target(target_dir: str, dst_path: str) -> bool:
    """Return True if *dst_path* resolves inside *target_dir*."""
    target_abs = os.path.abspath(target_dir)
    dst_abs = os.path.abspath(dst_path)
    try:
        common = os.path.commonpath([target_abs, dst_abs])
    except ValueError:
        return False
    return os.path.normcase(common) == os.path.normcase(target_abs)


class Syncer:
    """Applies a diff by copying files from source to target.

    Only copies *added* and *modified* files.  *removed* files on the target
    side are left untouched (safe-by-default semantics).
    """

    def __init__(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
        dry_run: bool = False,
    ):
        self._on_progress = progress_callback
        self._dry_run = dry_run

    def sync(
        self,
        source_dir: str,
        target_dir: str,
        diff: DiffResult,
    ) -> dict:
        """Copy added/modified files. Returns stats dict.

        stats keys: copied, skipped, errors, failed
        ``failed`` is a list of ``(relpath, error_message)`` tuples.
        """
        to_copy = diff.added + diff.modified
        total = len(to_copy)
        stats = {
            "copied": 0,
            "skipped": 0,
            "errors": 0,
            "failed": [],
        }

        if total == 0:
            return stats

        for idx, relpath in enumerate(to_copy):
            src = os.path.join(source_dir, relpath)
            dst = os.path.join(target_dir, relpath)

            if not _is_safe_target(target_dir, dst):
                stats["errors"] += 1
                stats["failed"].append((relpath, "path traversal blocked"))
                logger.warning("Blocked path traversal: %s -> %s", relpath, dst)
                continue

            try:
                if self._dry_run:
                    stats["copied"] += 1
                else:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    stats["copied"] += 1

            except (OSError, PermissionError) as exc:
                stats["errors"] += 1
                stats["failed"].append((relpath, str(exc)))
                logger.warning("Failed to copy %s: %s", relpath, exc)

            if self._on_progress:
                self._on_progress(idx + 1, total)

        return stats

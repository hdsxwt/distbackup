"""Walk a directory tree and produce a {relpath: hash} mapping."""

import os

from .hashing import hash_file

SKIP_NAMES = {".backup", ".git", "__pycache__", ".DS_Store", "Thumbs.db"}


class Scanner:
    """Scans a directory, hashing every file found."""

    @staticmethod
    def scan(directory: str) -> dict[str, str]:
        """Walk *directory* and return {relpath: sha256hex}."""
        directory = os.path.abspath(directory)
        result: dict[str, str] = {}

        for dirpath, dirnames, filenames in os.walk(directory):
            dirnames[:] = [d for d in dirnames if d not in SKIP_NAMES]

            for fname in filenames:
                if fname in SKIP_NAMES:
                    continue

                full = os.path.join(dirpath, fname)
                try:
                    digest = hash_file(full)
                except (OSError, PermissionError):
                    continue

                rel = os.path.relpath(full, directory)
                result[rel] = digest

        return result

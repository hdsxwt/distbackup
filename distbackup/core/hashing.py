"""SHA256 hashing utilities for the backup system."""

import hashlib
import os


CHUNK_SIZE = 65536  # 64 KB


def hash_file(filepath: str, chunk_size: int = CHUNK_SIZE) -> str:
    """Hash a file by reading it in chunks. Returns hex digest."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def hash_bytes(data: bytes) -> str:
    """Hash raw bytes. Returns hex digest."""
    return hashlib.sha256(data).hexdigest()

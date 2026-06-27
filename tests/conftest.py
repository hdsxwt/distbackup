"""Shared fixtures for the distbackup test suite."""

import os
import pytest


# ---------------------------------------------------------------------------
# Tree builder helper
# ---------------------------------------------------------------------------

def build_tree(root, spec):
    """Recursively create files/dirs described by *spec*.

    *spec* is a dict where:
      - "dirs": {name: sub_spec} creates subdirectories
      - "files": {name: content} creates files with string content
    """
    for name, sub in spec.get("dirs", {}).items():
        d = os.path.join(root, name)
        os.makedirs(d, exist_ok=True)
        build_tree(d, sub)
    for name, content in spec.get("files", {}).items():
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if isinstance(content, bytes):
            with open(path, "wb") as f:
                f.write(content)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_tree(tmp_path):
    """A small tree with 3 dirs and 5 text files."""
    spec = {
        "dirs": {
            "docs": {
                "files": {
                    "readme.md": "# Project\nHello world.\n",
                    "changelog.md": "## v1.0\nFirst release.\n",
                }
            },
            "config": {
                "files": {
                    "settings.json": '{"port": 8080}\n',
                    "users.csv": "id,name\n1,alice\n2,bob\n",
                }
            },
            "images": {
                "files": {
                    "logo.txt": "FAKE PNG DATA\n",
                }
            },
        }
    }
    build_tree(str(tmp_path), spec)
    return tmp_path


@pytest.fixture
def flat_tree(tmp_path):
    """A flat directory with 20 small text files."""
    for i in range(20):
        (tmp_path / f"file_{i:04d}.txt").write_text(
            f"content of file {i}\nline 2\n", encoding="utf-8"
        )
    return tmp_path


@pytest.fixture
def binary_tree(tmp_path):
    """A tree with binary files of varying sizes."""
    import random
    rng = random.Random(42)
    os.makedirs(str(tmp_path / "bin"), exist_ok=True)
    sizes = [0, 1, 1024, 65536, 131072]
    for idx, size in enumerate(sizes):
        data = bytes(rng.getrandbits(8) for _ in range(size))
        (tmp_path / "bin" / f"data_{idx}_{size}.bin").write_bytes(data)
    return tmp_path


@pytest.fixture
def empty_tree(tmp_path):
    """An empty directory."""
    return tmp_path


@pytest.fixture
def deep_tree(tmp_path):
    """A deeply nested directory tree: 5 levels, 2 files per level."""
    root = str(tmp_path)
    current = root
    for level in range(5):
        current = os.path.join(current, f"level_{level}")
        os.makedirs(current, exist_ok=True)
        for fnum in range(2):
            path = os.path.join(current, f"file_{fnum}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"level {level} file {fnum}\n")
    return tmp_path


@pytest.fixture
def unicode_tree(tmp_path):
    """A tree with unicode filenames and content."""
    spec = {
        "dirs": {
            "data": {
                "files": {
                    "resume.md": "Cafe & naive\n",
                    "emoji_1.txt": "party!\n",
                }
            },
        }
    }
    build_tree(str(tmp_path), spec)
    return tmp_path


@pytest.fixture
def skipped_names_tree(tmp_path):
    """A tree containing files/dirs that should be skipped."""
    spec = {
        "dirs": {
            ".backup": {"files": {"meta.json": "{}"}},
            ".git": {"files": {"config": "[core]\n"}},
            "__pycache__": {"files": {"module.cpython-313.pyc": b"\x00\x00"}},
            "real_data": {"files": {"important.txt": "keep me\n"}},
        },
        "files": {
            ".DS_Store": "junk",
            "Thumbs.db": b"\x00\x01",
            "normal.txt": "hello\n",
        }
    }
    build_tree(str(tmp_path), spec)
    return tmp_path

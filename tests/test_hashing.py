"""Tests for distbackup.core.hashing — hash_file, hash_bytes."""

import os
import pytest
from distbackup.core.hashing import hash_file, hash_bytes, CHUNK_SIZE


class TestHashBytes:
    def test_empty_bytes(self):
        digest = hash_bytes(b"")
        assert len(digest) == 64
        assert digest == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_ascii_bytes(self):
        assert hash_bytes(b"hello") == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_binary_bytes(self):
        data = bytes(range(256))
        digest = hash_bytes(data)
        assert len(digest) == 64

    def test_deterministic(self):
        data = b"deterministic test data\n" * 100
        d1 = hash_bytes(data)
        d2 = hash_bytes(data)
        assert d1 == d2

    def test_distinct(self):
        d1 = hash_bytes(b"alpha")
        d2 = hash_bytes(b"beta")
        assert d1 != d2


class TestHashFile:
    def test_small_text_file(self, sample_tree):
        path = os.path.join(str(sample_tree), "docs", "readme.md")
        digest = hash_file(path)
        assert len(digest) == 64
        assert digest == hash_file(path)

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.txt"
        p.write_text("")
        digest = hash_file(str(p))
        assert digest == hash_bytes(b"")

    def test_binary_file(self, binary_tree):
        path = os.path.join(str(binary_tree), "bin", "data_4_131072.bin")
        digest = hash_file(path)
        assert len(digest) == 64

    def test_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            hash_file(str(tmp_path / "does_not_exist.txt"))

    def test_matches_hash_bytes(self, tmp_path):
        content = b"matching test\n" * 50
        p = tmp_path / "match.txt"
        p.write_bytes(content)
        assert hash_file(str(p)) == hash_bytes(content)

    def test_large_file(self, tmp_path):
        size = CHUNK_SIZE * 3 + 100
        p = tmp_path / "large.bin"
        with open(str(p), "wb") as f:
            f.write(b"A" * size)
        digest = hash_file(str(p))
        assert len(digest) == 64

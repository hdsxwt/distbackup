"""Tests for distbackup.core.scanner — Scanner.scan."""

import os
import pytest
from distbackup.core.scanner import Scanner, SKIP_NAMES
from distbackup.core.hashing import hash_file


class TestScanner:
    def test_scan_normal_tree(self, sample_tree):
        result = Scanner.scan(str(sample_tree))
        assert len(result) == 5
        for rel in result:
            assert "\\" not in rel or os.sep == "\\"

    def test_scan_returns_relative_paths(self, sample_tree):
        result = Scanner.scan(str(sample_tree))
        root = str(sample_tree)
        for rel in result:
            full = os.path.join(root, rel)
            assert os.path.isfile(full)

    def test_scan_empty_directory(self, empty_tree):
        result = Scanner.scan(str(empty_tree))
        assert result == {}

    def test_scan_flat_directory(self, flat_tree):
        result = Scanner.scan(str(flat_tree))
        assert len(result) == 20

    def test_scan_deep_tree(self, deep_tree):
        result = Scanner.scan(str(deep_tree))
        assert len(result) == 10

    def test_scan_binary_files(self, binary_tree):
        result = Scanner.scan(str(binary_tree))
        assert len(result) == 5
        for rel, digest in result.items():
            full = os.path.join(str(binary_tree), rel)
            assert digest == hash_file(full)

    def test_skip_names_excluded(self, skipped_names_tree):
        result = Scanner.scan(str(skipped_names_tree))
        for rel in result:
            assert ".backup" not in rel.split(os.sep)
            assert ".git" not in rel.split(os.sep)
            assert "__pycache__" not in rel.split(os.sep)
        assert any(k == "normal.txt" or k.endswith(f"{os.sep}normal.txt") for k in result)
        assert any(k == "important.txt" or k.endswith(f"{os.sep}important.txt") for k in result)

    def test_hidden_directories_not_descended(self, skipped_names_tree):
        result = Scanner.scan(str(skipped_names_tree))
        for rel in result:
            assert ".backup" not in rel
            assert ".git" not in rel
            assert "__pycache__" not in rel

    def test_root_files_excluded(self, skipped_names_tree):
        result = Scanner.scan(str(skipped_names_tree))
        assert ".DS_Store" not in result
        assert "Thumbs.db" not in result

    def test_hashes_are_correct(self, sample_tree):
        result = Scanner.scan(str(sample_tree))
        for rel, digest in result.items():
            full = os.path.join(str(sample_tree), rel)
            assert hash_file(full) == digest

    def test_no_directory_keys_in_result(self, sample_tree):
        result = Scanner.scan(str(sample_tree))
        root = str(sample_tree)
        for rel in result:
            assert os.path.isfile(os.path.join(root, rel))

    def test_skip_names_is_set(self):
        assert ".backup" in SKIP_NAMES
        assert ".git" in SKIP_NAMES
        assert "__pycache__" in SKIP_NAMES

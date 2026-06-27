"""Tests for distbackup.core.differ — Differ.compare, DiffResult."""

import pytest
from distbackup.core.differ import Differ, DiffResult


class TestDiffResult:
    def test_total_changes_counts_added_and_modified(self):
        dr = DiffResult(added=["a"], modified=["b"], removed=["c"], unchanged=["d"])
        assert dr.total_changes == 2

    def test_total_changes_zero_when_only_removed_and_unchanged(self):
        dr = DiffResult(removed=["a"], unchanged=["b", "c"])
        assert dr.total_changes == 0


class TestDifferCompare:
    def test_both_empty(self):
        r = Differ.compare({}, {})
        assert r.added == []
        assert r.modified == []
        assert r.removed == []
        assert r.unchanged == []

    def test_added(self):
        r = Differ.compare({"a.txt": "h1"}, {})
        assert r.added == ["a.txt"]
        assert r.modified == []

    def test_removed(self):
        r = Differ.compare({}, {"a.txt": "h1"})
        assert r.removed == ["a.txt"]
        assert r.added == []

    def test_modified(self):
        r = Differ.compare({"a.txt": "h1"}, {"a.txt": "h2"})
        assert r.modified == ["a.txt"]

    def test_unchanged(self):
        r = Differ.compare({"a.txt": "h1"}, {"a.txt": "h1"})
        assert r.unchanged == ["a.txt"]

    def test_mixed(self):
        src = {"a.txt": "h1", "b.txt": "hb", "c.txt": "hc"}
        tgt = {"b.txt": "hb_new", "d.txt": "hd"}
        r = Differ.compare(src, tgt)
        assert sorted(r.added) == ["a.txt", "c.txt"]
        assert r.modified == ["b.txt"]
        assert r.removed == ["d.txt"]

    def test_results_are_sorted(self):
        src = {f"{i:04d}.txt": "h" for i in range(50)}
        r = Differ.compare(src, {})
        assert r.added == sorted(r.added)

    def test_large_manifest(self):
        size = 2000
        src = {f"file_{i:06d}.txt": f"hash_{i}" for i in range(size)}
        tgt = dict(src)
        del tgt["file_000500.txt"]
        tgt["file_000000.txt"] = "changed"
        tgt["file_extra.txt"] = "extra"
        r = Differ.compare(src, tgt)
        assert r.added == ["file_000500.txt"]
        assert r.modified == ["file_000000.txt"]
        assert r.removed == ["file_extra.txt"]
        assert len(r.unchanged) == size - 2

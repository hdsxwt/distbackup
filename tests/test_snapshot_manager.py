"""Tests for distbackup.core.snapshot_manager — SnapshotManager."""

import json
import os
import pytest
from distbackup.core.snapshot_manager import SnapshotManager


class TestSnapshotManager:
    def test_save_and_load_roundtrip(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        files = {"a.txt": "abc123", "sub/b.txt": "def456"}
        mgr.save("snap1", files, str(tmp_path))
        loaded = mgr.load("snap1")
        assert loaded["files"] == files
        assert loaded["root"] == os.path.abspath(str(tmp_path))
        assert "created" in loaded

    def test_created_is_iso_utc(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        mgr.save("snap1", {"x": "h"}, str(tmp_path))
        loaded = mgr.load("snap1")
        created = loaded["created"]
        assert "T" in created or "+" in created
        from datetime import datetime
        datetime.fromisoformat(created)

    def test_list_snapshots_sorted(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        mgr.save("ccc", {}, str(tmp_path))
        mgr.save("aaa", {}, str(tmp_path))
        mgr.save("bbb", {}, str(tmp_path))
        names = mgr.list_snapshots()
        assert names == ["aaa", "bbb", "ccc"]

    def test_list_empty(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        assert mgr.list_snapshots() == []

    def test_load_nonexistent_raises(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            mgr.load("nope")

    def test_backup_dir_created(self, tmp_path):
        assert not os.path.isdir(os.path.join(str(tmp_path), ".backup"))
        SnapshotManager(str(tmp_path))
        assert os.path.isdir(os.path.join(str(tmp_path), ".backup"))
        assert os.path.isdir(os.path.join(str(tmp_path), ".backup", "snapshots"))

    def test_path_escaping(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        mgr.save("a/b/c", {}, str(tmp_path))
        names = mgr.list_snapshots()
        assert "a_b_c" in names

    def test_multiple_snapshots_independent(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        mgr.save("one", {"f": "h1"}, str(tmp_path))
        mgr.save("two", {"f": "h2"}, str(tmp_path))
        assert mgr.load("one")["files"] == {"f": "h1"}
        assert mgr.load("two")["files"] == {"f": "h2"}

    def test_save_returns_path(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        path = mgr.save("test", {}, str(tmp_path))
        assert os.path.isfile(path)
        assert path.endswith("test.json")

    def test_corrupted_json_raises(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        snap_dir = os.path.join(str(tmp_path), ".backup", "snapshots")
        with open(os.path.join(snap_dir, "bad.json"), "w") as f:
            f.write("not valid json {{{")
        with pytest.raises(ValueError):
            mgr.load("bad")

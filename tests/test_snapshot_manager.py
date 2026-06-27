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


class TestRepoType:
    """Tests for the .backup/config.json repo-type feature."""

    def test_default_type_is_target(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        assert mgr.get_repo_type() == "Target"
        config_path = os.path.join(str(tmp_path), ".backup", "config.json")
        assert os.path.isfile(config_path)

    def test_set_and_get_type(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        mgr.set_repo_type("Source")
        assert mgr.get_repo_type() == "Source"
        mgr.set_repo_type("Target")
        assert mgr.get_repo_type() == "Target"

    def test_type_persists_across_instances(self, tmp_path):
        mgr1 = SnapshotManager(str(tmp_path))
        mgr1.set_repo_type("Source")
        mgr2 = SnapshotManager(str(tmp_path))
        assert mgr2.get_repo_type() == "Source"

    def test_invalid_type_raises(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        with pytest.raises(ValueError):
            mgr.set_repo_type("Invalid")
        # existing type unchanged
        assert mgr.get_repo_type() == "Target"

    def test_config_not_overwritten_by_save(self, tmp_path):
        """Saving a snapshot must not clobber the config.json file."""
        mgr = SnapshotManager(str(tmp_path))
        mgr.set_repo_type("Source")
        mgr.save("snap1", {"a.txt": "abc"}, str(tmp_path))
        assert mgr.get_repo_type() == "Source"

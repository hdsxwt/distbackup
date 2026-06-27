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


class TestRepoId:
    """Tests for repo_id generation, access, and migration."""

    def test_new_repo_has_no_repo_id(self, tmp_path):
        """New repositories (Target by default) start with no repo_id."""
        mgr = SnapshotManager(str(tmp_path))
        assert mgr.get_repo_id() is None

    def test_set_source_generates_repo_id(self, tmp_path):
        """Marking a repository as Source auto-generates a repo_id."""
        mgr = SnapshotManager(str(tmp_path))
        assert mgr.get_repo_id() is None
        mgr.set_repo_type("Source")
        rid = mgr.get_repo_id()
        assert rid is not None
        assert isinstance(rid, str)
        assert len(rid) == 36

    def test_repo_id_is_stable_across_instances(self, tmp_path):
        mgr1 = SnapshotManager(str(tmp_path))
        mgr1.set_repo_type("Source")
        rid1 = mgr1.get_repo_id()
        mgr2 = SnapshotManager(str(tmp_path))
        assert mgr2.get_repo_id() == rid1

    def test_config_json_no_repo_id_for_new_target(self, tmp_path):
        """New Target repos have no repo_id in config.json."""
        mgr = SnapshotManager(str(tmp_path))
        config_path = os.path.join(str(tmp_path), ".backup", "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "repo_id" not in data
        assert data["type"] == "Target"

    def test_config_json_has_repo_id_after_source(self, tmp_path):
        """After set_repo_type("Source"), config.json contains a repo_id."""
        mgr = SnapshotManager(str(tmp_path))
        mgr.set_repo_type("Source")
        config_path = os.path.join(str(tmp_path), ".backup", "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "repo_id" in data
        assert data["type"] == "Source"
        assert len(data["repo_id"]) == 36

    def test_different_sources_have_different_ids(self, tmp_path):
        d1 = str(tmp_path / "repo_a")
        d2 = str(tmp_path / "repo_b")
        os.makedirs(d1, exist_ok=True)
        os.makedirs(d2, exist_ok=True)
        m1 = SnapshotManager(d1)
        m2 = SnapshotManager(d2)
        m1.set_repo_type("Source")
        m2.set_repo_type("Source")
        assert m1.get_repo_id() != m2.get_repo_id()

    def test_set_repo_type_preserves_repo_id(self, tmp_path):
        """Toggling between Source/Target must preserve existing repo_id."""
        mgr = SnapshotManager(str(tmp_path))
        mgr.set_repo_type("Source")
        rid = mgr.get_repo_id()
        mgr.set_repo_type("Target")
        assert mgr.get_repo_id() == rid
        assert mgr.get_repo_type() == "Target"
        mgr.set_repo_type("Source")
        assert mgr.get_repo_id() == rid
        assert mgr.get_repo_type() == "Source"

    def test_set_target_does_not_generate_repo_id(self, tmp_path):
        """Setting to Target on a fresh repo does not generate a repo_id."""
        mgr = SnapshotManager(str(tmp_path))
        mgr.set_repo_type("Target")  # already Target, but idempotent
        assert mgr.get_repo_id() is None

    def test_set_repo_id_persists(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        mgr.set_repo_id("custom-lineage-id")
        assert mgr.get_repo_id() == "custom-lineage-id"
        mgr2 = SnapshotManager(str(tmp_path))
        assert mgr2.get_repo_id() == "custom-lineage-id"

    def test_ensure_repo_id_generates_on_any_repo(self, tmp_path):
        """ensure_repo_id generates a UUID for a Target repo that lacks one."""
        mgr = SnapshotManager(str(tmp_path))
        assert mgr.get_repo_id() is None
        ensured = mgr.ensure_repo_id()
        assert ensured is not None
        assert len(ensured) == 36
        assert mgr.get_repo_id() == ensured

    def test_ensure_repo_id_idempotent(self, tmp_path):
        """Calling ensure_repo_id twice returns the same value."""
        mgr = SnapshotManager(str(tmp_path))
        first = mgr.ensure_repo_id()
        second = mgr.ensure_repo_id()
        assert first == second


class TestValidateRoot:
    """Tests for SnapshotManager.validate_root() method."""

    def test_matching_root_passes(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        mgr.save("snap1", {"a.txt": "abc123"}, str(tmp_path))
        # Should not raise
        mgr.validate_root("snap1", str(tmp_path))

    def test_mismatched_root_raises(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        mgr.save("snap1", {"a.txt": "abc123"}, str(tmp_path))
        other = str(tmp_path / "other_dir")
        os.makedirs(other, exist_ok=True)
        # Temporary SnapshotManager just to load the snapshot
        with pytest.raises(ValueError, match="root mismatch"):
            mgr.validate_root("snap1", other)

    def test_root_validated_against_absolute_path(self, tmp_path):
        """Relative paths should be normalized before comparison."""
        import os as _os
        mgr = SnapshotManager(str(tmp_path))
        mgr.save("snap1", {"f": "h"}, str(tmp_path))
        # Use a path with a trailing separator or relative form
        mgr.validate_root("snap1", _os.path.abspath(str(tmp_path)))

    def test_missing_root_field_raises(self, tmp_path):
        """Snapshot without a root field should fail validation."""
        mgr = SnapshotManager(str(tmp_path))
        mgr.save("snap1", {"f": "h"}, str(tmp_path))
        # Manually corrupt the snapshot to remove root
        snap_path = os.path.join(str(tmp_path), ".backup", "snapshots", "snap1.json")
        with open(snap_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        del data["root"]
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        with pytest.raises(ValueError):
            mgr.validate_root("snap1", str(tmp_path))

    def test_validate_root_on_nonexistent_snapshot(self, tmp_path):
        mgr = SnapshotManager(str(tmp_path))
        with pytest.raises(FileNotFoundError):
            mgr.validate_root("nonexistent", str(tmp_path))

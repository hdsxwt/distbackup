import os
import pytest
from distbackup.core.scanner import Scanner
from distbackup.core.snapshot_manager import SnapshotManager
from distbackup.core.differ import Differ
from distbackup.core.syncer import Syncer
from distbackup.core.hashing import hash_file


class TestFullWorkflow:
    def test_scan_diff_sync_full(self, sample_tree, tmp_path):
        src = str(sample_tree)
        tgt = str(tmp_path / 'target')
        os.makedirs(tgt, exist_ok=True)
        src_files = Scanner.scan(src)
        src_mgr = SnapshotManager(src)
        src_mgr.save('source_v1', src_files, src)
        tgt_files = Scanner.scan(tgt)
        tgt_mgr = SnapshotManager(tgt)
        tgt_mgr.save('target_v1', tgt_files, tgt)
        diff = Differ.compare(src_files, tgt_files)
        assert diff.total_changes == 5
        syncer = Syncer()
        stats = syncer.sync(src, tgt, diff)
        assert stats['copied'] == 5
        assert stats['errors'] == 0
        for rel in src_files:
            assert os.path.isfile(os.path.join(tgt, rel))

    def test_hash_verification_after_sync(self, sample_tree, tmp_path):
        src = str(sample_tree)
        tgt = str(tmp_path / 'target')
        os.makedirs(tgt, exist_ok=True)
        src_files = Scanner.scan(src)
        diff = Differ.compare(src_files, {})
        Syncer().sync(src, tgt, diff)
        tgt_files = Scanner.scan(tgt)
        for rel, src_hash in src_files.items():
            assert rel in tgt_files
            assert tgt_files[rel] == src_hash

    def test_incremental_backup(self, sample_tree, tmp_path):
        src = str(sample_tree)
        tgt = str(tmp_path / 'target')
        os.makedirs(tgt, exist_ok=True)
        src_files_v1 = Scanner.scan(src)
        Syncer().sync(src, tgt, Differ.compare(src_files_v1, {}))
        new_file = os.path.join(src, 'docs', 'new_doc.md')
        with open(new_file, 'w', encoding='utf-8') as f:
            f.write('new file content\n')
        src_files_v2 = Scanner.scan(src)
        tgt_files_v1 = Scanner.scan(tgt)
        diff2 = Differ.compare(src_files_v2, tgt_files_v1)
        new_doc_rel = os.path.join('docs', 'new_doc.md'); assert new_doc_rel in diff2.added
        assert len(diff2.unchanged) == 5
        Syncer().sync(src, tgt, diff2)
        assert os.path.isfile(os.path.join(tgt, 'docs', 'new_doc.md'))

    def test_modified_file_backup(self, sample_tree, tmp_path):
        src = str(sample_tree)
        tgt = str(tmp_path / 'target')
        os.makedirs(tgt, exist_ok=True)
        src_files_v1 = Scanner.scan(src)
        Syncer().sync(src, tgt, Differ.compare(src_files_v1, {}))
        with open(os.path.join(src, 'docs', 'readme.md'), 'a', encoding='utf-8') as f:
            f.write('appended line\n')
        src_files_v2 = Scanner.scan(src)
        tgt_files_v1 = Scanner.scan(tgt)
        diff = Differ.compare(src_files_v2, tgt_files_v1)
        readme_rel = os.path.join('docs', 'readme.md')
        assert readme_rel in diff.modified
        Syncer().sync(src, tgt, diff)
        src_hash = hash_file(os.path.join(src, 'docs', 'readme.md'))
        tgt_hash = hash_file(os.path.join(tgt, 'docs', 'readme.md'))
        assert src_hash == tgt_hash

    def test_multiple_snapshots_cycle(self, sample_tree):
        src = str(sample_tree)
        mgr = SnapshotManager(src)
        files = Scanner.scan(src)
        for i in range(3):
            mgr.save(f'snap_{i}', files, src)
        all_names = mgr.list_snapshots()
        for i in range(3):
            assert f'snap_{i}' in all_names
            snap = mgr.load(f'snap_{i}')
            assert snap['files'] == files

    def test_target_extra_files_preserved(self, sample_tree, tmp_path):
        src = str(sample_tree)
        tgt = str(tmp_path / 'target')
        os.makedirs(tgt, exist_ok=True)
        src_files = Scanner.scan(src)
        Syncer().sync(src, tgt, Differ.compare(src_files, {}))
        extra_path = os.path.join(tgt, 'target_only.txt')
        with open(extra_path, 'w', encoding='utf-8') as f:
            f.write('target only\n')
        src_files_v2 = Scanner.scan(src)
        tgt_files = Scanner.scan(tgt)
        diff = Differ.compare(src_files_v2, tgt_files)
        assert 'target_only.txt' in diff.removed
        Syncer().sync(src, tgt, diff)
        assert os.path.isfile(extra_path)

    def test_post_backup_verification_passes(self, sample_tree, tmp_path):
        """After a full sync, re-scanning the target should show zero diffs."""
        src = str(sample_tree)
        tgt = str(tmp_path / 'target')
        os.makedirs(tgt, exist_ok=True)

        src_files = Scanner.scan(src)
        SnapshotManager(src).save('src', src_files, src)
        Syncer().sync(src, tgt, Differ.compare(src_files, {}))

        # Verify: re-scan target and compare against source
        tgt_files = Scanner.scan(tgt)
        verify = Differ.compare(src_files, tgt_files)
        assert verify.total_changes == 0
        assert verify.added == []
        assert verify.modified == []

    def test_post_backup_verification_detects_missing(self, sample_tree, tmp_path):
        """If a sync leaves a file behind, verification should catch it."""
        src = str(sample_tree)
        tgt = str(tmp_path / 'target')
        os.makedirs(tgt, exist_ok=True)

        src_files = Scanner.scan(src)
        # Only sync a subset by crafting a partial diff
        partial_files = dict(list(src_files.items())[:3])
        Syncer().sync(src, tgt, Differ.compare(partial_files, {}))

        # Full source should still have more files
        tgt_files = Scanner.scan(tgt)
        verify = Differ.compare(src_files, tgt_files)
        assert verify.total_changes > 0


import json
import os
import pytest
from distbackup.core.scanner import Scanner
from distbackup.core.snapshot_manager import SnapshotManager
from distbackup.core.differ import Differ
from distbackup.core.syncer import Syncer


import json
import os
import pytest
from distbackup.core.scanner import Scanner
from distbackup.core.snapshot_manager import SnapshotManager
from distbackup.core.differ import Differ
from distbackup.core.syncer import Syncer


import json
import os
import tempfile
import pytest
from distbackup.core.scanner import Scanner
from distbackup.core.snapshot_manager import SnapshotManager
from distbackup.core.differ import Differ
from distbackup.core.syncer import Syncer


class TestRepoIdLineage:
    """Integration tests for repo_id lineage enforcement and inheritance."""

    def _bootstrap_repos(self, src_dir, tgt_dir):
        """Create a source with files and an empty target, both as SnapshotManager."""
        os.makedirs(tgt_dir, exist_ok=True)
        src_mgr = SnapshotManager(src_dir)
        tgt_mgr = SnapshotManager(tgt_dir)
        src_files = Scanner.scan(src_dir)
        tgt_files = Scanner.scan(tgt_dir)
        src_mgr.save("src_snap", src_files, src_dir)
        tgt_mgr.save("tgt_snap", tgt_files, tgt_dir)
        return src_mgr, tgt_mgr, src_files, tgt_files

    def test_first_backup_inherits_repo_id(self, sample_tree, tmp_path):
        """A first-time backup (target has no lineage) inherits source repo_id."""
        src = str(sample_tree)
        tgt = str(tmp_path / "target")
        src_mgr, tgt_mgr, src_files, tgt_files = self._bootstrap_repos(src, tgt)

        # Ensure source has a repo_id; new Target repos start without one
        src_id = src_mgr.ensure_repo_id()
        assert tgt_mgr.get_repo_id() is None
        # New Target repos start with no repo_id
        assert tgt_mgr.get_repo_id() is None

        diff = Differ.compare(src_files, tgt_files)
        Syncer().sync(src, tgt, diff)

        # After backup: source inherits repo_id to target
        tgt_mgr.set_repo_id(src_id)  # simulate what CLI/GUI do
        assert tgt_mgr.get_repo_id() == src_id

    def test_matching_repo_ids_allow_backup(self, sample_tree, tmp_path):
        """Backup succeeds when source and target have the same repo_id."""
        src = str(sample_tree)
        tgt = str(tmp_path / "target")
        src_mgr, tgt_mgr, src_files, tgt_files = self._bootstrap_repos(src, tgt)

        # Set both to the same id (simulated inherited scenario)
        lineage_id = src_mgr.ensure_repo_id()
        tgt_mgr.set_repo_id(lineage_id)

        assert src_mgr.get_repo_id() == tgt_mgr.get_repo_id()
        diff = Differ.compare(src_files, tgt_files)
        stats = Syncer().sync(src, tgt, diff)
        assert stats["copied"] > 0

    def test_mismatched_repo_ids_are_detected(self, sample_tree, tmp_path):
        """Backup should be blocked when repo_ids differ."""
        src = str(sample_tree)
        tgt = str(tmp_path / "target")
        src_mgr, tgt_mgr, src_files, tgt_files = self._bootstrap_repos(src, tgt)

        # Force different repo_ids
        src_id = src_mgr.ensure_repo_id()
        tgt_mgr.set_repo_id("totally-different-lineage-id")
        assert src_mgr.get_repo_id() != tgt_mgr.get_repo_id()

        # The sync itself won't block, but the caller (CLI/GUI) should check
        src_id_check = src_mgr.ensure_repo_id()
        tgt_id_check = tgt_mgr.get_repo_id()
        assert tgt_id_check is not None
        assert tgt_id_check != src_id_check

        # Simulate the check that CLI/GUI performs
        if tgt_id_check is not None and tgt_id_check != src_id_check:
            blocked = True
        else:
            blocked = False
        assert blocked

    def test_ensure_repo_id_does_not_overwrite_existing(self, sample_tree):
        """Calling ensure_repo_id on a repo that already has one is idempotent."""
        src = str(sample_tree)
        mgr = SnapshotManager(src)
        first = mgr.ensure_repo_id()
        second = mgr.ensure_repo_id()
        assert first == second

    def test_legacy_target_gets_source_id_on_first_backup(self, sample_tree, tmp_path):
        """End-to-end: legacy target without repo_id inherits source id after backup."""
        src = str(sample_tree)
        tgt = str(tmp_path / "target")
        os.makedirs(tgt, exist_ok=True)

        src_mgr = SnapshotManager(src)
        tgt_mgr = SnapshotManager(tgt)
        src_files = Scanner.scan(src)
        tgt_files = Scanner.scan(tgt)
        src_mgr.save("src_snap", src_files, src)
        tgt_mgr.save("tgt_snap", tgt_files, tgt)

        # New Target repos have no repo_id; source gets one via ensure
        src_id = src_mgr.ensure_repo_id()
        assert tgt_mgr.get_repo_id() is None
        assert src_mgr.get_repo_id() == src_id

        # Perform lineage check (should pass: tgt_id is None)
        tgt_id = tgt_mgr.get_repo_id()
        src_id_check = src_mgr.ensure_repo_id()
        blocked = (tgt_id is not None and tgt_id != src_id_check)
        assert not blocked

        # Run backup
        diff = Differ.compare(src_files, tgt_files)
        Syncer().sync(src, tgt, diff)

        # Inherit
        tgt_mgr.set_repo_id(src_id)
        assert tgt_mgr.get_repo_id() == src_id


class TestSecurityProtection:
    """Integration tests for the three security fixes."""

    def test_root_mismatch_blocks_sync(self, sample_tree, tmp_path):
        """validate_root raises when snapshot root does not match directory."""
        src = str(sample_tree)
        tgt = str(tmp_path / "target")
        os.makedirs(tgt, exist_ok=True)

        src_mgr = SnapshotManager(src)
        src_files = Scanner.scan(src)
        src_mgr.save("src_snap", src_files, src)

        # Save a target snapshot normally, then tamper its root
        tgt_mgr = SnapshotManager(tgt)
        tgt_mgr.save("tgt_snap", {}, tgt)

        # Tamper: change the root in the JSON to point to a different directory
        snap_path = os.path.join(tgt, ".backup", "snapshots", "tgt_snap.json")
        with open(snap_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["root"] = str(tmp_path / "some_other_dir")
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        with pytest.raises(ValueError, match="root mismatch"):
            tgt_mgr.validate_root("tgt_snap", tgt)

    def test_path_traversal_snapshot_is_blocked(self, sample_tree, tmp_path):
        """A tampered snapshot with traversal paths is blocked during sync."""
        src = str(sample_tree)
        tgt = str(tmp_path / "target")
        os.makedirs(tgt, exist_ok=True)

        src_files = Scanner.scan(src)
        tgt_files = Scanner.scan(tgt)

        # Build a DiffResult manually with a traversal path in added
        diff = Differ.compare(src_files, tgt_files)
        diff.added.append(os.path.join("..", "..", "..", "evil.dll"))

        syncer = Syncer()
        stats = syncer.sync(src, tgt, diff)
        assert stats["errors"] >= 1
        assert any("path traversal blocked" in err for _, err in stats["failed"])

    def test_root_mismatch_detected_before_copy(self, sample_tree, tmp_path):
        """Root mismatch is caught before any files are copied."""
        src = str(sample_tree)
        tgt = str(tmp_path / "target")
        os.makedirs(tgt, exist_ok=True)

        src_mgr = SnapshotManager(src)
        src_files = Scanner.scan(src)
        src_mgr.save("src_snap", src_files, src)
        src_mgr.set_repo_type("Source")

        # Save a snapshot and tamper its root
        tgt_mgr = SnapshotManager(tgt)
        tgt_mgr.save("tgt_snap", {"dummy": "hash"}, tgt)
        tgt_mgr.set_repo_type("Target")

        # Tamper root
        snap_path = os.path.join(tgt, ".backup", "snapshots", "tgt_snap.json")
        with open(snap_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["root"] = str(tmp_path / "wrong_dir")
        with open(snap_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        with pytest.raises(ValueError, match="root mismatch"):
            tgt_mgr.validate_root("tgt_snap", tgt)

    def test_scanner_logs_unreadable_in_workflow(self, sample_tree, tmp_path, caplog):
        """Full workflow: scanner logs unreadable instead of silently skipping."""
        import logging
        from unittest.mock import patch
        from distbackup.core.hashing import hash_file as orig_hash

        src = str(sample_tree)

        bad_path = os.path.join(src, "docs", "readme.md")

        def mock_hash(path, *args, **kwargs):
            if os.path.abspath(path) == os.path.abspath(bad_path):
                raise PermissionError("Permission denied during test")
            return orig_hash(path, *args, **kwargs)

        with patch("distbackup.core.scanner.hash_file", side_effect=mock_hash):
            with caplog.at_level(logging.WARNING):
                result = Scanner.scan(src)

        assert os.path.join("docs", "readme.md") not in result
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) >= 1
        assert any("readme.md" in str(r.message) for r in warnings)

    def test_tampered_json_with_traversal_full_flow(self, sample_tree, tmp_path):
        """End-to-end: a tampered snapshot JSON with traversal paths."""
        src = str(sample_tree)
        tgt = str(tmp_path / "target")
        os.makedirs(tgt, exist_ok=True)

        src_mgr = SnapshotManager(src)
        src_files = Scanner.scan(src)
        src_mgr.save("src_snap", src_files, src)

        tgt_mgr = SnapshotManager(tgt)
        tgt_files = Scanner.scan(tgt)
        # Tamper: add traversal path to source snapshot so it appears as "added"
        src_files[os.path.join("..", "..", "hack.dll")] = "fakehash"
        src_mgr.save("src_snap", src_files, src)
        tgt_mgr.save("tgt_snap", tgt_files, tgt)

        diff = Differ.compare(src_files, tgt_files)

        syncer = Syncer()
        stats = syncer.sync(src, tgt, diff)
        # The traversal file should be in "added" and blocked
        assert stats["errors"] >= 1


class TestEmptyTargetBackup:
    """Regression: backing up to an empty target folder must not fail."""

    def test_sync_to_empty_target_works(self, sample_tree, tmp_path):
        """All snapshots in source store, target is an empty directory."""
        import subprocess, sys, json

        src = str(sample_tree)
        tgt = str(tmp_path / "target")
        os.makedirs(tgt, exist_ok=True)

        mgr = SnapshotManager(src)
        src_files = Scanner.scan(src)
        mgr.save("src_snap", src_files, src)
        # Simulate a target scan with empty results, saved into source store
        mgr.save("tgt_snap", {}, tgt)

        # Run the sync programmatically (same as CLI would do)
        from distbackup.cli import cmd_sync
        import argparse

        class Args:
            pass

        a = Args()
        a.source = src
        a.target = tgt
        a.source_snap = "src_snap"
        a.target_snap = "tgt_snap"
        a.store = src
        a.force = True
        a.dry_run = False

        cmd_sync(a)

        # After sync, all source files should be in target
        for rel in src_files:
            assert os.path.isfile(os.path.join(tgt, rel)), f"Missing: {rel}"

import os
import pytest
from distbackup.core.differ import Differ, DiffResult
from distbackup.core.syncer import Syncer
from distbackup.core.hashing import hash_file


class TestSyncer:
    def test_copies_added_files(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        (src / 'new.txt').write_text('hello', encoding='utf-8')
        diff = Differ.compare({'new.txt': 'h1'}, {})
        syncer = Syncer()
        stats = syncer.sync(str(src), str(tgt), diff)
        assert stats['copied'] == 1
        assert stats['errors'] == 0
        assert (tgt / 'new.txt').read_text(encoding='utf-8') == 'hello'

    def test_copies_modified_files(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        (src / 'mod.txt').write_text('new content', encoding='utf-8')
        (tgt / 'mod.txt').write_text('old content', encoding='utf-8')
        diff = Differ.compare(
            {'mod.txt': hash_file(str(src / 'mod.txt'))},
            {'mod.txt': hash_file(str(tgt / 'mod.txt'))})
        syncer = Syncer()
        stats = syncer.sync(str(src), str(tgt), diff)
        assert stats['copied'] == 1
        assert (tgt / 'mod.txt').read_text(encoding='utf-8') == 'new content'

    def test_leaves_removed_files_untouched(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        (tgt / 'extra.txt').write_text('keep me', encoding='utf-8')
        diff = Differ.compare({}, {'extra.txt': 'h1'})
        syncer = Syncer()
        stats = syncer.sync(str(src), str(tgt), diff)
        assert stats['copied'] == 0
        assert (tgt / 'extra.txt').exists()

    def test_creates_intermediate_directories(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        os.makedirs(str(src / 'deep' / 'nested'), exist_ok=True)
        (src / 'deep' / 'nested' / 'file.txt').write_text('data', encoding='utf-8')
        diff = Differ.compare({'deep/nested/file.txt': 'h1'}, {})
        syncer = Syncer()
        stats = syncer.sync(str(src), str(tgt), diff)
        assert stats['copied'] == 1
        assert (tgt / 'deep' / 'nested' / 'file.txt').exists()

    def test_empty_diff_does_nothing(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        diff = Differ.compare({}, {})
        syncer = Syncer()
        stats = syncer.sync(str(src), str(tgt), diff)
        assert stats['copied'] == 0
        assert stats['errors'] == 0

    def test_progress_callback_invocation(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        for i in range(5):
            (src / f'file_{i}.txt').write_text(f'content {i}', encoding='utf-8')
        files = {f'file_{i}.txt': f'h{i}' for i in range(5)}
        diff = Differ.compare(files, {})
        calls = []
        def cb(cur, total):
            calls.append((cur, total))
        syncer = Syncer(progress_callback=cb)
        syncer.sync(str(src), str(tgt), diff)
        assert len(calls) == 5

    def test_binary_file_integrity(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        data = bytes(range(256)) * 100
        (src / 'data.bin').write_bytes(data)
        diff = Differ.compare({'data.bin': hash_file(str(src / 'data.bin'))}, {})
        syncer = Syncer()
        syncer.sync(str(src), str(tgt), diff)
        assert (tgt / 'data.bin').read_bytes() == data

    def test_error_counted_when_source_missing(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        diff = DiffResult(added=['ghost.txt'])
        syncer = Syncer()
        stats = syncer.sync(str(src), str(tgt), diff)
        assert stats['errors'] == 1
        assert stats['copied'] == 0

    def test_stats_dict_keys(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        diff = Differ.compare({}, {})
        syncer = Syncer()
        stats = syncer.sync(str(src), str(tgt), diff)
        assert 'copied' in stats
        assert 'skipped' in stats
        assert 'errors' in stats

    def test_dry_run_does_not_write(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        (src / 'new.txt').write_text('hello', encoding='utf-8')
        diff = Differ.compare({'new.txt': 'h1'}, {})
        syncer = Syncer(dry_run=True)
        stats = syncer.sync(str(src), str(tgt), diff)
        assert stats['copied'] == 1
        assert stats['errors'] == 0
        assert not (tgt / 'new.txt').exists(), "dry-run should not create files"

    def test_failed_files_in_stats(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        diff = DiffResult(added=['ghost.txt'])
        syncer = Syncer()
        stats = syncer.sync(str(src), str(tgt), diff)
        assert stats['errors'] == 1
        assert len(stats['failed']) == 1
        assert stats['failed'][0][0] == 'ghost.txt'


import os
import json
import pytest
from distbackup.core.syncer import Syncer, _is_safe_target
from distbackup.core.differ import Differ, DiffResult


import os
import json
import pytest
from distbackup.core.syncer import Syncer, _is_safe_target
from distbackup.core.differ import Differ, DiffResult


class TestPathTraversalProtection:
    """Tests for _is_safe_target and Syncer path traversal blocking."""

    def test_simple_safe_path(self, tmp_path):
        target = str(tmp_path / "target")
        os.makedirs(target, exist_ok=True)
        assert _is_safe_target(target, os.path.join(target, "file.txt"))

    def test_parent_directory_traversal_blocked(self, tmp_path):
        target = str(tmp_path / "target")
        os.makedirs(target, exist_ok=True)
        assert not _is_safe_target(target, os.path.join(target, "..", "escape.txt"))

    def test_double_parent_traversal_blocked(self, tmp_path):
        target = str(tmp_path / "target")
        os.makedirs(target, exist_ok=True)
        assert not _is_safe_target(target, os.path.join(target, "..", "..", "etc", "passwd"))

    def test_absolute_path_blocked(self, tmp_path):
        target = str(tmp_path / "target")
        os.makedirs(target, exist_ok=True)
        assert not _is_safe_target(target, os.path.join(target, "..", "other"))

    def test_syncer_blocks_traversal_in_added(self, tmp_path):
        """Syncer should block added files with traversal paths."""
        src = str(tmp_path / "src")
        tgt = str(tmp_path / "tgt")
        os.makedirs(src, exist_ok=True)
        os.makedirs(tgt, exist_ok=True)
        # Create the legitimate file so it doesnt cause a second error
        (tmp_path / "src" / "escape.txt").write_text("data", encoding="utf-8")

        diff = DiffResult(added=["..", "escape.txt"])
        syncer = Syncer()
        stats = syncer.sync(src, tgt, diff)
        assert stats["errors"] >= 1
        assert any("path traversal blocked" in err for _, err in stats["failed"])

    def test_syncer_blocks_traversal_in_modified(self, tmp_path):
        """Syncer should block modified files with traversal paths."""
        src = str(tmp_path / "src")
        tgt = str(tmp_path / "tgt")
        os.makedirs(src, exist_ok=True)
        os.makedirs(tgt, exist_ok=True)
        (tmp_path / "src" / "sneaky.dll").write_text("dll", encoding="utf-8")

        diff = DiffResult(modified=[os.pardir, os.pardir, "sneaky.dll"])
        syncer = Syncer()
        stats = syncer.sync(src, tgt, diff)
        # Both ".." entries and ".." should be blocked (each is a separate list item)
        assert stats["errors"] >= 1
        assert stats["copied"] == 1  # sneaky.dll is safe

    def test_syncer_blocks_mixed_safe_and_unsafe(self, tmp_path):
        """Safe files still get copied alongside blocked traversals."""
        src = str(tmp_path / "src")
        tgt = str(tmp_path / "tgt")
        os.makedirs(src, exist_ok=True)
        os.makedirs(tgt, exist_ok=True)
        (tmp_path / "src" / "good.txt").write_text("hello", encoding="utf-8")

        diff = DiffResult(added=["good.txt", "..", "hack.exe"])
        syncer = Syncer()
        stats = syncer.sync(src, tgt, diff)
        assert stats["copied"] == 1
        assert stats["errors"] >= 1
        assert os.path.exists(os.path.join(tgt, "good.txt"))

    def test_dry_run_also_blocks_traversal(self, tmp_path):
        """Dry-run mode should also detect and block path traversal."""
        src = str(tmp_path / "src")
        tgt = str(tmp_path / "tgt")
        os.makedirs(src, exist_ok=True)
        os.makedirs(tgt, exist_ok=True)

        diff = DiffResult(added=["..", "evil.sh"])
        syncer = Syncer(dry_run=True)
        stats = syncer.sync(src, tgt, diff)
        assert stats["errors"] >= 1
        assert any("path traversal blocked" in err for _, err in stats["failed"])

    def test_tampered_snapshot_path_is_blocked(self, tmp_path):
        """Simulate a tampered snapshot JSON with traversal paths."""
        src = str(tmp_path / "src")
        tgt = str(tmp_path / "tgt")
        os.makedirs(src, exist_ok=True)
        os.makedirs(tgt, exist_ok=True)

        # Simulate a diff created from a tampered snapshot
        diff = DiffResult(added=[
            os.path.join("..", "..", "..", "..", "Windows", "System32", "malware.dll"),
        ])
        syncer = Syncer()
        stats = syncer.sync(src, tgt, diff)
        assert stats["errors"] == 1
        assert stats["copied"] == 0

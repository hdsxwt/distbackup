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

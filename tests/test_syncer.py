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

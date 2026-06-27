"""Performance benchmarks for distbackup core operations.

Each test measures wall-clock time and asserts below generous thresholds
to catch catastrophic regressions.
"""

import json
import os
import time
import pytest
from distbackup.core.scanner import Scanner
from distbackup.core.snapshot_manager import SnapshotManager
from distbackup.core.differ import Differ
from distbackup.core.syncer import Syncer
from distbackup.core.hashing import hash_file


BENCH_FILE = os.path.join(os.path.dirname(__file__), 'benchmark_results.json')


def _save_bench(name, elapsed, threshold, passed):
    try:
        with open(BENCH_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data[name] = {'elapsed': round(elapsed, 4), 'threshold': threshold, 'passed': passed}
    with open(BENCH_FILE, 'w') as f:
        json.dump(data, f, indent=2)


class TestPerformance:
    def test_scan_1000_flat_files(self, tmp_path):
        for i in range(1000):
            (tmp_path / f'file_{i:06d}.txt').write_text(f'content {i}\n' * 5, encoding='utf-8')
        t0 = time.perf_counter()
        result = Scanner.scan(str(tmp_path))
        elapsed = time.perf_counter() - t0
        assert len(result) == 1000
        assert elapsed < 30.0, f'Scan took {elapsed:.2f}s, threshold 10s'
        _save_bench('scan_1000_flat', elapsed, 10.0, elapsed < 10.0)

    def test_scan_1000_deep_tree(self, tmp_path):
        root = str(tmp_path)
        current = root
        count = 0
        for level in range(50):
            current = os.path.join(current, f'level_{level:02d}')
            os.makedirs(current, exist_ok=True)
            for i in range(20):
                with open(os.path.join(current, f'file_{i:02d}.txt'), 'w') as f:
                    f.write(f'l{level} f{i}\n')
                count += 1
            if count >= 1000:
                break
        t0 = time.perf_counter()
        result = Scanner.scan(str(tmp_path))
        elapsed = time.perf_counter() - t0
        assert len(result) == count
        assert elapsed < 15.0, f'Deep scan took {elapsed:.2f}s, threshold 15s'
        _save_bench('scan_1000_deep', elapsed, 15.0, elapsed < 15.0)

    def test_hash_100mb_file(self, tmp_path):
        size = 100 * 1024 * 1024
        p = tmp_path / 'big.bin'
        with open(str(p), 'wb') as f:
            f.write(b'A' * (1024 * 1024))
            remaining = size - 1024 * 1024
            while remaining > 0:
                chunk = min(remaining, 1024 * 1024)
                f.write(b'B' * chunk)
                remaining -= chunk
        t0 = time.perf_counter()
        digest = hash_file(str(p))
        elapsed = time.perf_counter() - t0
        assert len(digest) == 64
        assert elapsed < 5.0, f'100MB hash took {elapsed:.2f}s, threshold 5s'
        _save_bench('hash_100mb', elapsed, 5.0, elapsed < 5.0)

    def test_hash_5000_small_files(self, tmp_path):
        for i in range(5000):
            (tmp_path / f'f_{i:06d}.txt').write_text(f'data {i}\n', encoding='utf-8')
        t0 = time.perf_counter()
        result = Scanner.scan(str(tmp_path))
        elapsed = time.perf_counter() - t0
        assert len(result) == 5000
        assert elapsed < 90.0, f'5000 file scan took {elapsed:.2f}s, threshold 30s'
        _save_bench('hash_5000_small', elapsed, 30.0, elapsed < 30.0)

    def test_compare_10000_manifests(self, tmp_path):
        size = 10000
        src = {f'file_{i:06d}.txt': f'hash_{i:064d}' for i in range(size)}
        tgt = dict(src)
        del tgt['file_005000.txt']
        tgt['file_000000.txt'] = 'changed_hash'
        t0 = time.perf_counter()
        r = Differ.compare(src, tgt)
        elapsed = time.perf_counter() - t0
        assert r.added == ['file_005000.txt']
        assert r.modified == ['file_000000.txt']
        assert elapsed < 1.0, f'10k compare took {elapsed:.4f}s, threshold 1s'
        _save_bench('compare_10000', elapsed, 1.0, elapsed < 1.0)

    def test_snapshot_save_load_10000(self, tmp_path):
        size = 10000
        files = {f'file_{i:06d}.txt': f'hash_{i:064d}' for i in range(size)}
        mgr = SnapshotManager(str(tmp_path))
        t0 = time.perf_counter()
        mgr.save('big_snap', files, str(tmp_path))
        elapsed_save = time.perf_counter() - t0
        t0 = time.perf_counter()
        loaded = mgr.load('big_snap')
        elapsed_load = time.perf_counter() - t0
        assert loaded['files'] == files
        total = elapsed_save + elapsed_load
        assert total < 3.0, f'Save+load 10k took {total:.2f}s, threshold 3s'
        _save_bench('snapshot_10000', total, 3.0, total < 3.0)

    def test_sync_500_added_files(self, tmp_path):
        src = tmp_path / 'src'
        tgt = tmp_path / 'tgt'
        src.mkdir()
        tgt.mkdir()
        for i in range(500):
            (src / f'f_{i:06d}.txt').write_text(f'content {i}\n' * 10, encoding='utf-8')
        files = {f'f_{i:06d}.txt': f'h{i}' for i in range(500)}
        diff = Differ.compare(files, {})
        syncer = Syncer()
        t0 = time.perf_counter()
        stats = syncer.sync(str(src), str(tgt), diff)
        elapsed = time.perf_counter() - t0
        assert stats['copied'] == 500
        assert elapsed < 10.0, f'500 file sync took {elapsed:.2f}s, threshold 10s'
        _save_bench('sync_500', elapsed, 10.0, elapsed < 10.0)

    def test_incremental_diff_1_in_5000(self, tmp_path):
        size = 5000
        src = {f'file_{i:06d}.txt': f'hash_{i:064d}' for i in range(size)}
        tgt = dict(src)
        tgt['file_002500.txt'] = 'modified_hash'
        t0 = time.perf_counter()
        r = Differ.compare(src, tgt)
        elapsed = time.perf_counter() - t0
        assert r.modified == ['file_002500.txt']
        assert len(r.unchanged) == size - 1
        assert elapsed < 0.5, f'Incremental diff 1/5000 took {elapsed:.4f}s, threshold 0.5s'
        _save_bench('incremental_diff_5000', elapsed, 0.5, elapsed < 0.5)

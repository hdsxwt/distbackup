"""Command-line interface for quick scripting and testing."""

import argparse
import os
import sys

from distbackup.core import (Scanner, SnapshotManager, Differ, Syncer)


def cmd_scan(args):
    files = Scanner.scan(args.dir)
    print(f"Scanned {len(files)} files in {args.dir}")

    mgr = SnapshotManager(args.store or args.dir)
    path = mgr.save(args.name, files, args.dir)
    print(f"Snapshot '{args.name}' saved to {path}")


def cmd_diff(args):
    mgr = SnapshotManager(args.store or os.path.commonpath([args.source, args.target]))
    snap_a = mgr.load(args.source_snap)
    snap_b = mgr.load(args.target_snap)

    result = Differ.compare(snap_a["files"], snap_b["files"])
    print(f"Added:   {len(result.added)}")
    for p in result.added:
        print(f"  + {p}")
    print(f"Modified: {len(result.modified)}")
    for p in result.modified:
        print(f"  ~ {p}")
    print(f"Removed:  {len(result.removed)}")
    for p in result.removed:
        print(f"  - {p}")
    print(f"Unchanged: {len(result.unchanged)}")


def cmd_sync(args):
    mgr = SnapshotManager(args.store or args.source)
    snap_src = mgr.load(args.source_snap)
    snap_tgt = mgr.load(args.target_snap)

    result = Differ.compare(snap_src["files"], snap_tgt["files"])

    def progress(cur, total):
        pct = cur * 100 // total
        print(f"\rCopying... {cur}/{total} ({pct}%)", end="", flush=True)

    syncer = Syncer(progress_callback=progress)
    stats = syncer.sync(args.source, args.target, result)
    print()
    print(f"Done: {stats['copied']} copied, {stats['errors']} errors")


def cmd_list(args):
    mgr = SnapshotManager(args.store or ".")
    names = mgr.list_snapshots()
    if not names:
        print("No snapshots found.")
        return
    print("Snapshots:")
    for n in names:
        snap = mgr.load(n)
        print(f"  {n}  ({len(snap['files'])} files, {snap['created']})")


def main():
    parser = argparse.ArgumentParser(prog="distbackup")
    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="Scan a directory and save snapshot")
    p_scan.add_argument("dir", help="Directory to scan")
    p_scan.add_argument("name", help="Snapshot name")
    p_scan.add_argument("--store", help="Path to .backup root (default: same as dir)")

    p_diff = sub.add_parser("diff", help="Compare two snapshots")
    p_diff.add_argument("source_snap", help="Source snapshot name")
    p_diff.add_argument("target_snap", help="Target snapshot name")
    p_diff.add_argument("--store", help="Path to .backup root")

    p_sync = sub.add_parser("sync", help="Sync files from source to target folder")
    p_sync.add_argument("source", help="Source directory path")
    p_sync.add_argument("target", help="Target directory path")
    p_sync.add_argument("source_snap", help="Source snapshot name")
    p_sync.add_argument("target_snap", help="Target snapshot name")
    p_sync.add_argument("--store", help="Path to .backup root")

    p_list = sub.add_parser("list", help="List all snapshots")
    p_list.add_argument("--store", help="Path to .backup root")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "diff":
        cmd_diff(args)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

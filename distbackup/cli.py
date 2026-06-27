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
    """Perform sync with optional dry-run."""
    mgr = SnapshotManager(args.store or args.source)
    snap_src = mgr.load(args.source_snap)
    snap_tgt = mgr.load(args.target_snap)

    # -- enforce target repo type --
    tgt_mgr = SnapshotManager(args.target)
    if tgt_mgr.get_repo_type() == "Source":
        print("ERROR: Target directory is marked as 'Source' and cannot receive writes.")
        print(f"       Use 'distbackup type {args.target} Target' to change it.")
        return

    result = Differ.compare(snap_src["files"], snap_tgt["files"])

    print(f"Files to add:    {len(result.added)}")
    print(f"Files to modify: {len(result.modified)}")
    print(f"Total changes:   {result.total_changes}")
    print(f"Source: {args.source}  ->  Target: {args.target}")

    if result.total_changes == 0:
        print("Nothing to sync.")
        return

    if not args.force and not args.dry_run:
        answer = input("Proceed with copy? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return

    def progress(cur, total):
        pct = cur * 100 // total
        verb = "Would copy" if args.dry_run else "Copying"
        print(f"\r{verb}... {cur}/{total} ({pct}%)", end="", flush=True)

    syncer = Syncer(progress_callback=progress, dry_run=args.dry_run)
    stats = syncer.sync(args.source, args.target, result)
    print()

    if args.dry_run:
        print(f"DRY RUN -- would copy {stats['copied']} files.")
    else:
        msg = f"Done: {stats['copied']} copied"
        if stats["errors"]:
            msg += f", {stats['errors']} errors"
        print(msg)
        for relpath, err in stats["failed"]:
            print(f"  FAILED: {relpath}  ({err})")


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


def cmd_type(args):
    """Get or set the repository type for a directory."""
    mgr = SnapshotManager(args.dir)
    current = mgr.get_repo_type()
    if args.set_type:
        mgr.set_repo_type(args.set_type)
        print(f"Changed {args.dir} from {current} to {args.set_type}")
    else:
        print(f"{args.dir}  type = {current}")


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
    p_sync.add_argument(
        "--force", "-f", action="store_true",
        help="Skip confirmation prompt before copying."
    )
    p_sync.add_argument(
        "--dry-run", "-n", action="store_true",
        help="Show what would be copied without actually copying."
    )

    p_list = sub.add_parser("list", help="List all snapshots")
    p_list.add_argument("--store", help="Path to .backup root")

    p_type = sub.add_parser("type", help="Get or set repo type (Source / Target)")
    p_type.add_argument("dir", help="Directory whose .backup to manage")
    p_type.add_argument("set_type", nargs="?", choices=["Source", "Target"],
                         help="New type to set (omit to read current)")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "diff":
        cmd_diff(args)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "type":
        cmd_type(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

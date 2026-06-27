# Distributed Backup System

A content-addressable backup tool that detects file changes by SHA256 hash
comparison and syncs directories one-way, safely.

## How it works

1. **Scan** a folder — every file is hashed with SHA256 and stored in a
   content-addressable object store (`.backup/objects/ab/cdef...`), modeled
   after git's object layout.
2. **Snapshot** — the scan result (a `relative_path → hash` map) is
   automatically saved as a timestamp-named JSON snapshot (`20260627_113025`).
3. **Compare** two snapshots to see what changed: added, modified, removed,
   unchanged.
4. **Backup** — copy added and modified files from source to target. Files
   that exist only on the target side are left untouched (no deletions).

Before backup, the GUI warns if either folder has not been re-scanned this
session, or if you are comparing against a snapshot that is not the latest.

## Quick start

```powershell
# Launch the GUI
python -m distbackup

# Or use the CLI
python -m distbackup cli scan D:\my-data  laptop_snap
python -m distbackup cli scan D:\nas\backup nas_snap
python -m distbackup cli diff  laptop_snap nas_snap --store D:\my-data
python -m distbackup cli sync D:\my-data D:\nas\backup laptop_snap nas_snap
```

## Storage layout

```
source-folder/
  .backup/
    objects/              # Content-addressable blob store
      0e/
        20aab55cbb...     # File content stored by hash
    snapshots/            # Timestamp-named directory-state snapshots
      20260627_113025.json
      20260627_114201.json
```

Each snapshot records:
- `created` — UTC timestamp
- `root` — absolute path of the scanned directory
- `files` — `{relative_path: sha256_hexdigest}` mapping

## GUI workflow

1. **Browse** to select source and target folders. The latest snapshot is
   auto-loaded for each folder.
2. **Scan** (optional) each folder to create a fresh snapshot. Snapshots are
   named automatically by timestamp.
3. The combo box shows the current snapshot. A `(new)` marker indicates the
   latest one. Select any snapshot from the dropdown to load it.
4. Click **Compare** to see differences in the tree view.
5. Click **Start Backup** to sync. Warnings appear if snapshots are stale.

## Architecture

| Module | Role |
|--------|------|
| `ContentStore` | Manages `.backup/objects/`. Stores, retrieves, and deduplicates files by SHA256 hash. |
| `Scanner` | Walks a directory tree, hashes every file, optionally stores them in the object store. |
| `SnapshotManager` | Saves and loads timestamp-named JSON snapshots to/from `.backup/snapshots/`. |
| `Differ` | Compares two `{path: hash}` maps and reports added / modified / removed / unchanged. |
| `Syncer` | Copies added and modified files from source to target. Leaves removed files alone. |

## Test data

A sample source/target pair is included under `testdata/`:

```
testdata/
  source/     (6 files across docs/, config/, images/)
  target/     (initially empty, populated by backup)
```

## Requirements

- Python 3.10+ (uses `str | None` type syntax)
- Standard library only — no external dependencies

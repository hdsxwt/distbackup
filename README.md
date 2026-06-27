# distbackup

A content-addressable backup tool that detects file changes by SHA256 hash
comparison and syncs directories one-way, safely.

## How it works

1. **Scan** a folder — every file is hashed with SHA256. The result is
   automatically saved as a timestamp-named JSON snapshot (`20260627_113025`).
2. **Compare** any two snapshots to see what changed: added, modified,
   removed, unchanged.
3. **Backup** — copy added and modified files from source to target. Files
   that exist only on the target side are left untouched (no deletions).

Before backup, the GUI checks whether each folder has been re-scanned
this session and whether the loaded snapshots are the latest. Warnings
appear if conditions are not met.

## Quick start

```powershell
# GUI
python -m distbackup

# CLI
python -m distbackup cli scan D:\my-data  laptop_snap
python -m distbackup cli scan D:\nas\backup nas_snap
python -m distbackup cli diff  laptop_snap nas_snap --store D:\my-data
python -m distbackup cli sync D:\my-data D:\nas\backup laptop_snap nas_snap
```

## Storage layout

```
source-folder/
  .backup/                  # Automatically hidden on Windows
    snapshots/              # Timestamp-named JSON snapshots
      20260627_113025.json
      20260627_114201.json
```

Each snapshot records:
- `created` — UTC timestamp
- `root` — absolute path of the scanned directory
- `files` — `{relative_path: sha256_hexdigest}` mapping

No raw file copies are stored — the snapshot JSON is the sole source of
truth for hash mappings.

## GUI workflow

1. **Browse** to select source and target folders. The latest snapshot
   auto-loads for each side.
2. **Scan** (optional) to create a fresh snapshot. Naming is automatic
   and timestamp-based.
3. The combo box shows the current snapshot, with a `(new)` marker on
   the latest one. Select any snapshot from the dropdown to load it.
4. Click **Compare** to see the diff in a tree view.
5. Click **Start Backup** to sync. Safety warnings appear if snapshots
   are stale or folders have not been scanned this session.

## Architecture

| Module | Role |
|--------|------|
| `hashing` | `hash_file()` and `hash_bytes()` — SHA256 hashing. |
| `Scanner` | Walks a directory tree and returns `{relpath: hash}`. |
| `SnapshotManager` | Saves/loads timestamp-named JSON snapshots. Hides `.backup/`. |
| `Differ` | Compares two `{path: hash}` maps → added / modified / removed / unchanged. |
| `Syncer` | Copies added and modified files from source to target. Never deletes. |

## Test data

```
testdata/
  source/     (7 files across docs/, config/, images/)
  target/     (synced copy)
```

## Requirements

- Python 3.10+
- Standard library only — `hashlib`, `os`, `shutil`, `json`, `tkinter`, `argparse`

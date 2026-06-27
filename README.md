# distbackup

A content-addressable backup tool that detects file changes by SHA256 hash
comparison, enforces repository type safety, and syncs directories one-way
with automatic post-backup verification.

## How it works

1. **Scan** a folder -- every file is hashed with SHA256. The result is
   automatically saved as a timestamp-named JSON snapshot (`20260627_113025`).
2. **Compare** any two snapshots to see what changed: added, modified,
   removed, unchanged.
3. **Backup** -- copy added and modified files from source to target. Files
   that exist only on the target side are left untouched (no deletions).
4. **Verify** -- after a backup completes, the target directory is
   automatically re-scanned and compared against the source snapshot to
   confirm correctness.

## Repository type

Each directory tracked by distbackup carries a type in `.backup/config.json`:

| Type | Can be source | Can be target |
|------|:------------:|:-------------:|
| **Source** | Yes | No |
| **Target** | Yes | Yes |

A directory marked as **Source** is protected: it can never receive writes
from a sync operation. This prevents accidentally overwriting your origin
of truth. Toggle the type in the GUI or with the CLI.

## Quick start

```powershell
# GUI
python -m distbackup

# CLI -- scan
python -m distbackup cli scan D:\my-data  laptop_snap
python -m distbackup cli scan D:\nas\backup nas_snap

# CLI -- diff
python -m distbackup cli diff  laptop_snap nas_snap --store D:\my-data

# CLI -- sync (interactive confirmation)
python -m distbackup cli sync D:\my-data D:\nas\backup laptop_snap nas_snap

# CLI -- dry-run (preview without writing)
python -m distbackup cli sync D:\my-data D:\nas\backup laptop_snap nas_snap --dry-run

# CLI -- skip confirmation
python -m distbackup cli sync D:\my-data D:\nas\backup laptop_snap nas_snap --force

# CLI -- manage repo type
python -m distbackup cli type D:\my-data             # read current type
python -m distbackup cli type D:\my-data Source      # mark as source
python -m distbackup cli type D:\nas\backup Target   # mark as target

# CLI -- list snapshots
python -m distbackup cli list --store D:\my-data
```

## Storage layout

```
root-folder/
  .backup/                  # Automatically hidden on Windows
    config.json             # {"type": "Target"} or {"type": "Source"}
    snapshots/              # Timestamp-named JSON snapshots (atomic writes)
      20260627_113025.json
      20260627_114201.json
```

Each snapshot records:
- `created` -- UTC ISO timestamp
- `root` -- absolute path of the scanned directory
- `files` -- `{relative_path: sha256_hexdigest}` mapping

Snapshots are written atomically (temp file + `os.replace`) so a crash
cannot leave a truncated JSON behind.

## Skipped paths

The scanner automatically skips common version-control, tooling, and OS
directories to avoid hashing gigabytes of irrelevant files:

`.backup` `.git` `.svn` `.hg` `__pycache__` `.pytest_cache` `.mypy_cache`
`.ruff_cache` `.tox` `.venv` `venv` `node_modules` `.idea` `.vscode`
`.DS_Store` `Thumbs.db` `target` `vendor`

## GUI workflow

1. **Browse** to select source and target folders. The latest snapshot
   auto-loads for each side, and the repo type is displayed with a Toggle
   button.
2. **Toggle** the repo type (Source / Target). Changing from Source to
   Target requires a confirmation dialog since it removes write protection.
3. **Scan** (optional) to create a fresh timestamp-named snapshot.
4. The snapshot combo box shows available snapshots, with a `(new)` marker
   on the latest one. Select any snapshot from the dropdown to load it.
5. Click **Compare** to see the diff in a tree view.
6. Click **Start Backup** to sync. Safety checks include:
   - Target type enforcement (blocks writes to Source repos)
   - Stale-snapshot warnings
   - Unscanned-folder warnings
7. After the backup completes, verification runs automatically:
   the target is re-scanned, compared against the source snapshot, and
   results appear in the diff tree with OK / FAILED markers.

## CLI commands

| Command | Description |
|---------|-------------|
| `scan <dir> <name>` | Hash a directory and save a snapshot |
| `diff <src> <tgt>` | Compare two snapshots |
| `sync <src> <tgt> <src_snap> <tgt_snap>` | Copy changed files; `-n` dry-run, `-f` skip confirm |
| `list` | List all snapshots |
| `type <dir> [Source\|Target]` | Get or set repo type |

## Architecture

| Module | Role |
|--------|------|
| `hashing` | `hash_file()` and `hash_bytes()` -- SHA256 hashing. |
| `Scanner` | Walks a directory tree and returns `{relpath: hash}`. Skips tooling dirs. |
| `SnapshotManager` | Saves/loads timestamp-named JSON snapshots (atomic writes). Manages repo type via `config.json`. Hides `.backup/`. |
| `Differ` | Compares two `{path: hash}` maps -> added / modified / removed / unchanged. |
| `Syncer` | Copies added and modified files from source to target. Supports dry-run. Never deletes. Tracks per-file errors. |
| `_win32` | Windows-specific helpers (hide directory, logged errors). |

## Test data

```
testdata/
  source/     (7 files across docs/, config/, images/)
  target/     (synced copy)
```

## Requirements

- Python 3.10+
- Standard library only -- `hashlib`, `os`, `shutil`, `json`, `tkinter`, `argparse`
- 107 tests, all passing

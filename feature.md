## Features

### Scanning & Hashing
- Recursive directory walk with SHA256 content-addressed hashing (64 KB chunk streaming).
- Produces a `{relpath: sha256_hexdigest}` mapping for every file under the root.
- Automatically skips common VCS, tooling, and OS directories: `.backup`, `.git`, `.svn`, `.hg`, `__pycache__`, `.venv`, `venv`, `node_modules`, `.idea`, `.vscode`, `target`, `vendor`, and more.
- Gracefully logs and skips unreadable files instead of aborting the scan.

### Versioned Snapshots
- Timestamp-named JSON snapshots (`20260627_113025.json`) stored under `.backup/snapshots/`.
- Atomic writes via temp file + `os.replace` -- a crash cannot leave a truncated snapshot.
- Each snapshot records the scan timestamp (UTC ISO), scanned root absolute path, and the full file-to-hash mapping.
- Snapshot root validation prevents using a snapshot from one directory with another.

### Diff Engine
- Static comparison of two `{path: hash}` maps produces four categories: added, modified, removed, unchanged.
- Lightweight `DiffResult` dataclass with a `total_changes` convenience property.

### One-Way Sync (Source to Target)
- Copies only added and modified files from source to target -- files that exist only on the target are untouched.
- Path-traversal guard: every destination path is verified to resolve inside the target directory.
- `--dry-run` mode previews what would be copied without writing anything.
- Per-file error tracking reports failures without aborting the remaining copies.
- Interactive confirmation before copying (skip with `--force`).

### Post-Backup Verification
- Automatically re-scans the target directory after every sync.
- Compares the fresh target scan against the source snapshot to confirm correctness.
- Saves the verification result as a new timestamped target snapshot.

### Repository Type Protection
- Each directory carries a type in `.backup/config.json`: `Source` or `Target` (default).
- A `Source` directory is write-protected -- sync operations refuse to write into it.
- Toggling from `Source` to `Target` prompts a confirmation dialog in the GUI.
- Type is inspectable and settable from both CLI and GUI.

### Storage Layout
- All metadata lives under a hidden `.backup/` directory (automatically hidden via `SetFileAttributesW` on Windows).
- `.backup/config.json` holds the repository type.
- `.backup/snapshots/` holds timestamp-named JSON snapshot files.

### CLI
- `scan <dir> <name>` -- hash a directory and save a snapshot.
- `diff <src_snap> <tgt_snap>` -- compare two snapshots with human-readable output.
- `sync <src> <tgt> <src_snap> <tgt_snap>` -- copy changed files with `--dry-run` and `--force` options.
- `list` -- enumerate all snapshots with file counts and timestamps.
- `type <dir> [Source|Target]` -- read or set the repository type.

### GUI (tkinter)
- Browse-to-select source and target folders with automatic latest-snapshot loading.
- Read-only snapshot combo boxes with `(new)` marker on the latest entry.
- Side-by-side scan buttons that run in background threads with progress feedback.
- One-click Compare populating a tree view of added, modified, and removed files.
- Pre-backup safety checks: stale-snapshot warnings, unscanned-folder warnings, and an optional confirmation dialog.
- Post-backup verification results rendered in the same diff tree with OK / FAILED markers.
- Toggle button to switch repository type with confirmation on safety-critical transitions.
- Keyboard shortcuts: `Ctrl+O` browse source, `Ctrl+Shift+O` browse target, `Ctrl+R` refresh snapshots, `Ctrl+W` / `Ctrl+Q` quit.

### Test Suite
- 107 tests covering hashing, scanning, diffing, sync logic, snapshot management, CLI commands, GUI static structure, GUI logic methods, and end-to-end integration.
- Uses isolated `tmp_path` fixtures; no tests touch real user directories.

### Dependencies
- Python 3.10+ standard library only: `hashlib`, `os`, `shutil`, `json`, `tkinter`, `argparse`, `tempfile`, `ctypes`, `threading`, `dataclasses`.

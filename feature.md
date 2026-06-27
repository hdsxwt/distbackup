# Features

## Repository identity

Each repository tracked by distbackup can carry a unique identity code
(`repo_id`) in its `.backup/config.json`. This code represents the
repository lineage and is used to prevent accidentally mixing files from
unrelated source directories into the same backup target.

### Identity lifecycle

| Event | Behavior |
|-------|----------|
| New repository created (Target) | No `repo_id` assigned |
| `set_repo_type("Source")` | UUIDv4 generated and persisted |
| Source scanned / loaded | `repo_id` already present |
| First backup to a Target | Target inherits source's `repo_id` |
| Subsequent backup (same lineage) | Allowed - `repo_id`s match |
| Backup from different source | **Rejected** - `repo_id`s differ |

### Rationale

Without lineage enforcement, it is easy to accidentally back up two
unrelated source trees into the same target directory, creating an
incoherent mess of files from different origins. The `repo_id` mechanism
ensures each backup target stays bound to a single source lineage.

---

## Security protections

### Path traversal blocking

Before copying any file, the sync engine validates that the resolved
destination path stays within the target directory. Tampered snapshot JSON
files containing `..` escape sequences are detected and blocked.

Blocked traversals are recorded in the sync stats with the message
`"path traversal blocked"` and logged as warnings.

### Snapshot root validation

Each snapshot records its origin directory in the `root` field. Before a
sync, both the source and target snapshots are validated to ensure they
were created for the directories currently being operated on. A mismatch
raises a `ValueError` with a descriptive message.

### Scanner transparency

The scanner previously skipped unreadable files silently. Now, any file
that fails to hash due to `OSError` or `PermissionError` is logged as a
warning:

```
WARNING  distbackup.core.scanner: Skipping unreadable file: C:\...\locked.txt (Permission denied)
```

This makes it clear which files were omitted from a scan and why.

### Source write protection

Directories marked as `"Source"` in their `config.json` reject all incoming
sync writes. This is enforced before any files are copied, both in the CLI
and GUI flows.

### Lineage enforcement

See [Repository identity](#repository-identity) above.

---

## Snapshot management

Snapshots are stored as timestamp-named JSON files under `.backup/snapshots/`.
Each write uses a temporary file + `os.replace()` for atomicity - a crash
during snapshot creation cannot leave a truncated JSON file behind.

The `SnapshotManager` API also provides:
- `list_snapshots()` - sorted list of all snapshot names
- `validate_root(name, directory)` - assert that a snapshot was created for the expected directory
- `get_repo_id()` / `ensure_repo_id()` / `set_repo_id()` - identity code management

"""tkinter GUI for the distributed backup system."""

import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from distbackup.core import (Scanner, SnapshotManager, Differ, Syncer)


class BackupGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Distributed Backup")
        self.root.geometry("780x620")
        self.root.resizable(True, True)

        self._diff_result = None
        self._source_files: dict[str, str] = {}
        self._target_files: dict[str, str] = {}
        self._source_scanned: bool = False
        self._target_scanned: bool = False
        self._source_type_var = tk.StringVar(value="?")
        self._target_type_var = tk.StringVar(value="?")

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # --- Folder selection row ---
        folder_frame = ttk.LabelFrame(self.root, text="Folders", padding=6)
        folder_frame.pack(fill=tk.X, padx=8, pady=(8, 2))

        # Source row
        ttk.Label(folder_frame, text="Source:").grid(row=0, column=0, sticky=tk.W)
        self.src_entry = ttk.Entry(folder_frame, width=50)
        self.src_entry.grid(row=0, column=1, padx=(4, 2), sticky=tk.EW)
        ttk.Button(folder_frame, text="Browse", command=self._browse_source).grid(
            row=0, column=2, padx=2
        )
        self.btn_scan_src = ttk.Button(
            folder_frame, text="Scan", command=self._scan_source
        )
        self.btn_scan_src.grid(row=0, column=3, padx=2)
        ttk.Label(folder_frame, text="Type:").grid(row=0, column=4, padx=(8, 2), sticky=tk.W)
        ttk.Label(folder_frame, textvariable=self._source_type_var,
                  foreground="blue").grid(row=0, column=5, padx=2, sticky=tk.W)
        self.btn_toggle_src = ttk.Button(
            folder_frame, text="Toggle", command=self._toggle_source_type, width=8
        )
        self.btn_toggle_src.grid(row=0, column=6, padx=2)
        self.btn_toggle_src.configure(state=tk.DISABLED)

        # Target row
        ttk.Label(folder_frame, text="Target:").grid(row=1, column=0, sticky=tk.W, pady=(4, 0))
        self.tgt_entry = ttk.Entry(folder_frame, width=50)
        self.tgt_entry.grid(row=1, column=1, padx=(4, 2), pady=(4, 0), sticky=tk.EW)
        ttk.Button(folder_frame, text="Browse", command=self._browse_target).grid(
            row=1, column=2, padx=2, pady=(4, 0)
        )
        self.btn_scan_tgt = ttk.Button(
            folder_frame, text="Scan", command=self._scan_target
        )
        self.btn_scan_tgt.grid(row=1, column=3, padx=2, pady=(4, 0))
        ttk.Label(folder_frame, text="Type:").grid(row=1, column=4, padx=(8, 2), pady=(4, 0), sticky=tk.W)
        ttk.Label(folder_frame, textvariable=self._target_type_var,
                  foreground="green").grid(row=1, column=5, padx=2, pady=(4, 0), sticky=tk.W)
        self.btn_toggle_tgt = ttk.Button(
            folder_frame, text="Toggle", command=self._toggle_target_type, width=8
        )
        self.btn_toggle_tgt.grid(row=1, column=6, padx=2, pady=(4, 0))
        self.btn_toggle_tgt.configure(state=tk.DISABLED)

        folder_frame.columnconfigure(1, weight=1)

        # --- Snapshot row (combo selects, auto-loads) ---
        snap_frame = ttk.LabelFrame(self.root, text="Snapshots", padding=6)
        snap_frame.pack(fill=tk.X, padx=8, pady=2)

        ttk.Label(snap_frame, text="Source:").grid(row=0, column=0, sticky=tk.W)
        self.src_snap_combo = ttk.Combobox(snap_frame, state="readonly", width=22)
        self.src_snap_combo.grid(row=0, column=1, padx=4, sticky=tk.W)
        self.src_snap_combo.bind("<<ComboboxSelected>>", self._on_src_combo_select)
        ttk.Button(snap_frame, text="Refresh", command=self._refresh_snapshot_lists).grid(
            row=0, column=2, padx=2
        )

        ttk.Label(snap_frame, text="Target:").grid(row=1, column=0, sticky=tk.W, pady=(4, 0))
        self.tgt_snap_combo = ttk.Combobox(snap_frame, state="readonly", width=22)
        self.tgt_snap_combo.grid(row=1, column=1, padx=4, pady=(4, 0), sticky=tk.W)
        self.tgt_snap_combo.bind("<<ComboboxSelected>>", self._on_tgt_combo_select)
        ttk.Button(snap_frame, text="Refresh", command=self._refresh_snapshot_lists).grid(
            row=1, column=2, padx=2, pady=(4, 0)
        )

        self.btn_compare = ttk.Button(
            snap_frame, text="Compare", command=self._compare, width=12
        )
        self.btn_compare.grid(row=0, column=3, rowspan=2, padx=(16, 0), sticky=tk.NS)

        # --- Diff result area ---
        diff_frame = ttk.LabelFrame(self.root, text="Diff Results", padding=6)
        diff_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=2)

        columns = ("status", "path")
        self.diff_tree = ttk.Treeview(
            diff_frame, columns=columns, show="headings", height=10
        )
        self.diff_tree.heading("status", text="Status")
        self.diff_tree.heading("path", text="File Path")
        self.diff_tree.column("status", width=80, anchor=tk.CENTER)
        self.diff_tree.column("path", width=580)

        scrollbar = ttk.Scrollbar(
            diff_frame, orient=tk.VERTICAL, command=self.diff_tree.yview
        )
        self.diff_tree.configure(yscrollcommand=scrollbar.set)

        self.diff_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Progress bar ---
        self.progress = ttk.Progressbar(
            self.root, mode="determinate", length=400
        )
        self.progress.pack(fill=tk.X, padx=8, pady=(2, 0))

        # --- Log area ---
        log_frame = ttk.LabelFrame(self.root, text="Log", padding=4)
        log_frame.pack(fill=tk.X, padx=8, pady=2)

        self.log_text = tk.Text(log_frame, height=4, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.X)

        # --- Backup button ---
        self.btn_backup = ttk.Button(
            self.root, text="Start Backup", command=self._backup, width=14
        )
        self.btn_backup.pack(pady=(4, 8))
        self.btn_backup.configure(state=tk.DISABLED)

        self._bind_shortcuts()

    # ------------------------------------------------------------------
    # Folder selection (with auto-load of latest snapshot)
    # ------------------------------------------------------------------

    def _bind_shortcuts(self):
        """Register keyboard shortcuts on the root window."""
        self.root.bind("<Control-o>", lambda e: (self._browse_source(), "break")[1])
        self.root.bind("<Control-Shift-O>", lambda e: (self._browse_target(), "break")[1])
        self.root.bind("<Control-r>", lambda e: (self._refresh_snapshot_lists(), "break")[1])
        self.root.bind("<Control-q>", lambda e: (self.root.destroy(), "break")[1])
        self.root.bind("<Control-w>", lambda e: (self.root.destroy(), "break")[1])

    def _browse_source(self):
        path = filedialog.askdirectory(title="Select Source Folder")
        if path:
            self.src_entry.delete(0, tk.END)
            self.src_entry.insert(0, path)
            self._refresh_type_display("source")
            self._auto_load_latest("source")

    def _browse_target(self):
        path = filedialog.askdirectory(title="Select Target Folder")
        if path:
            self.tgt_entry.delete(0, tk.END)
            self.tgt_entry.insert(0, path)
            self._refresh_type_display("target")
            self._auto_load_latest("target")

    # ------------------------------------------------------------------
    # Auto-load latest snapshot (marks combo with "(new)")
    # ------------------------------------------------------------------

    def _auto_load_latest(self, side: str):
        """After selecting a folder, load its most recent snapshot automatically."""
        entry = self.src_entry if side == "source" else self.tgt_entry
        file_attr = "_source_files" if side == "source" else "_target_files"
        combo = self.src_snap_combo if side == "source" else self.tgt_snap_combo

        directory = entry.get().strip()
        if not directory:
            return

        mgr = SnapshotManager(directory)
        name = self._find_latest_snapshot(mgr)
        if name is None:
            self._log(f"No snapshots in {directory}. Click Scan to create one.")
            self._refresh_snapshot_lists()
            return

        snap = mgr.load(name)
        setattr(self, file_attr, snap["files"])
        self._refresh_snapshot_lists()
        self._mark_combo(side, name)
        self._log(
            f"Auto-loaded {side} snapshot '{name}': "
            f"{len(snap['files'])} files ({snap['created']})"
        )

    @staticmethod
    def _find_latest_snapshot(mgr: SnapshotManager) -> str | None:
        """Return the name of the most recent snapshot, or None."""
        names = mgr.list_snapshots()
        if not names:
            return None
        best_name = names[0]
        best_ts = ""
        for n in names:
            try:
                snap = mgr.load(n)
                ts = snap.get("created", "")
                if ts > best_ts:
                    best_ts = ts
                    best_name = n
            except Exception:
                pass
        return best_name

    # ------------------------------------------------------------------
    # Scanning (auto-saves with date+time name, no prefix)
    # ------------------------------------------------------------------

    def _scan_source(self):
        directory = self.src_entry.get().strip()
        if not directory:
            messagebox.showwarning("Warning", "Please select a source folder first.")
            return
        self._log(f"Scanning source: {directory}")
        self._set_buttons_state(tk.DISABLED)

        def worker():
            try:
                files = Scanner.scan(directory)
                self._source_files = files
                self.root.after(0, lambda: self._on_scan_done("source", len(files), directory))
            except Exception as e:
                self.root.after(0, lambda: self._on_scan_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _scan_target(self):
        directory = self.tgt_entry.get().strip()
        if not directory:
            messagebox.showwarning("Warning", "Please select a target folder first.")
            return
        self._log(f"Scanning target: {directory}")
        self._set_buttons_state(tk.DISABLED)

        def worker():
            try:
                files = Scanner.scan(directory)
                self._target_files = files
                self.root.after(0, lambda: self._on_scan_done("target", len(files), directory))
            except Exception as e:
                self.root.after(0, lambda: self._on_scan_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_scan_done(self, side: str, count: int, directory: str):
        ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        mgr = SnapshotManager(directory)
        files = self._source_files if side == "source" else self._target_files
        mgr.save(ts_name, files, directory)
        if side == "source":
            self._source_scanned = True
        else:
            self._target_scanned = True
        self._log(f"{side.capitalize()} scan complete: {count} files, saved as '{ts_name}'")
        self._set_buttons_state(tk.NORMAL)
        self._auto_load_latest(side)
        self._refresh_type_display(side)

    def _on_scan_error(self, msg: str):
        self._log(f"ERROR: {msg}")
        self._set_buttons_state(tk.NORMAL)
        messagebox.showerror("Scan Error", msg)

    # ------------------------------------------------------------------
    # Snapshot selection (combo triggers auto-load, strips "(new)")
    # ------------------------------------------------------------------

    def _on_src_combo_select(self, event):
        name = self.src_snap_combo.get().replace(" (new)", "")
        if not name:
            return
        directory = self.src_entry.get().strip()
        if not directory:
            return
        mgr = SnapshotManager(directory)
        try:
            snap = mgr.load(name)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Snapshot '{name}' not found.")
            return
        self._source_files = snap["files"]
        self._mark_combo("source", name)
        self._refresh_type_display("source")
        self._log(f"Loaded source snapshot '{name}': {len(snap['files'])} files ({snap['created']})")

    def _on_tgt_combo_select(self, event):
        name = self.tgt_snap_combo.get().replace(" (new)", "")
        if not name:
            return
        directory = self.tgt_entry.get().strip()
        if not directory:
            return
        mgr = SnapshotManager(directory)
        try:
            snap = mgr.load(name)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Snapshot '{name}' not found.")
            return
        self._target_files = snap["files"]
        self._mark_combo("target", name)
        self._refresh_type_display("target")
        self._log(f"Loaded target snapshot '{name}': {len(snap['files'])} files ({snap['created']})")
    def _mark_combo(self, side: str, name: str):
        """Set combo display, adding (new) only if this is the latest snapshot."""
        entry = self.src_entry if side == "source" else self.tgt_entry
        combo = self.src_snap_combo if side == "source" else self.tgt_snap_combo
        directory = entry.get().strip()
        if directory:
            mgr = SnapshotManager(directory)
            latest = self._find_latest_snapshot(mgr)
            if latest == name:
                combo.set(f"{name} (new)")
            else:
                combo.set(name)



    def _get_combo_name(self, side: str) -> str:
        """Get the raw snapshot name currently shown in the combo (without (new))."""
        combo = self.src_snap_combo if side == "source" else self.tgt_snap_combo
        return combo.get().replace(" (new)", "")

    def _find_latest_snapshot_name(self, side: str) -> str | None:
        """Find the latest snapshot name for the given side's directory."""
        entry = self.src_entry if side == "source" else self.tgt_entry
        directory = entry.get().strip()
        if not directory:
            return None
        mgr = SnapshotManager(directory)
        return self._find_latest_snapshot(mgr)

    def _refresh_snapshot_lists(self):
        src_dir = self.src_entry.get().strip()
        if src_dir:
            mgr = SnapshotManager(src_dir)
            names = mgr.list_snapshots()
            self.src_snap_combo["values"] = names

        tgt_dir = self.tgt_entry.get().strip()
        if tgt_dir:
            mgr = SnapshotManager(tgt_dir)
            names = mgr.list_snapshots()
            self.tgt_snap_combo["values"] = names

    # ------------------------------------------------------------------
    # Compare
    # ------------------------------------------------------------------

    def _compare(self):
        if not self._source_files:
            messagebox.showwarning("Warning", "No source data. Scan or load a snapshot first.")
            return
        if not self._target_files:
            messagebox.showwarning("Warning", "No target data. Scan or load a snapshot first.")
            return

        self._diff_result = Differ.compare(self._source_files, self._target_files)
        self._populate_diff_tree()

        total = self._diff_result.total_changes
        self._log(
            f"Compare: {len(self._diff_result.added)} added, "
            f"{len(self._diff_result.modified)} modified, "
            f"{len(self._diff_result.removed)} removed, "
            f"{len(self._diff_result.unchanged)} unchanged"
        )

        if total > 0:
            self.btn_backup.configure(state=tk.NORMAL)
        else:
            self.btn_backup.configure(state=tk.DISABLED)
            self._log("No changes to backup.")

    def _populate_diff_tree(self):
        for item in self.diff_tree.get_children():
            self.diff_tree.delete(item)

        if not self._diff_result:
            return

        for p in self._diff_result.added:
            self.diff_tree.insert("", tk.END, values=("+ ADDED", p))
        for p in self._diff_result.modified:
            self.diff_tree.insert("", tk.END, values=("~ MODIFIED", p))
        for p in self._diff_result.removed:
            self.diff_tree.insert("", tk.END, values=("- REMOVED", p))

        n = len(self._diff_result.unchanged)
        if n:
            self.diff_tree.insert("", tk.END, values=(f"= {n} unchanged", ""))

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    def _backup(self):
        src = self.src_entry.get().strip()
        tgt = self.tgt_entry.get().strip()
        if not src or not tgt:
            messagebox.showwarning("Warning", "Both source and target folders are required.")
            return
        if not self._diff_result or self._diff_result.total_changes == 0:
            return

        # --- enforce target repo type ---
        tgt_mgr = SnapshotManager(tgt)
        if tgt_mgr.get_repo_type() == "Source":
            messagebox.showerror(
                "Blocked",
                "Target directory is marked as 'Source' and cannot receive writes.\n\n"
                "Use the Toggle button or CLI to change it to 'Target' first."
            )
            self._log("Backup blocked: target is Source type.")
            return

        # Pre-backup safety checks
        warnings = []
        if not self._source_scanned:
            warnings.append("Source folder has NOT been scanned in this session.")
        if not self._target_scanned:
            warnings.append("Target folder has NOT been scanned in this session.")

        src_latest = self._get_combo_name("source")
        tgt_latest = self._get_combo_name("target")
        src_actual = self._find_latest_snapshot_name("source")
        tgt_actual = self._find_latest_snapshot_name("target")
        if src_latest and src_actual and src_latest != src_actual:
            warnings.append(f"Source snapshot \"{src_latest}\" is not the latest (\"{src_actual}\" is newer).")
        if tgt_latest and tgt_actual and tgt_latest != tgt_actual:
            warnings.append(f"Target snapshot \"{tgt_latest}\" is not the latest (\"{tgt_actual}\" is newer).")

        if warnings:
            msg = "Warnings:\n\n" + "\n".join(f"  - {w}" for w in warnings)
            msg += "\n\nContinue anyway?"
            if not messagebox.askyesno("Backup Warning", msg):
                self._log("Backup cancelled by user.")
                return

        self._set_buttons_state(tk.DISABLED)
        self.progress["maximum"] = self._diff_result.total_changes
        self.progress["value"] = 0
        source_files_copy = dict(self._source_files)
        diff_copy = self._diff_result
        self._diff_result = None

        def progress_cb(cur, total):
            self.root.after(0, lambda: self._update_progress(cur, total))

        syncer = Syncer(progress_callback=progress_cb, dry_run=False)

        def worker():
            try:
                stats = syncer.sync(src, tgt, diff_copy)
                self.root.after(0, lambda: self._on_backup_done(stats))

                # --- post-backup verification ---
                self.root.after(0, lambda: self._log("Verifying target ..."))
                tgt_now = Scanner.scan(tgt)
                verify = Differ.compare(source_files_copy, tgt_now)
                # Save fresh scan as timestamped snapshot
                verify_name = datetime.now().strftime("%Y%m%d_%H%M%S")
                tgt_mgr.save(verify_name, tgt_now, tgt)
                self.root.after(0, lambda vn=verify_name: self._on_verify_done(verify, tgt, vn))
            except Exception as e:
                self.root.after(0, lambda: self._on_backup_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, cur: int, total: int):
        self.progress["value"] = cur
        pct = cur * 100 // total if total else 0
        self._log(f"Copying... {cur}/{total} ({pct}%)")

    def _on_backup_done(self, stats: dict):
        msg_parts = [f"Backup complete: {stats['copied']} copied"]
        if stats["errors"]:
            msg_parts.append(f"{stats['errors']} errors")
        self._log(", ".join(msg_parts))

        for relpath, err in stats.get("failed", []):
            self._log(f"  FAILED: {relpath}  ({err})")

        if stats["errors"]:
            messagebox.showwarning(
                "Backup Done",
                f"{stats['copied']} copied, {stats['errors']} errors."
            )
        else:
            messagebox.showinfo("Backup Done", f"Successfully copied {stats['copied']} files.")

    def _on_verify_done(self, verify, tgt_dir: str, verify_name: str):
        """Handle post-backup verification result."""
        self.progress["value"] = 0
        self._set_buttons_state(tk.NORMAL)
        self._diff_result = None
        self.btn_backup.configure(state=tk.DISABLED)

        if verify.total_changes == 0:
            self._log("Verification passed -- target matches source.")
            self._populate_verify_tree(
                verify.added, verify.modified, verify.removed, verify.unchanged,
            )
        else:
            self._log(
                f"Verification found {verify.total_changes} remaining difference(s): "
                f"{len(verify.added)} added, {len(verify.modified)} modified"
            )
            self._populate_verify_tree(
                verify.added, verify.modified, verify.removed, verify.unchanged,
                failed=True,
            )
        # Refresh target state from the verification snapshot (named with timestamp)
        try:
            mgr = SnapshotManager(tgt_dir)
            snap = mgr.load(verify_name)
            self._target_files = snap["files"]
            self._target_scanned = True
            self._auto_load_latest("target")
        except Exception:
            pass

    def _populate_verify_tree(self, added, modified, removed, unchanged, failed=False):
        """Populate diff tree with verification results."""
        for item in self.diff_tree.get_children():
            self.diff_tree.delete(item)
        label = "!! FAILED" if failed else "OK"
        for p in added:
            self.diff_tree.insert("", tk.END, values=(f"+ {label}", p))
        for p in modified:
            self.diff_tree.insert("", tk.END, values=(f"~ {label}", p))
        for p in removed:
            self.diff_tree.insert("", tk.END, values=("- OK", p))
        n = len(unchanged)
        if n:
            self.diff_tree.insert("", tk.END, values=(f"= {n} OK", ""))

    def _on_backup_error(self, msg: str):
        self._log(f"ERROR: {msg}")
        self._set_buttons_state(tk.NORMAL)
        self.progress["value"] = 0
        messagebox.showerror("Backup Error", msg)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_buttons_state(self, state: str):
        for btn in [
            self.btn_scan_src,
            self.btn_scan_tgt,
            self.btn_compare,
            self.btn_backup,
            self.btn_toggle_src,
            self.btn_toggle_tgt,
        ]:
            try:
                btn.configure(state=state)
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Repo type toggle
    # ------------------------------------------------------------------

    def _refresh_type_display(self, side: str):
        """Read the repo type from .backup/config.json and update display."""
        entry = self.src_entry if side == "source" else self.tgt_entry
        var = self._source_type_var if side == "source" else self._target_type_var
        btn = self.btn_toggle_src if side == "source" else self.btn_toggle_tgt

        directory = entry.get().strip()
        if not directory or not os.path.isdir(directory):
            var.set("?")
            btn.configure(state=tk.DISABLED)
            return

        try:
            mgr = SnapshotManager(directory)
            var.set(mgr.get_repo_type())
            btn.configure(state=tk.NORMAL)
        except Exception:
            var.set("?")
            btn.configure(state=tk.DISABLED)

    def _toggle_source_type(self):
        self._toggle_type("source")

    def _toggle_target_type(self):
        self._toggle_type("target")

    def _toggle_type(self, side: str):
        entry = self.src_entry if side == "source" else self.tgt_entry
        directory = entry.get().strip()
        if not directory:
            return

        mgr = SnapshotManager(directory)
        current = mgr.get_repo_type()
        new_type = "Target" if current == "Source" else "Source"

        # Source -> Target is a safety-critical transition: confirm.
        if current == "Source" and new_type == "Target":
            if not messagebox.askyesno(
                "Confirm",
                f"Change {side} from Source to Target?\n\n"
                "A Target directory can receive writes (sync into it).\n"
                "This means its files could be overwritten by a future backup."
            ):
                return

        mgr.set_repo_type(new_type)
        self._refresh_type_display(side)
        self._log(f"{side.capitalize()} type changed: {current} -> {new_type}")

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self):
        self.root.mainloop()


def main():
    app = BackupGUI()
    app.run()


if __name__ == "__main__":
    main()

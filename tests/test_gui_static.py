"""Static AST-based verification of gui.py — no tkinter import needed."""

import ast
import os


GUI_PATH = os.path.join(
    os.path.dirname(__file__), "..", "distbackup", "gui.py"
)


def _parse_gui():
    with open(GUI_PATH, "r", encoding="utf-8") as f:
        return ast.parse(f.read())


def _find_class(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _class_method_names(cls_node):
    return {
        n.name for n in cls_node.body
        if isinstance(n, ast.FunctionDef)
    }


def _class_assign_targets(cls_node):
    targets = []
    for node in ast.walk(cls_node):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                    targets.append(t.attr)
    return set(targets)


class TestGuiClassExists:
    def test_backup_gui_class_present(self):
        tree = _parse_gui()
        cls = _find_class(tree, "BackupGUI")
        assert cls is not None, "BackupGUI class not found"


class TestRequiredMethods:
    @classmethod
    def setup_class(cls):
        tree = _parse_gui()
        cls_node = _find_class(tree, "BackupGUI")
        assert cls_node is not None
        cls.methods = _class_method_names(cls_node)

    def test_ui_builder(self):
        assert "_build_ui" in self.methods

    def test_scan_methods(self):
        assert "_scan_source" in self.methods
        assert "_scan_target" in self.methods

    def test_scan_done(self):
        assert "_on_scan_done" in self.methods

    def test_compare(self):
        assert "_compare" in self.methods

    def test_backup(self):
        assert "_backup" in self.methods

    def test_auto_load(self):
        assert "_auto_load_latest" in self.methods

    def test_mark_combo(self):
        assert "_mark_combo" in self.methods

    def test_find_latest_snapshot(self):
        assert "_find_latest_snapshot" in self.methods

    def test_find_latest_snapshot_name(self):
        assert "_find_latest_snapshot_name" in self.methods

    def test_refresh_snapshot_lists(self):
        assert "_refresh_snapshot_lists" in self.methods

    def test_get_combo_name(self):
        assert "_get_combo_name" in self.methods


class TestRequiredWidgets:
    @classmethod
    def setup_class(cls):
        tree = _parse_gui()
        cls_node = _find_class(tree, "BackupGUI")
        assert cls_node is not None
        cls.attrs = _class_assign_targets(cls_node)

    def test_entry_widgets(self):
        assert "src_entry" in self.attrs
        assert "tgt_entry" in self.attrs

    def test_button_widgets(self):
        assert "btn_scan_src" in self.attrs
        assert "btn_scan_tgt" in self.attrs
        assert "btn_compare" in self.attrs
        assert "btn_backup" in self.attrs

    def test_combo_widgets(self):
        assert "src_snap_combo" in self.attrs
        assert "tgt_snap_combo" in self.attrs

    def test_display_widgets(self):
        assert "diff_tree" in self.attrs
        assert "progress" in self.attrs
        assert "log_text" in self.attrs

    def test_state_attrs(self):
        assert "_source_files" in self.attrs
        assert "_target_files" in self.attrs
        assert "_source_scanned" in self.attrs
        assert "_target_scanned" in self.attrs
        assert "_diff_result" in self.attrs


class TestThreadingPatterns:
    def test_threading_imported(self):
        tree = _parse_gui()
        imports = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]
        assert "threading" in imports or any(
            n.module == "threading" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
        )

    def test_daemon_threads(self):
        with open(GUI_PATH, "r", encoding="utf-8") as f:
            source = f.read()
        assert "daemon=True" in source


class TestTkinterSafety:
    def test_root_after_calls(self):
        with open(GUI_PATH, "r", encoding="utf-8") as f:
            source = f.read()
        assert "self.root.after(" in source

    def test_buttons_disabled_during_scan(self):
        with open(GUI_PATH, "r", encoding="utf-8") as f:
            source = f.read()
        assert "tk.DISABLED" in source


class TestKeyboardShortcuts:
    @classmethod
    def setup_class(cls):
        with open(GUI_PATH, "r", encoding="utf-8") as f:
            cls.source = f.read()

    def test_bind_shortcuts_method_exists(self):
        tree = _parse_gui()
        cls_node = _find_class(tree, "BackupGUI")
        methods = _class_method_names(cls_node)
        assert "_bind_shortcuts" in methods

    def test_all_shortcut_sequences_present(self):
        assert "<Control-o>" in self.source
        assert "<Control-Shift-O>" in self.source
        assert "<Control-r>" in self.source
        assert "<Control-q>" in self.source
        assert "<Control-w>" in self.source

    def test_shortcuts_called_from_build_ui(self):
        assert "self._bind_shortcuts()" in self.source
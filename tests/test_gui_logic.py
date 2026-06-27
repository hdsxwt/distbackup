"""Test pure-logic methods from gui.py extracted without tkinter.

These tests instantiate BackupGUI with mocked tkinter to exercise
the logic methods that don't require a display server.
"""

import os
import sys
import types
import pytest

gui_path = os.path.join(os.path.dirname(__file__), '..', 'distbackup', 'gui.py')


class FakeTk:
    pass


class FakeEntry:
    def __init__(self):
        self._value = ''
    def get(self):
        return self._value
    def delete(self, a, b):
        self._value = ''
    def insert(self, a, s):
        self._value = s


class FakeCombo:
    def __init__(self):
        self._value = ''
        self.values = []
    def get(self):
        return self._value
    def set(self, v):
        self._value = v
    def bind(self, event, cb):
        pass


class FakeButton:
    def configure(self, **kw):
        pass


class FakeTreeview:
    def get_children(self):
        return []
    def delete(self, item):
        pass
    def insert(self, *a, **kw):
        pass
    def heading(self, *a, **kw):
        pass
    def column(self, *a, **kw):
        pass
    def configure(self, *a, **kw):
        pass
    def pack(self, *a, **kw):
        pass


class FakeProgressbar:
    def __setitem__(self, k, v):
        pass
    def pack(self, *a, **kw):
        pass


class FakeText:
    def __init__(self):
        self._state = 'normal'
    def configure(self, **kw):
        pass
    def insert(self, pos, text):
        pass
    def see(self, pos):
        pass
    def pack(self, *a, **kw):
        pass


def _make_fake_gui():
    import importlib.util
    spec = importlib.util.spec_from_file_location('gui', gui_path)
    mod = importlib.util.module_from_spec(spec)

    fake_tk = types.ModuleType('tkinter')
    fake_tk.Tk = FakeTk
    fake_tk.DISABLED = 'disabled'
    fake_tk.NORMAL = 'normal'
    fake_tk.END = 'end'
    fake_tk.W = 'w'
    fake_tk.X = 'x'
    fake_tk.Y = 'y'
    fake_tk.BOTH = 'both'
    fake_tk.LEFT = 'left'
    fake_tk.RIGHT = 'right'
    fake_tk.TOP = 'top'
    fake_tk.BOTTOM = 'bottom'
    fake_tk.EW = 'ew'
    fake_tk.NS = 'ns'
    fake_tk.CENTER = 'center'
    fake_tk.WORD = 'word'

    fake_ttk = types.ModuleType('tkinter.ttk')
    fake_ttk.LabelFrame = lambda *a, **kw: FakeTk()
    fake_ttk.Label = lambda *a, **kw: FakeTk()
    fake_ttk.Entry = lambda *a, **kw: FakeEntry()
    fake_ttk.Button = lambda *a, **kw: FakeButton()
    fake_ttk.Combobox = lambda *a, **kw: FakeCombo()
    fake_ttk.Treeview = lambda *a, **kw: FakeTreeview()
    fake_ttk.Scrollbar = lambda *a, **kw: FakeTk()
    fake_ttk.Progressbar = lambda *a, **kw: FakeProgressbar()

    fake_tk.Text = lambda *a, **kw: FakeText()

    fake_msg = types.ModuleType('tkinter.messagebox')
    fake_msg.showwarning = lambda *a, **kw: 'ok'
    fake_msg.showerror = lambda *a, **kw: 'ok'
    fake_msg.showinfo = lambda *a, **kw: 'ok'
    fake_msg.askyesno = lambda *a, **kw: True

    fake_fd = types.ModuleType('tkinter.filedialog')
    fake_fd.askdirectory = lambda **kw: '/tmp/test'

    fake_tk.messagebox = fake_msg
    fake_tk.filedialog = fake_fd
    fake_tk.ttk = fake_ttk

    sys.modules['tkinter'] = fake_tk
    sys.modules['tkinter.ttk'] = fake_ttk
    sys.modules['tkinter.messagebox'] = fake_msg
    sys.modules['tkinter.filedialog'] = fake_fd

    try:
        spec.loader.exec_module(mod)
    finally:
        for m in ['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog']:
            sys.modules.pop(m, None)

    return mod


class TestFindLatestSnapshot:
    @classmethod
    def setup_class(cls):
        cls.mod = _make_fake_gui()

    def test_method_exists(self):
        assert hasattr(self.mod.BackupGUI, '_find_latest_snapshot')

    def test_returns_none_for_empty(self, tmp_path):
        from distbackup.core.snapshot_manager import SnapshotManager
        mgr = SnapshotManager(str(tmp_path))
        result = self.mod.BackupGUI._find_latest_snapshot(mgr)
        assert result is None

    def test_returns_name_for_single(self, tmp_path):
        from distbackup.core.snapshot_manager import SnapshotManager
        mgr = SnapshotManager(str(tmp_path))
        mgr.save('mysnap', {'a': 'h'}, str(tmp_path))
        result = self.mod.BackupGUI._find_latest_snapshot(mgr)
        assert result == 'mysnap'

    def test_returns_newest(self, tmp_path):
        from distbackup.core.snapshot_manager import SnapshotManager
        import time
        mgr = SnapshotManager(str(tmp_path))
        mgr.save('older', {'a': 'h'}, str(tmp_path))
        time.sleep(0.01)
        mgr.save('newer', {'a': 'h'}, str(tmp_path))
        result = self.mod.BackupGUI._find_latest_snapshot(mgr)
        assert result == 'newer'

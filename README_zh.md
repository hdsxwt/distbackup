# distbackup

基于 SHA256 哈希比较的目录备份工具，支持仓库类型保护、单向安全同步，
同步后自动验证。

## 工作原理

1. **扫描** -- 对目录中每个文件计算 SHA256，结果自动保存为时间戳命名
   的 JSON 快照（如 `20260627_113025`）。
2. **比较** -- 对比任意两个快照，得出新增、修改、仅目标有、未变化四类差异。
3. **备份** -- 将新增和修改的文件从源复制到目标。目标侧独有的文件不删除。
4. **验证** -- 备份完成后自动重新扫描目标目录，与源快照比对以确认正确性。

## 仓库类型

distbackup 管理的每个目录在 `.backup/config.json` 中记录类型：

| 类型 | 可作为源 | 可作为目标 |
|------|:------:|:------:|
| **Source** | 是 | 否 |
| **Target** | 是 | 是 |

标记为 **Source** 的目录受写保护：sync 操作无法向其中写入数据，
防止意外覆盖原始数据。可在 GUI 中切换或通过 CLI 管理。

## 快速开始

```powershell
# 图形界面
python -m distbackup

# CLI -- 扫描
python -m distbackup cli scan D:\my-data  laptop_snap
python -m distbackup cli scan D:\nas\backup nas_snap

# CLI -- 比较
python -m distbackup cli diff  laptop_snap nas_snap --store D:\my-data

# CLI -- 同步（交互确认）
python -m distbackup cli sync D:\my-data D:\nas\backup laptop_snap nas_snap

# CLI -- 试运行（预览不写入）
python -m distbackup cli sync D:\my-data D:\nas\backup laptop_snap nas_snap --dry-run

# CLI -- 跳过确认
python -m distbackup cli sync D:\my-data D:\nas\backup laptop_snap nas_snap --force

# CLI -- 管理仓库类型
python -m distbackup cli type D:\my-data             # 查看当前类型
python -m distbackup cli type D:\my-data Source      # 标记为源
python -m distbackup cli type D:\nas\backup Target   # 标记为目标

# CLI -- 列出快照
python -m distbackup cli list --store D:\my-data
```

## 存储结构

```
目录/
  .backup/                  # Windows 下自动隐藏
    config.json             # {"type": "Target"} 或 {"type": "Source"}
    snapshots/              # 时间戳命名的 JSON 快照（原子写入）
      20260627_113025.json
      20260627_114201.json
```

每个快照记录：
- `created` -- UTC ISO 时间戳
- `root` -- 被扫描目录的绝对路径
- `files` -- `{相对路径: SHA256十六进制摘要}` 映射

快照采用原子写入（临时文件 + `os.replace`），崩溃不会残留残缺 JSON。

## 跳过的路径

扫描器自动跳过常见版本控制、工具链和操作系统目录，
避免对大量无关文件做哈希：

`.backup` `.git` `.svn` `.hg` `__pycache__` `.pytest_cache` `.mypy_cache`
`.ruff_cache` `.tox` `.venv` `venv` `node_modules` `.idea` `.vscode`
`.DS_Store` `Thumbs.db` `target` `vendor`

## GUI 操作流程

1. **Browse** 选择源和目标文件夹，自动加载各自最新快照，
   显示仓库类型并提供 Toggle 切换按钮。
2. **Toggle** 切换仓库类型（Source / Target）。从 Source 切换到
   Target 需要确认对话框，因为这会移除写保护。
3. **Scan**（可选）重新扫描，自动保存新的时间戳快照。
4. 快照下拉框显示可用快照，`(new)` 标记表示最新快照。
   下拉选择即可加载。
5. **Compare** 查看差异树形列表。
6. **Start Backup** 执行同步。安全检查包括：
   - 目标类型强制检查（阻止向 Source 仓库写入）
   - 快照过期警告
   - 未扫描文件夹警告
7. 备份完成后自动验证：重新扫描目标目录，与源快照比对，
   结果以 OK / FAILED 标记显示在差异树中。

## CLI 命令

| 命令 | 说明 |
|---------|------|
| `scan <目录> <名称>` | 哈希扫描目录并保存快照 |
| `diff <源快照> <目标快照>` | 比较两个快照 |
| `sync <源目录> <目标目录> <源快照> <目标快照>` | 复制变更文件；`-n` 试运行，`-f` 跳过确认 |
| `list` | 列出所有快照 |
| `type <目录> [Source\|Target]` | 获取或设置仓库类型 |

## 架构

| 模块 | 职责 |
|--------|------|
| `hashing` | `hash_file()` / `hash_bytes()` -- SHA256 哈希计算 |
| `Scanner` | 遍历目录树，返回 `{相对路径: 哈希}`，跳过工具目录 |
| `SnapshotManager` | 保存/加载时间戳命名的 JSON 快照（原子写入）。管理 `config.json` 仓库类型。隐藏 `.backup/` |
| `Differ` | 比较两个 `{路径: 哈希}` 映射 -> 新增/修改/仅目标/未变化 |
| `Syncer` | 复制新增和修改的文件到目标。支持 dry-run。不删除。追踪逐文件错误 |
| `_win32` | Windows 专用辅助（隐藏目录，记录日志错误） |

## 测试数据

```
testdata/
  source/     （7 个文件，分布在 docs/、config/、images/ 下）
  target/     （同步后的副本）
```

## 运行环境

- Python 3.10+
- 仅标准库 -- `hashlib`、`os`、`shutil`、`json`、`tkinter`、`argparse`
- 107 个测试，全部通过

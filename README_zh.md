# distbackup

基于 SHA256 哈希比较的目录备份工具，单向安全同步。

## 原理

1. **扫描** 文件夹 —— 对每个文件计算 SHA256，结果自动保存为时间戳命名的
   JSON 快照（如 `20260627_113025`）。
2. **比较** 任意两个快照，得出新增、修改、仅目标有、未变化四类差异。
3. **备份** —— 将新增和修改的文件从源复制到目标。目标侧独有的文件不删除。

备份前 GUI 会检查：文件夹是否在本次会话中重新扫描过、当前快照是否最新。
不满足时弹窗警告，用户确认后继续。

## 快速开始

```powershell
# 图形界面
python -m distbackup

# 命令行
python -m distbackup cli scan D:\我的数据  笔记本快照
python -m distbackup cli scan D:\nas\备份  NAS快照
python -m distbackup cli diff  笔记本快照 NAS快照 --store D:\我的数据
python -m distbackup cli sync D:\我的数据 D:\nas\备份 笔记本快照 NAS快照
```

## 存储结构

```
源文件夹/
  .backup/                  # Windows 下自动隐藏
    snapshots/              # 时间戳命名的 JSON 快照
      20260627_113025.json
      20260627_114201.json
```

每个快照记录：
- `created` — UTC 时间戳
- `root` — 被扫描目录的绝对路径
- `files` — `{相对路径: SHA256十六进制摘要}` 映射

不存储原始文件副本 — 快照 JSON 是哈希映射的唯一数据源。

## 界面操作

1. **Browse** 选择源和目标文件夹，自动加载各自最新快照。
2. **Scan**（可选）重新扫描，自动保存新的时间戳快照。
3. 下拉框显示当前快照，`(new)` 标记表示最新快照。下拉选择即加载。
4. **Compare** 查看差异树形列表。
5. **Start Backup** 执行同步。快照过期或未扫描会弹警告。

## 架构

| 模块 | 职责 |
|------|------|
| `hashing` | `hash_file()` / `hash_bytes()` — SHA256 哈希计算。 |
| `Scanner` | 遍历目录树，返回 `{相对路径: 哈希}`。 |
| `SnapshotManager` | 保存/加载时间戳命名的 JSON 快照，隐藏 `.backup/`。 |
| `Differ` | 比较两个快照，输出新增/修改/仅目标/未变化。 |
| `Syncer` | 复制新增和修改的文件到目标，不删除目标文件。 |

## 测试数据

```
testdata/
  source/     （7 个文件，分布在 docs/、config/、images/ 下）
  target/     （同步后的副本）
```

## 运行环境

- Python 3.10+
- 仅标准库 — `hashlib`、`os`、`shutil`、`json`、`tkinter`、`argparse`

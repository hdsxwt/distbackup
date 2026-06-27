# 特性

## 仓库身份识别

distbackup 管理的每个仓库可在 `.backup/config.json` 中携带唯一的身份识别码
（`repo_id`）。此识别码代表仓库血统，用于防止将不同源目录的文件
意外混入同一个备份目标。

### 识别码生命周期

| 事件 | 行为 |
|------|------|
| 新建仓库（Target） | 无 `repo_id` |
| `set_repo_type("Source")` | 生成 UUIDv4 并持久化 |
| 扫描 / 加载 Source 仓库 | `repo_id` 已存在 |
| 首次备份到 Target | Target 继承 Source 的 `repo_id` |
| 同血统后续备份 | 允许 -- `repo_id` 一致 |
| 从不同 Source 备份 | **拒绝** -- `repo_id` 不一致 |

### 设计动机

若没有血统强制检查，很容易将两个无关的源目录备份到同一个目标目录中，
产生来源混乱的文件集合。`repo_id` 机制确保每个备份目标始终绑定
唯一的源血统。

---

## 安全保护

### 路径穿越拦截

复制文件前，同步引擎会校验目标路径是否确实落在目标目录内。
被篡改的快照 JSON 中若包含 `..` 逃逸序列会被检测并拦截。

被拦截的路径穿越记录在同步统计中，消息为 `"path traversal blocked"`，
同时输出警告日志。

### 快照 Root 校验

每份快照在 `root` 字段中记录其来源目录。sync 前会校验源和目标两个快照
的 root 是否与当前操作的目录一致。不匹配时抛出 `ValueError` 并附带描述信息。

### 扫描器透明化

扫描器此前在遇到不可读文件时静默跳过。现在，所有因 `OSError` 或
`PermissionError` 导致哈希失败的文件都会以警告日志记录：

```
WARNING  distbackup.core.scanner: Skipping unreadable file: C:\...\locked.txt (Permission denied)
```

这让用户清楚知道扫描跳过了哪些文件及其原因。

### 源仓库写保护

`config.json` 中标记为 `"Source"` 的目录拒绝所有写入同步操作。此检查
在 CLI 和 GUI 流程中均在文件复制前执行。

### 血统强制检查

参见上方的[仓库身份识别](#仓库身份识别)。

---

## 快照管理

快照以时间戳命名的 JSON 文件存储在 `.backup/snapshots/` 下。
每次写入使用临时文件 + `os.replace()` 实现原子性 -- 快照创建过程中的
崩溃不会留下残缺的 JSON 文件。

`SnapshotManager` API 还提供：
- `list_snapshots()` - 排序后的全部快照名称列表
- `validate_root(name, directory)` - 断言快照是为指定目录创建的
- `get_repo_id()` / `ensure_repo_id()` / `set_repo_id()` - 身份识别码管理
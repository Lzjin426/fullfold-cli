---
name: fullfold-cli
description: Read and write a Fullfold.md library from agents or scripts with the fullfold-cli binary. Use when the user asks to edit notes, patch blocks, manage boards, links, attachments, calendar notes, trash, conflicts, or PDF annotation sidecars in a Fullfold library. Never edit library files directly; call the CLI.
---

# fullfold-cli

## 何时使用

用户要在 Fullfold 文档库里读取或修改数据，而不是操作界面时：

- 笔记：列出、读取、搜索、大纲、追加、块级 patch、整篇替换、改名、移动、回收站。
- 画板：列出、读取 JSON Canvas、按节点/边 patch。
- 链接、附件、日历/日笔记、回收站、冲突稿。
- PDF：只读信息与 4+1 标注 sidecar（PDF 原文件永不改写）。
- 不负责 UI：标签、窗口、主题、缩放、阅读模式不属于 CLI。

## 第一原则

**不要用 `cat`、`sed`、`python`、重定向或任何直接文件写入去改库内 `.md`、`.canvas`、`.quiet/**` 或 PDF sidecar。** 先调用 `fullfold-cli`；它经过 `fdl_core` 的模型、Markdown、Canvas 和标注 API，能保留富内容、未知字段、冲突稿和原子写。

## 先发现命令

```sh
fullfold-cli capabilities --json
```

这是命令、参数、schema、features、退出码和 unsupported 列表的事实源。不要凭记忆猜子命令；用 `capabilities --command "doc.patch" --json` 看单个命令。

## 库与安全

- 库路径用 `--library <path>`；不传时按 `QUIET_MD_HOME` / 默认库发现。不要假设用户的库路径。
- 自动化测试和脚本一律用临时库；不要碰 `~/Documents/Quiet.md`、`~/Desktop/md 测试` 或用户正在使用的库。
- 写前先读，记下 `hash`；并发修改用 `--expect sha256:...`，不匹配时 CLI 退出 4 且不写。
- 不确定的写入先加 `--dry-run`，确认输出里的 `dryRun:true` 和计划结果。
- `doc.write` 是整篇覆盖，必须 `--replace`；能块级改就用 `doc.patch` 或 `doc.append`，避免丢 callout、分栏、合并表格、附件、图片裁剪和 rich HTML。
- 删除/清空/永久删除必须 `--yes`；不要替用户猜。
- 冲突默认保留冲突稿；不要用 `--conflict-copy never` 覆盖证据。
- 不要在用户库里生成 `AGENTS.md`、`CLAUDE.md` 或 `agent.md`。

## 多 AI 并发

- 同一个库只有一把跨进程写锁。打开库、扫描索引也会短暂持锁，所以多个 AI 即使改不同文档，命令也会排队，不是真并行；通常毫秒级，大库扫描或批量导入会等更久。
- 写命令在“读 → 改 → 校验 → 写盘”全程持锁；读命令只在打开/扫描时短暂持锁。
- 每次写盘前会复读磁盘，发现被改就退出 4，不覆盖。跨命令的“先读后写”用 `--expect` 带上读到的 hash。
- 多个 AI 改同一文档：一个成功，另一个退出 4；重读拿新 hash 再试。不要用 `doc write --replace` 硬覆盖。
- 跨机器共用同步盘：锁只在本机生效，CLI 不做跨机协调；冲突同样靠复读/退出 4 发现。
- 权限只有库级「命令行访问」开关，没有按 AI 或按文档的授权。

## 常用流程

```sh
# 库概况
fullfold-cli --json --library /path/to/lib library info
fullfold-cli --json --library /path/to/lib doc list --kind note

# 读文档
fullfold-cli --json --library /path/to/lib doc read --id <id> --format md
fullfold-cli --json --library /path/to/lib doc read --id <id> --format model

# 块级修改（推荐；先 dry-run）
fullfold-cli --json --library /path/to/lib doc patch --id <id> --ops ops.json --dry-run
fullfold-cli --json --library /path/to/lib doc patch --id <id> --ops ops.json --expect sha256:<hash>

# 追加 Markdown 文件或 stdin
fullfold-cli --json --library /path/to/lib doc append --id <id> --markdown notes.md

# 整篇替换（必须 --replace）
fullfold-cli --json --library /path/to/lib doc write --id <id> --source new.md --replace --expect sha256:<hash>

# 画板 / 日历 / PDF 标注
fullfold-cli --json --library /path/to/lib board read --id <id> --format summary
fullfold-cli --json --library /path/to/lib board patch --id <id> --ops board-ops.json --expect sha256:<hash>
fullfold-cli --json --library /path/to/lib calendar read --date 2026-11-16
fullfold-cli --json --library /path/to/lib pdf annotations list --path paper.pdf
```

## 样式配方（本库默认风格）

这些样式普通 Markdown 写不出来，必须用块 JSON；先 `--dry-run`。字段真相以 `capabilities --json` 的 schemas 为准。

### 自动编号标题

普通 `##` 不会自动编号。插入时用 `seqAuto`：

```json
{ "op": "insert", "target": { "path": [2], "hash": "sha256:…" }, "position": "after",
  "block": { "kind": "heading", "level": 2, "seqAuto": true, "text": "小节标题" } }
```

已有标题改用 `set`，字段是 `seq_auto`：

```json
{ "op": "set", "target": { "path": [2], "hash": "sha256:…" }, "fields": { "seq_auto": true } }
```

### 居中图片 + 图注

```json
{ "op": "insert", "target": { "path": [2], "hash": "sha256:…" }, "position": "after",
  "block": { "kind": "image", "srcKind": "src", "src": "assets/图.png", "caption": "图 1 说明", "align": "center" } }
```

- 图注就是 `caption`；图片居中只能写在块 JSON 的 `align`（`set` 白名单没有图片 align）。
- 图片一旦带居中/尺寸/裁剪，整块会存成富 HTML，这是正常状态，不要“修回”纯 Markdown。

### 高亮块 / 分栏

```json
{ "kind": "callout", "emoji": "💡", "bg": "light-yellow", "children": [ { "kind": "text", "text": "内容" } ] }
```

```json
{ "kind": "columns", "children": [
  { "kind": "column", "ratio": 0.5, "children": [ { "kind": "text", "text": "左" } ] },
  { "kind": "column", "ratio": 0.5, "children": [ { "kind": "text", "text": "右" } ] } ] }
```

颜色名必须是 palette 认识的名称；未知名称退出 5。分栏只能用 `replace-block` 或插入新块，不能靠 `replace` 把文本改成结构。

## 画板（JSON Canvas）

当前构建的能力（以 `capabilities --json` 为准）：`board list`、`board read`、`board patch` 可用；`board create`、`board replace`、`board rename`、`board trash` 未实现（退出 8）。新建画板用 GUI 的斜杠「画板」，CLI 只在已有画板上工作。

- 找画板：`board list --folder <id|path>`，返回 id 和库内相对 path。
- 读：`board read --id <id> --format json`，得到 JSON Canvas 的 nodes/edges；节点有稳定 id。
- 改：`board patch --ops ops.json`（`add-node`、`move-node`、`set-node`、`delete-node`、`connect`、`delete-edge`）；先 dry-run，写时带 `--expect`。
- 嵌入正文：用 `doc patch` 插入一个 file 块。`src` 用画板文件的绝对路径：`library info` 的 `root` 拼接 `board list` 返回的相对 path。

```json
{ "op": "insert", "target": { "path": [2], "hash": "sha256:…" }, "position": "after",
  "block": { "kind": "file", "srcKind": "canvas", "src": "<root>/<相对 path>.canvas", "name": "画板.canvas", "view": "preview" } }
```

不要直接改 `.canvas`；不要手写节点/边的 id。

## Excalidraw（内嵌块）

当前构建还不支持：CLI 没有对应的块 schema/命令，不要在 `.md` 里手写 HTML，也不要直接改文件。M1 交付后按 `capabilities` 更新本 skill；Excalidraw JSON 即使 AI 熟悉，也必须经过本库的包装层与往返校验。

## 版本与更新

- 本 skill 的版本在 `VERSION`（当前 0.1.0）；master 是独立公开仓库 https://github.com/Lzjin426/fullfold-cli（本地 `~/.skillsbase/skills/fullfold-cli`）。
- 首次使用或怀疑过期：运行 `python3 scripts/check_update.py`（只读、几秒）。有新版就告诉用户，不要自动改。
- 修改本 skill 后：升 `VERSION`，再跑 `python3 scripts/check_push_version.py`，输出 `VERSION_OK` 才推送 skills 仓库。
- 推送后把 `SKILL.md`、`VERSION`、`scripts/` 同步到 Qoder 副本 `~/.qoder-cn/skills/fullfold-cli`（目前是复制，不是链接）。
- 项目侧规则：正文格式、默认样式、富块 schema 或 CLI 命令面变化时，同步 CLI、CLI 合同与本 skill（见项目 AGENTS.md）。

## 结果与退出码

- 一律优先加 `--json`：stdout 是一个 envelope：`{schemaVersion, ok, data, warnings, error}`。
- `ok:true` 看 `data`；`ok:false` 看 `error.code`、`error.hint`、`error.conflictCopy`。
- 退出码：0 ok、2 usage、3 not_found、4 conflict、5 invalid、6 permission、7 forbidden、8 unsupported、9 partial、10 internal。
- `8 unsupported` 表示本构建没有该能力（例如表格结构 ops、HTML/PDF 导出、compat 导入）；不要用别的命令拼一个降级版本。
- `4 conflict` 表示目标在读写之间被改动；重新读、拿新 hash、再试，不要覆盖磁盘。
- 同一个库多个 AI 同时写时，排队是正常现象；退出 4 不是失败，是“先重读再改”的信号。

## 找不到命令或二进制

- 先运行 `fullfold-cli --help` 和 `capabilities --json`；仍没有就明确告诉用户本构建不支持，不要用直接文件写入兜底。
- 找不到 `fullfold-cli` 时，问用户二进制路径；源码构建可用 `target/release/fullfold-cli`，不要假设它在 PATH。

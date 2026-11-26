---
name: fullfold-cli
description: Read and write a Fullfold.md library from agents or scripts with the fullfold-cli binary. Use when the user asks to edit notes, patch blocks, manage boards, links, attachments, calendar notes, trash, conflicts, or PDF annotation sidecars in a Fullfold library. Never edit library files directly; call the CLI.
---

# fullfold-cli

## 何时使用

用户要在 Fullfold 文档库里读取或修改数据，而不是操作界面时：

- 笔记：列出、读取、搜索、大纲、追加、块级 patch、整篇替换、改名、移动、回收站。
- 画板：列出、读取、创建、改名、回收站；`.canvas` 节点/边 patch 与 `.excalidraw` 元素级 patch。
- 链接、附件、日历/日笔记、回收站、冲突稿。
- PDF：只读信息与 4+1 标注 sidecar（PDF 原文件永不改写）。
- 不负责 UI：标签、窗口、主题、缩放、阅读模式不属于 CLI。

## 第一原则

**不要用 `cat`、`sed`、`python`、重定向或任何直接文件写入去改库内 `.md`、`.canvas`、`.excalidraw`、`.quiet/**` 或 PDF sidecar。** 先调用 `fullfold-cli`；它经过 `fdl_core` 的模型、Markdown、Canvas 和标注 API，能保留富内容、未知字段、冲突稿和原子写。

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
fullfold-cli --json --library /path/to/lib board create --title "草图" --folder <id> --elements elements.json --dry-run
fullfold-cli --json --library /path/to/lib calendar read --date 2026-11-16
fullfold-cli --json --library /path/to/lib pdf annotations list --path paper.pdf
```

## 样式配方（本库默认风格）

这些样式普通 Markdown 写不出来，必须用块 JSON；先 `--dry-run`。字段真相以 `capabilities --json` 的 schemas 为准。

### 自动编号标题

导入或整理已有章节编号的文档时，不要仅按默认风格直接开启自动编号。若用户尚未明确本次选择，操作前说明并询问：保留原书编号，还是改用 Fullfold 自动编号。结合文档说明可能的显示变化及其对正文引用、公式和图表编号的影响。用户已有明确选择时遵照执行，不重复询问。

当前 Fullfold 的自动编号按当前文档启用编号的标题从 1 重新计算，不能指定任意起始章号。例如原书第 3 章的 `3.1` 可能显示为 `1.1`，而书中公式和图表仍为 `3.x`；实际行为随版本变化时重新核实。保留原书编号时，不给仍带静态数字的标题启用自动编号；选择自动编号并接受变化时，先移除标题文字中的原编号，再按真实层级设置自动编号，避免重复显示。不要添加虚构标题凑编号，也不改动书中的公式、图表或引用编号。

普通 `##` 不会自动编号。插入时用 `seqAuto`：

```json
{ "op": "insert", "target": { "path": [2], "hash": "sha256:…" }, "position": "after",
  "block": { "kind": "heading", "level": 2, "seqAuto": true, "text": "小节标题" } }
```

已有标题改用 `set`，字段是 `seq_auto`：

```json
{ "op": "set", "target": { "path": [2], "hash": "sha256:…" }, "fields": { "seq_auto": true } }
```

写入后用 `doc outline` 或 `doc read --format model` 检查标题文字、层级和 `seqAuto`。标题上看得到数字，只能说明有数字，不代表开启了自动编号。

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

## 画板（JSON Canvas 与 Excalidraw）

画板分两类，以 `board list` 返回的 `kind` 为准：`canvas`（旧 AFFiNE 画板）和 `excalidraw`（独立 `.excalidraw` 文件）。`capabilities --json` 的 `features.boards` / `features.excalidrawWrites` 说明本构建支持到什么程度。

- 找画板：`board list --folder <id|path>`，返回 id、库内相对 path 和 `kind`。
- 读：`board read --id <id>|--path <库内路径> --format json|summary`。`.canvas` 给 JSON Canvas 的 nodes/edges；`.excalidraw` 给官方 Excalidraw JSON（type/version/source/elements/appState/files），`summary` 给 elements/files/text。
- 嵌入正文：用 `doc patch` 插入 file 块，`src` 用绝对路径：`library info` 的 `root` 拼 `board list` / `board create` 返回的库内相对 path。

```json
{ "op": "insert", "target": { "path": [2], "hash": "sha256:…" }, "position": "after",
  "block": { "kind": "file", "srcKind": "canvas", "src": "<root>/<相对 path>.canvas", "name": "画板.canvas", "view": "preview" } }
```

### `.canvas`（旧画板）

- `board patch` 支持节点/边 ops：`add-node`、`move-node`、`set-node`、`delete-node`、`connect`、`delete-edge`；未知节点/边 id 退出 3。
- `board create --type canvas`、`.canvas` 的 `board rename` / `board trash` 退出 8；新建与生命周期仍走 GUI。

### `.excalidraw`（独立文件）

- 文件在笔记同名子文件夹（`笔记名/画板 1.excalidraw`）；正文引用卡片和侧栏子项由应用维护，卡片用 GUI 插入，不要在 CLI 里手写 HTML。
- 创建：`board create --title <名称> [--folder <id|path>] [--elements <文件|->] [--dry-run]`。只建 `.excalidraw`；命名冲突（含同名目录）自动递增为 `标题 (2)`；返回 `boardId` / `title` / `path` / `hash` / `elements`，`path` 是库根相对路径。
- 改名：`board rename --id|--path --title <名称> [--expect] [--dry-run]`，引用卡片随迁。回收站：`board trash --id|--path [--expect] [--dry-run]`，进系统废纸篓，笔记与卡片保留。Windows 上网络共享、`Volume{GUID}`、超过 `MAX_PATH` 的路径没有可靠回收站，命令退出 8，要在文件管理器里手动删除。
- 元素级修改：`board patch --ops <文件|-> [--dry-run] [--expect sha256:…]`，ops 有：
  - `add-element`：`element` 可以是官方完整元素（`version` / `versionNonce` / `seed` 等原样保留），也可以是 MCP 简化元素（`type/id/x/y/width/height`，形状可带 `label`，箭头可带 `start` / `end`）。`label` 生成居中绑定文字；箭头端点可指向同一批或画板已有元素，CLI 维护反向 `boundElements`。`id` 必须唯一，省略时自动生成。`cameraUpdate` 伪元素忽略；`delete` 伪元素只用于 `board create --elements` 点名“不要创建”的 id，`add-element` 不接受它（删已有元素用 `delete-element`）。图片只能引用画板 `files` 里已有的 `fileId`；内联 dataURL 与新增图片文件不支持。
  - `set-element`：`id` + `fields`（官方字段）。已知字段按模型类型严格校验（`points` 至少两个 `[x, y]`、枚举必须是认识的值、`fontFamily` 必须是整数等），不合规退出 5 且整批不写；不能改 `id` / `type` / `version` / `isDeleted` 和绑定字段（`startBinding` / `endBinding` / `boundElements` / `containerId` / `frameId`）；文本不能置空（用 `delete-element`）；只给 `text` 时同步 `originalText`。改几何不会带动已绑定箭头端点。
  - `delete-element`：按官方删除语义连带删绑定文字、清理指向它的绑定；删画框时子元素留在画板。
  - `set-app`：`fields` 只接受 `viewBackgroundColor`、`gridSize`、`gridStep`（1–100，取整）、`gridModeEnabled`。
- 写回采用应用的 canonical 形式：`source` 改写，`isDeleted` 元素、未被引用的 `files`、未知 `appState` 与顶层键不保留；要逐字节保真就别用 patch。画板里有未落盘的 dataURL 图片时写回退出 5，先用 GUI 打开一次让图片进库内 `assets`。
- 任一 op 失败整批不写；读写之间磁盘变化按 `disk_changed` 退出 4；没有实际变化不写盘。
- `board replace` 仍退出 8；不要直接改 `.canvas` / `.excalidraw`，不要手写节点/边/元素 id。

## 版本与更新

- 本 skill 的版本在 `VERSION`（当前 0.1.3）；master 是独立公开仓库 https://github.com/Lzjin426/fullfold-cli（本地 `~/.skillsbase/skills/fullfold-cli`）。
- 首次使用或怀疑过期：运行 `python3 scripts/check_update.py`（只读、几秒）。有新版就告诉用户，不要自动改。
- 修改本 skill 后升 `VERSION`；需要发布本 skill 的独立仓库时，先按用户授权运行 `python3 scripts/check_push_version.py`，输出 `VERSION_OK` 才发布。不要向已停止维护的 `.skillsbase/skills` 共享库推送。
- Qoder 入口如果指向本技能目录，会随本地修改生效；如果是独立副本，再按实际部署方式同步。
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
- 找不到 `fullfold-cli` 时，先看应用 设置 › 文档库 › 安装命令行工具：它把随应用附带的 CLI 装到 Windows `%LOCALAPPDATA%\Fullfold\bin\fullfold-cli.exe`（macOS `~/.local/bin/fullfold-cli`）并加进 PATH，应用升级后自动刷新。仍找不到再问用户二进制路径；源码构建可用 `target/release/fullfold-cli`，不要假设它在 PATH。

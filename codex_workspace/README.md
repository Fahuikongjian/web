# `codex_workspace/` — Codex Bridge 隔离工作区

本目录是 Antigravity 全局插件 **`codex-bridge`**（本地 ChatGPT Codex CLI，默认模型 `gpt-6.2-sol`）在当前仓库中的**专用旁路隔离工作区**。

## 用途与边界

- **隔离写入**：所有由 Codex 生成的代码草稿、重构候选、单元测试或独立 Code Review 报告，均默认落盘于本目录（及其子目录）下，不会直接修改正式源码树。
- **审阅合入**：Antigravity 编排器会对本目录内的输出进行审阅、校验与测试；仅当确认无误后，才由编排器将改动合入正式目录。
- **Git 忽略策略**：仓库根目录 `.gitignore` 已配置 `codex_workspace/*` 与 `!codex_workspace/README.md`，确保临时产物与草稿不会污染正式 Git 提交与推送，同时保留本说明文件。
- **清理建议**：当某项任务产物已合入正式代码或确认废弃后，可随时清理本目录下除 `README.md` 之外的临时文件。

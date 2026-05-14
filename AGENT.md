# Wudao Dict Plus Agent Guide

本文件用于约束在本仓库中进行修改的 Agent 或贡献者，目标是保持实现风格稳定、目录职责清晰、提交历史可读。

## 架构风格

- 项目是一个以 CLI 为入口的终端词典工具，主流程是 `CLI -> Client -> Server -> Dict Provider / Local DB -> Draw`。
- `wudao_dict/cli.py` 负责参数解析、一次查询的流程组织，以及结果展示入口；不要在这里堆积底层抓取、数据库或音频实现。
- `wudao_dict/client.py` 负责与后台服务通信；它应保持轻量，只处理 socket 生命周期、消息发送与接收。
- `wudao_dict/server.py` 负责查询编排，是“线上查询、本地回退、数据库更新”等策略逻辑的中心位置。
- `wudao_dict/dict/local.py` 负责 SQLite 读写；本地词典相关 SQL 应集中在这里，不要散落到 CLI 或 Server。
- `wudao_dict/dict/youdao/youdao.py` 负责第三方词典抓取与解析；网络请求、HTML 解析和 provider 级错误处理应留在该层。
- `wudao_dict/draw.py` 只负责渲染输出，不承担业务决策。
- `wudao_dict/core/` 放置配置、路径、类型定义和基础设施代码；跨模块共享的常量与接口优先放这里。

## 设计原则

- 优先保持分层清晰，而不是把功能“就近写进能跑的文件”。
- 查询策略优先放在 `server.py`，不要让 `cli.py` 直接拼接 provider 或数据库逻辑。
- provider 失败应返回可处理的空结果或 `None`，由上层决定 fallback；不要轻易让抓取层异常直接打断主流程。
- 新功能如果同时涉及“下载 / 缓存 / 播放 / 展示”，应拆成独立模块，不要把多个职责塞进一个函数。
- 增加新 provider、新缓存或新播放后端时，优先复用现有抽象和目录边界。

## 编码风格

- Python 版本下限是 3.8；新增语法和标准库能力必须兼容 3.8。
- 延续现有代码风格：类型标注尽量完整，公开函数写简短 docstring。
- 默认遵循 PEP 8，并以仓库里的 `autopep8` 配置为准；单行长度上限按 `pyproject.toml` 中的 `180` 处理。
- 变量、函数、模块名使用清晰直白的英文；用户可见文案和日志可使用中文。
- 不要为了“优雅”重写整段旧代码；优先做局部、可验证的修改。
- 解析外部数据时保持容错，避免因第三方页面细节变化直接崩溃。
- 错误处理要分层：底层负责收敛具体异常，上层负责决定回退、报错或提示。
- 新增辅助函数时，优先提取可复用的查询、缓存、格式化逻辑，避免复制分支代码。
- 除非该文件已经广泛使用，否则不要引入不必要的复杂模式或额外依赖。

## 测试与验证

- 任何修改至少应做最小静态验证，例如 `python -m py_compile` 覆盖改动文件。
- 涉及 CLI、server、网络 fallback、数据库写入等行为时，提交前应尽量做一次手工路径验证。
- 如果没有自动化测试，提交说明里应明确写出已验证的场景和未验证的风险点。

## Git Commit Message 风格

- Commit messages must be written in English.
- There are two preferred styles in this repository, based on scope.
- If the change only touches a single file or a single focused feature, use a short one-line subject starting with a capitalized type prefix such as `Fix:`, `Feat:`, `Refactor:`, `Docs:`, `Chore:`, or `Test:`.
- If the change spans multiple files or contains several related updates, use `change log` as the subject and write a detailed body below it.
- The multi-file style should follow the existing history in `git log`: keep the title exactly as `change log`, then add a blank line, then a `Changes:` section, and then list concrete file-level or behavior-level updates.
- Keep the subject line concise and specific; avoid vague summaries such as `update code` or `misc changes`.

Recommended short one-line examples:

- `Fix: fallback to local DB when online query fails`
- `Feat: add local cache for pronunciation audio`
- `Docs: clarify daemon mode usage`

Recommended multi-file example:

- `change log`

  `Changes:`

  `    wudao_dict/server.py: Fallback to local DB if online query fails.`
  `    wudao_dict/dict/youdao/youdao.py: Catch more exception types.`

Alternative multi-file example:

- `change log`

  `Changes:`

  `    1. Finish online query for Chinese words.`
  `    2. Add foreground daemon mode.`

## 修改约束

- 不要顺手重排大量无关代码或做纯格式化提交，除非用户明确要求。
- 不要修改公共行为的默认值，除非同时更新文档和相关提示文案。
- 涉及配置目录、缓存路径、数据库结构或网络策略的变更时，应优先考虑向后兼容。

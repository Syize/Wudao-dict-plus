# TODO: Pronunciation Feature Plan

本文档用于规划无道词典的发音功能实现。目标是在尽量保持现有架构分层的前提下，为英文字词提供可缓存、可播放、可跨平台运行的发音能力。

## 目标与约束

- 发音文件的下载由 `server` 负责，不放到 `client` 或 `cli` 中。
- 发音播放由 `server` 负责，但触发时机应发生在 `client` 完成词义绘制之后。
- 发音口音通过全局配置控制，至少支持 `uk` / `usa`。
- 功能优先服务英文词条；中文查询暂不要求发音。
- 方案需要兼容 Linux、macOS、Windows。
- 不把发音文件写进 SQLite；音频应作为独立缓存管理。

## 总体设计

建议把发音能力拆成四层：

1. `provider` 层：给定英文单词和口音，生成或获取 provider 的音频下载地址。
2. `server` 调度层：决定是否下载、是否命中缓存、是否异步播放。
3. `audio cache` 层：管理文件路径、元数据、容量限制、过期策略。
4. `audio backend` 层：屏蔽不同平台的播放器差异，对外暴露统一的播放接口。

建议新增模块：

- `wudao_dict/audio/cache.py`
- `wudao_dict/audio/player.py`
- `wudao_dict/audio/service.py`

可选新增：

- `wudao_dict/audio/__init__.py`

其中：

- `cache.py` 只负责缓存路径、索引、清理。
- `player.py` 只负责播放器探测和播放调用。
- `service.py` 作为 `server` 的调用入口，负责“确保文件存在”和“播放文件”。

## Part 1: 发音文件下载

### 需要改动的部分

- `wudao_dict/dict/youdao/youdao.py`
- `wudao_dict/server.py`
- `wudao_dict/core/interface.py`
- 新增 `wudao_dict/audio/service.py`

### 实现方式

#### 1.1 在 provider 层补充发音地址能力

不要把“下载音频文件”的实现直接写进 provider 查询主函数里。建议先在 provider 层只暴露“生成音频 URL”或“返回音频资源描述”的能力。

建议在 `youdao.py` 中新增类似接口：

- `get_pronunciation_audio_url(word: str, accent: Literal["uk", "usa"]) -> str`

如果有道的音频接口 URL 可直接由单词和口音拼出，则优先用“直接构造 URL”的方式，不必先抓 HTML 再解析下载地址。这样实现更稳定，也更容易单测。

#### 1.2 下载逻辑放到 server 侧的 audio service

建议在 `audio/service.py` 中新增：

- `ensure_pronunciation_file(word: str, accent: Literal["uk", "usa"]) -> str`

职责：

- 计算缓存 key 和目标路径
- 判断本地缓存是否可用
- 若不可用，则向 provider 请求下载地址
- 使用 `requests.get(..., stream=True)` 下载音频文件
- 原子写入缓存目录
- 更新元数据索引
- 返回本地音频文件路径

#### 1.3 查询时的下载调度

建议在 `server` 端查询成功后再做发音预取，而不是在 provider 查询前下载。

推荐流程：

1. `server` 处理 `query`
2. 返回词义 JSON
3. 如果是英文词条，并且配置开启了发音功能，则调用 `ensure_pronunciation_file(...)`

这里建议将“下载”和“播放”分离：

- 下载可以在返回释义前完成，以保证后续播放命中缓存
- 也可以先回包再后台下载，但这会让第一次播放时序更复杂

第一版建议：

- 查询成功后同步确保文件存在
- 播放由独立命令触发

这样最简单，也最符合当前 socket 请求-响应模型。

### 技术选择

- `requests`：继续复用现有依赖下载音频
- `stream=True`：避免一次性把整个音频读进内存
- 临时文件 + `os.replace()`：保证下载过程原子化，避免半写入缓存

### 风险与注意点

- provider 的音频 URL 可能变化，建议把 URL 构造逻辑封装在 provider 层
- 断网时下载失败不应影响词义查询结果
- 如果 provider 没有某个口音的音频，需回退到另一个口音或跳过播放

## Part 2: 发音文件缓存

### 需要改动的部分

- `wudao_dict/core/config.py`
- 新增 `wudao_dict/audio/cache.py`
- 可选新增缓存元数据文件，例如 `audio_index.json`

### 缓存目录设计

建议把音频缓存放在配置目录下，而不是仓库目录：

- `CONFIG_DIR/audio/`

建议结构：

```text
audio/
  youdao/
    uk/
      ab/
        abcdef123456.mp3
    usa/
      cd/
        cdefab987654.mp3
  audio_index.json
```

目录分层的目的：

- 避免单目录文件过多
- 明确区分 provider 和 accent
- 后续支持多个 provider 时不需要迁移结构

### 缓存 key 设计

建议用以下字段生成稳定 key：

- provider
- accent
- normalized word

例如：

- `sha256("youdao:uk:test")`

不要直接用原单词做文件名，避免空格、大小写、引号和非 ASCII 字符带来的路径问题。

### 元数据设计

建议单独维护一个 JSON 索引文件，记录：

- `word`
- `provider`
- `accent`
- `path`
- `etag` 或 `source_version`（如果 provider 能提供）
- `created_at`
- `last_accessed_at`
- `file_size`

第一版可以不做 SQLite 元数据，JSON 已足够；后续如果缓存策略复杂，再考虑迁移。

### 时效性策略

第一版建议不要主动做“远程更新检查”，只做本地长期缓存。

原因：

- 发音文件更新频率极低
- 每次都访问远端检查新版本会增加复杂度和延迟
- 当前项目更需要稳定而不是“最新音频”

推荐策略：

- 默认认为音频缓存长期有效
- 仅在文件缺失、损坏或用户手动清理缓存时重新下载

可预留后续配置项：

- `audio_refresh_days`
- `audio_force_redownload`

但第一版不必启用。

### 容量控制

建议按总字节数做上限，不按文件数。

推荐配置项：

- `audio_cache_enabled: bool`
- `audio_cache_max_mb: int`

清理策略建议使用近似 LRU：

- 每次命中缓存时更新 `last_accessed_at`
- 下载新文件前计算总占用
- 若超过上限，则按 `last_accessed_at` 从旧到新删除

第一版可先做“下载前清理”，不必上后台定期清理任务。

### 技术选择

- `hashlib.sha256`：生成缓存 key
- `json`：缓存索引
- `os.replace`：原子写入
- `os.walk` / 元数据累加：计算缓存体积

## Part 3: 发音文件播放

### 需要改动的部分

- 新增 `wudao_dict/audio/player.py`
- 新增 `wudao_dict/audio/service.py`
- `wudao_dict/server.py`
- `wudao_dict/client.py`
- `wudao_dict/cli.py`
- `wudao_dict/core/interface.py`
- `wudao_dict/core/config.py`

### 播放职责划分

按你的要求，播放由 `server` 负责。但要满足“client 绘制完词义后再播放”，协议需要拆成两个阶段：

1. `query` 请求：返回词义内容
2. `play_pronunciation` 请求：在 client 绘制完成后显式通知 server 播放

不要让 `server` 在处理 `query` 时立刻播放，否则它无法知道 client 是否已经绘制完。

### 推荐协议改动

在 `core/interface.py` 中新增消息类型：

- `PlayPronunciationMessage`

字段建议：

- `cmd: Literal["play_pronunciation"]`
- `word: str`

可选字段：

- `accent: Literal["uk", "usa", "auto"]`

但如果口音由全局配置统一控制，那么 message 中可以不传 accent，由 server 读取全局配置决定。

### Client 侧触发时机

建议 `cli.py` 的 `query()` 流程调整为：

1. 调用 `client.get_word_info(...)`
2. 完成 `draw_text()` 或 `draw_zh_text()`
3. 如果是英文词条且配置开启自动播放，则调用 `client.play_pronunciation(word)`

这样可以严格满足“绘制完词义输出以后再播放”的要求。

### Server 侧播放流程

建议在 `server.py` 中新增处理分支：

1. 接到 `play_pronunciation`
2. 读取全局配置决定 accent
3. 调用 `ensure_pronunciation_file(word, accent)`
4. 调用 `play_audio(path)`
5. 返回空响应或简短确认消息

### 跨平台播放后端

建议 `player.py` 实现一个后端探测器，按平台分别处理，并将探测结果持久化到全局配置中。

最终平台策略如下：

#### macOS

- 默认只使用系统自带的 `afplay`
- 不做多后端探测
- 如果 `afplay` 不可用，则由 `server` 返回结构化错误，由 `client` 显式提示用户检查 `afplay` 或本机音频环境

#### Linux

- 按顺序探测 `mpv` -> `ffplay` -> `paplay`
- 第一次探测到可用后端后，将结果写入配置，例如 `audio_player_backend`
- 后续优先使用已固定的后端，避免因系统环境变化导致播放后端来回切换
- 如果固定后端执行失败或命令不存在，则清空该配置并重新探测
- 如果所有候选后端都不可用，则由 `server` 返回结构化错误，由 `client` 显式提示用户安装其中之一

#### Windows

- 使用 `python-vlc` 作为 Python 侧播放依赖
- 显式要求用户安装 VLC
- 通过配置指定 VLC 的路径，至少需要 `vlc_path`
- 预留 `vlc_lib_path`，用于后续处理 `libvlc` 动态库定位问题
- 如果 `python-vlc`、VLC 或其配置路径不可用，则由 `server` 返回结构化错误，由 `client` 显式提示用户安装或修正配置

第一版固定采用以下后端组合：

- macOS: `afplay`
- Linux: `mpv` / `ffplay` / `paplay`
- Windows: `python-vlc` + VLC

### 播放实现建议

建议对外统一接口：

- `play_audio(path: str) -> PlaybackResult`
- `detect_audio_backend() -> AudioBackendResult`

实现策略：

- 默认异步播放，不阻塞 server 主循环
- 使用 `subprocess.Popen(...)`
- `stdin/stdout/stderr` 重定向到 `DEVNULL`

但要注意：

- 若 server 单线程执行播放命令且命令本身阻塞，会影响后续查询
- 因此播放必须放到独立线程或直接使用非阻塞子进程

第一版建议：

- `server` 在收到播放请求后仅启动一个非阻塞播放器进程，然后立即返回

### 风险与注意点

- Windows 的音频后端兼容性仍然是最复杂的一段，因此第一版直接依赖 `python-vlc` + VLC
- 如果播放器不可用，server 不应报致命错误，而应返回明确错误码交给 client 展示
- 对同一单词连续播放时，需要避免重复并发启动过多播放器进程
- Linux 的“固定后端”逻辑必须带失效恢复，否则一旦配置指向无效命令会长期不可播放
- Windows 的 VLC 路径校验不能只检查 `vlc.exe`，还应预留 `libvlc` 相关定位能力

## Part 4: 配置项设计

### 需要改动的部分

- `wudao_dict/core/config.py`
- `wudao_dict/cli.py`

### 建议新增配置项

- `pronounce`: 是否启用发音功能
- `pronounce_auto_play`: 查询后是否自动播放
- `pronounce_accent`: `uk` / `usa`
- `audio_cache_max_mb`: 音频缓存容量上限
- `audio_player_backend`: 当前固定的播放后端
- `vlc_path`: Windows 下 VLC 可执行文件路径
- `vlc_lib_path`: Windows 下 `libvlc` 路径，可选

建议默认值：

```json
{
  "pronounce": false,
  "pronounce_auto_play": false,
  "pronounce_accent": "usa",
  "audio_cache_max_mb": 256,
  "audio_player_backend": "",
  "vlc_path": "",
  "vlc_lib_path": ""
}
```

### CLI 参数建议

可考虑新增：

- `--pronounce {yes,no}`
- `--accent {uk,usa}`
- `--play`
- `--vlc-path`

其中：

- `--pronounce` 控制全局功能启用
- `--accent` 设置全局口音偏好
- `--play` 可用于“仅播放，不查词”或“本次查询完成后强制播放”
- `--vlc-path` 用于 Windows 下写入 VLC 路径配置

第一版不必一次把所有参数都加齐；优先全局配置即可。

## Part 5: 消息协议与调度

### 需要改动的部分

- `wudao_dict/core/interface.py`
- `wudao_dict/client.py`
- `wudao_dict/server.py`

### 推荐新增命令

- `play_pronunciation`

### 推荐新增响应结果

建议为播放请求增加结构化结果，而不是只返回空字符串。至少区分：

- `ok`
- `backend_not_found`
- `backend_broken`
- `afplay_not_found`
- `linux_backend_not_found`
- `vlc_not_installed`
- `vlc_path_invalid`
- `play_failed`

Client 侧建议新增：

- `play_pronunciation(word: str) -> None`

Server 侧建议新增：

- `_handle_play_pronunciation(...)`

### 时序建议

英文查词时：

1. client 发送 `query`
2. server 返回词义
3. cli 输出词义
4. client 发送 `play_pronunciation`
5. server 读取配置、检测或恢复播放后端并播放音频
6. client 在必要时展示明确的依赖安装或配置提示

这样分层最清晰，也不会把“查询结果返回”与“播放器时长”耦合到同一个请求里。

## Part 6: 分阶段实现建议

### Stage 1: 最小可用版本

- 只支持英文单词
- 只支持 youdao provider
- 只支持 `uk` / `usa`
- 只做本地长期缓存，不做远端更新检查
- 自动播放通过第二条 socket 命令触发
- macOS 使用 `afplay`
- Linux 使用 `mpv` / `ffplay` / `paplay` 探测并固定
- Windows 使用 `python-vlc` + VLC 路径配置

交付结果：

- 能下载音频
- 能本地缓存
- 能在查询后播放

### Stage 2: 稳定化

- 加容量清理
- 加损坏文件检测
- 完善 Linux 固定后端失效恢复
- 完善 Windows `libvlc` 路径定位
- 补充 client 侧依赖提示文案

### Stage 3: 增强

- 支持手动播放某个单词
- 支持仅下载不播放
- 支持预热高频词发音
- 支持 provider fallback

## Part 7: 建议优先级

建议按以下顺序实施：

1. 定义配置项和消息协议
2. 完成 provider 音频 URL 获取
3. 完成缓存目录和文件下载
4. 在 server 中接入“确保缓存存在”
5. 在 client/cli 中加入“绘制后触发播放”
6. 实现 macOS/Linux/Windows 的分平台播放后端
7. 最后补容量控制和错误收敛

## Part 8: 当前方案中的关键决策

为避免后续返工，建议先固定以下决策：

1. 第一版只支持英文单词发音 (已确定)
2. Windows 强制依赖 `python-vlc` + VLC (已确定)
3. Linux 第一次探测成功后固定后端，失效时重新探测 (已确定)
4. 自动播放默认关闭 (已确定)

当前已确定的默认方向：

- 只支持英文
- 自动播放默认关闭
- 发音缓存长期有效
- macOS 使用 `afplay`
- Linux 使用 `mpv` / `ffplay` / `paplay`
- Windows 使用 `python-vlc` + VLC

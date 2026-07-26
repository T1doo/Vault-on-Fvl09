# Claude Code 安装配置实时日志

> 本文档记录 Claude Code 在当前服务器上的个人用户级安装与配置过程。按时间顺序追加事实；失败、取消和后续更正均保留。

## 2026-07-25

### 安装前确认

- 工作区：`/bigbig_nfs_share/lijunhui`
- 用户主目录：`/home/lijunhui`
- 执行用户：`lijunhui`（UID 10202，GID 10202）
- 平台：Linux x86_64
- `/home/lijunhui` 所在文件系统：
  - 总容量：879 GB
  - 已使用：540 GB
  - 可用：294 GB
  - 使用率：65%
  - inode 使用率：7%
- `/home/lijunhui` 所有者和权限：`lijunhui:lijunhui`，模式 `750`
- 决策：Claude Code 本体、版本、个人配置和认证状态使用官方默认的用户主目录路径；项目和研究资料继续存放在 `/bigbig_nfs_share/lijunhui`。
- 安全边界：不使用 `sudo`，不使用系统包管理器，不写入 `/usr`、`/usr/local`、`/etc` 或其他用户目录。

### 官方资料复核

- 官方安装文档：<https://code.claude.com/docs/en/installation>
- 官方配置文档：<https://code.claude.com/docs/en/settings>
- 选择官方推荐的 Native Install。
- 选择 `stable` 发布渠道。该渠道通常比 latest 略晚，并避开已知重大回归。
- 官方 Linux 用户级路径：
  - 启动器：`~/.local/bin/claude`
  - 版本文件：`~/.local/share/claude/versions/`
  - 用户配置与状态：`~/.claude/`
  - 其他用户状态：`~/.claude.json`

### 16:07 左右——下载安装脚本并审计

- 下载地址：`https://claude.ai/install.sh`
- 审计副本：
  `/bigbig_nfs_share/lijunhui/tmp/claude-code-install-review/install.sh`
- 脚本长度：217 行。
- 审计结论：
  - 明确拒绝普通用户通过 `sudo` 运行。
  - 以 `$HOME` 为安装根目录。
  - 临时下载目录为 `~/.claude/downloads`。
  - 从 `https://downloads.claude.ai/claude-code-releases` 获取版本、manifest 和平台二进制。
  - 下载后核对 manifest 中的 SHA-256。
  - 未发现系统包管理器调用。
  - 未发现向 `/usr`、`/usr/local` 或 `/etc` 写入。
  - 下载完成后调用已校验二进制的 `install` 子命令建立用户级启动器。

### 16:08 左右——执行安装

执行的核心命令：

```sh
bash /bigbig_nfs_share/lijunhui/tmp/claude-code-install-review/install.sh stable
```

安装结果：

- 状态：成功
- 版本：`2.1.212`
- 启动器：`/home/lijunhui/.local/bin/claude`
- 实际二进制：
  `/home/lijunhui/.local/share/claude/versions/2.1.212`
- 启动器是指向上述版本文件的符号链接。
- 安装器提示 `~/.local/bin` 当时不在 `PATH` 中，未报告系统级写入。

验证命令和结果：

```text
/home/lijunhui/.local/bin/claude --version
2.1.212 (Claude Code)
```

### PATH 配置

修改文件：

`/bigbig_nfs_share/lijunhui/activate.sh`

新增逻辑：将 `$HOME/.local/bin` 幂等地加入 `PATH`。该文件已由用户 shell profile 加载，因此新终端中可以直接运行 `claude`。

验证结果：

```text
command -v claude
/home/lijunhui/.local/bin/claude

claude --version
2.1.212 (Claude Code)
```

### 权限收紧

- 将 `/home/lijunhui/.claude` 权限设置为 `700`。
- 验证结果：`700 lijunhui:lijunhui /home/lijunhui/.claude`
- 目的：Claude Code 的个人配置、会话和认证相关数据仅允许当前用户访问。

### 16:09 左右——健康检查未完成

- 已尝试运行官方建议的 `claude doctor`。
- 该操作的授权/执行被用户取消，因此没有获得健康检查结果。
- 未将健康检查标记为成功。
- 进程复查时未发现遗留的 `claude doctor` 进程。
- 下一步：用户方便时重新运行 `claude doctor`，然后首次启动 `claude` 完成登录。

## 当前状态

- [x] 官方文档复核
- [x] 官方脚本下载并审计
- [x] Claude Code stable 用户级安装
- [x] 版本命令验证
- [x] PATH 配置
- [x] 配置目录权限收紧
- [ ] `claude doctor` 健康检查
- [ ] 首次登录
- [ ] 实际交互测试

### 16:10 以后——首次启动网络故障

用户在执行 `cwork`、`claude` 后看到：

```text
Unable to connect to Anthropic services
Failed to connect to api.anthropic.com: ERR_BAD_REQUEST
```

只读诊断结果：

- Clash HTTP/Mixed 端口 `127.0.0.1:10425` 正在监听。
- 当前代理环境同时包含：
  - `HTTP_PROXY=http://127.0.0.1:10425`
  - `HTTPS_PROXY=http://127.0.0.1:10425`
  - `ALL_PROXY=socks5h://127.0.0.1:10425`
- 通过 HTTP 代理访问 `https://api.anthropic.com/`：
  - curl 退出码：0
  - HTTP 状态：404
- 404 是访问 API 根路径的应用层响应，说明 DNS、代理连接和 TLS 通道已经建立；不是 Clash 端口未启动。
- 官方网络文档明确说明 Claude Code 不支持 SOCKS 代理，因此同时存在的 `ALL_PROXY=socks5h://...` 是首要冲突项。
- 下一步：在不修改全局代理函数的情况下，用仅保留 HTTP/HTTPS 代理的一次性环境重试 Claude Code。

建议命令：

```sh
env -u ALL_PROXY -u all_proxy \
  HTTP_PROXY=http://127.0.0.1:10425 \
  HTTPS_PROXY=http://127.0.0.1:10425 \
  http_proxy=http://127.0.0.1:10425 \
  https_proxy=http://127.0.0.1:10425 \
  claude
```

截至本次记录，尚未取得上述重试结果，不能标记首次登录成功。

### 16:15 左右——用户终端确认 HTTP 代理连通

用户从 Windows PowerShell SSH 登录 `fvl09` 后依次执行：

```sh
cwork
personal_proxy_on
unset ALL_PROXY all_proxy
env | grep -i proxy
curl -I --max-time 15 https://api.anthropic.com
```

环境确认：

- `HTTP_PROXY` 和 `HTTPS_PROXY` 均指向 `http://127.0.0.1:10425`
- `ALL_PROXY` 已从当前终端移除

curl 实际结果：

```text
HTTP/1.1 200 Connection established
HTTP/2 404
server: cloudflare
cf-ray: ...-LAX
```

结论：

- `200 Connection established` 表示 Clash HTTP 代理成功建立 HTTPS 隧道。
- 后续 `HTTP/2 404` 是 Anthropic API 根路径返回的应用层响应。
- 当前终端经 Clash 到 `api.anthropic.com` 的代理、TLS 和网络通道已验证成功。
- 下一步是在同一终端直接运行 `claude`，观察是否进入登录流程。

### 后续确认——Claude Code 启动成功

- 用户确认：在上述同一 SSH 终端移除 `ALL_PROXY`、保留 HTTP/HTTPS Clash 代理后，`claude` 成功启动。
- 结论：Claude Code 可以通过本机 Clash 的 HTTP 代理入口正常使用。
- 本次 `personal_proxy_on` 和 `unset ALL_PROXY all_proxy` 都只改变当前 SSH shell 的环境变量；关闭该终端后不会继续存在，也不会影响其他用户或其他已打开终端。
- 登录状态由 Claude Code 保存在当前用户的个人配置目录中，下一次通常不需要重新登录；但新 SSH 终端仍需重新准备代理环境。

### 自动代理入口配置

用户希望新 SSH 终端中直接运行 `claude`，不再手工设置代理。

修改文件：

`/bigbig_nfs_share/lijunhui/activate.sh`

新增个人 shell 函数 `claude()`：

- 自动将 Claude Code 子进程的 HTTP/HTTPS 代理指向 `http://127.0.0.1:10425`
- 仅为 Claude Code 子进程移除 `ALL_PROXY` 和 `all_proxy`
- 调用官方安装路径 `/home/lijunhui/.local/bin/claude`
- 原样转发全部命令行参数
- 不改变调用它的 shell 环境
- 不修改官方启动器符号链接，因此不干扰 Native Install 自动更新
- 该 `activate.sh` 仅由用户个人 shell 加载，不影响其他用户

预期日常操作：

```sh
cwork
claude
```

### 工作区长期规则同步

更新 `/bigbig_nfs_share/lijunhui/AGENTS.md`，新增：

- Claude Code 的个人安装位置、配置位置和 stable 渠道约定。
- 用户对 `/home/lijunhui` 的窄范围授权：仅限 Claude Code 的安装、配置、验证、更新和故障排查，不扩展到其他工作。
- `activate.sh` 中 Claude 自动 HTTP 代理入口的行为约定。
- 保留官方 native launcher、不以自定义 wrapper 替换的更新兼容要求。
- Claude Code 日志和使用说明的规范路径。
- 禁止在日志中记录凭据、授权码、API Key 或 Token。
- 每次任务结束前主动复查是否有稳定、跨任务的信息应沉淀到 `AGENTS.md`；只记录长期规则，不记录临时输出、推测或秘密。

本次仅编辑文件，未执行 Git commit 或 push。

## 第三方模型/提供商配置研究

### 背景

- 用户当前没有 Claude 官方会员订阅，希望评估 Claude Code 接入第三方模型或第三方计费渠道的可行性。
- 当前阶段仅研究，未写入第三方地址、模型名或凭据，未改变现有 Claude Code 配置。

### 官方支持边界

- Claude Code 不强制要求 Claude Pro/Max 会员，但必须有一种可用的模型认证和计费来源。
- 官方支持的主要替代来源：
  - Anthropic Console API 按量计费
  - Amazon Bedrock 上的 Claude
  - Google Vertex AI 上的 Claude
  - Microsoft Foundry 上的 Claude
  - 符合要求的 LLM Gateway
- Gateway 至少需要暴露 Claude Code 支持的 API 格式之一。最常见的是 Anthropic Messages：
  - `/v1/messages`
  - `/v1/messages/count_tokens`
  - 正确转发 `anthropic-beta` 和 `anthropic-version` 请求头
- 只有 OpenAI `/v1/chat/completions` 接口的第三方服务不能被 Claude Code 直接使用；需要可靠的 Anthropic Messages 协议转换层。
- `ANTHROPIC_BASE_URL` 只改变请求目的地，本身不会自动把 API 协议或模型转换成 Claude Code 可用格式。
- 非 Claude 模型通过兼容网关运行属于兼容性方案。工具调用、流式响应、扩展思考、上下文长度、提示缓存、token 计数和子代理等功能可能不完整。
- 官方文档提到 LiteLLM 作为第三方网关示例，但 Anthropic 不维护或审计它；官方还警告 LiteLLM PyPI `1.82.7` 和 `1.82.8` 曾遭供应链攻击，不能安装这些版本。

### 配置前必须确认

- 第三方服务名称和官方文档地址
- API 基础地址
- 它提供 Anthropic Messages 兼容接口，还是仅提供 OpenAI 兼容接口
- 目标模型的准确 ID
- 鉴权要求使用 `Authorization: Bearer` 还是 `x-api-key`
- 是否支持流式输出、工具调用和 token 计数
- 计费方式、余额和数据处理政策

### 凭据安全约定

- 不在聊天、实时日志、Git 仓库、`AGENTS.md` 或项目 `CLAUDE.md` 中记录真实 API Key。
- 后续如需配置凭据，应写入当前用户的私有配置或权限为 `600` 的独立凭据文件，并避免命令输出泄露。
- 在明确第三方提供商之前，不实施配置。

### 官方参考

- Authentication: <https://code.claude.com/docs/en/authentication>
- LLM Gateway: <https://code.claude.com/docs/en/llm-gateway>
- Model configuration: <https://code.claude.com/docs/en/model-config>
- Third-party integrations: <https://code.claude.com/docs/en/third-party-integrations>

### CC Switch 项目适配性研究

用户提出研究 GitHub 上的 CC Switch 是否有适合当前服务器的版本。

#### 原版桌面项目

- 唯一官方仓库：`farion1231/cc-switch`
- 仓库：<https://github.com/farion1231/cc-switch>
- 定位：基于 Tauri 的跨平台桌面应用。
- 官方 Release 提供 Linux x86_64 的 AppImage、deb 和 rpm。
- 当前服务器是 Ubuntu 22.04 x86_64，因此 CPU 架构与 Linux release 匹配。
- 但当前使用方式以 Windows SSH 登录服务器为主，未确认存在桌面会话、X11 转发或远程桌面。
- deb 安装文档要求 `sudo`/系统包管理器，与当前个人用户级安装边界不符。
- AppImage 理论上可以用户级运行，但仍需要图形显示环境，并可能依赖 FUSE；因此原版 GUI 不适合作为当前服务器的首选方案。

#### CLI 分支

- 仓库：`SaladDay/cc-switch-cli`
- 地址：<https://github.com/SaladDay/cc-switch-cli>
- 关系：原版 CC Switch 的独立 CLI 分支，不是 `farion1231/cc-switch` 原仓库本身。
- 定位：为服务器/终端工作流提供 TUI 和 CLI。
- 最新检索到的 release：v5.7.0。
- 提供：
  - Linux x64 musl 静态构建
  - Linux x64 glibc 构建
  - SHA-256 release 校验值
- 默认安装目标为 `~/.local/bin`，可用 `CC_SWITCH_INSTALL_DIR` 自定义，因此可以在不使用 `sudo` 的情况下进行个人安装。
- 配置目录默认是 `~/.cc-switch/`，也可通过 `CC_SWITCH_CONFIG_DIR` 定向。
- 支持供应商切换、Claude Code 配置同步、OpenAI/Responses 到 Anthropic 的本地协议路由、模型映射和健康检查。
- Linux/macOS 支持 daemon 管理的本地代理；Windows 端限制与本服务器无关。

#### 风险和限制

- CLI 分支会读取和修改 Claude Code live 配置，启用路由时会把 `ANTHROPIC_BASE_URL` 指向本地服务；实施前必须备份现有 `~/.claude` 配置。
- 它会在 SQLite 数据库中保存供应商配置，可能包含 API 凭据。
- 项目当前存在关于数据库文件权限应进一步收紧的开放 issue（#218），因此不能依赖默认权限；若安装，应显式使用私有配置目录并验证/收紧为目录 `700`、敏感文件 `600`。
- 项目也存在非 Claude 模型工具参数兼容问题的开放 issue，例如通过 Claude Code 配置 GPT 时 Read 工具参数异常（#208）。
- 这是社区项目，不是 Anthropic 官方组件；其协议转换和第三方模型兼容性不能等同于官方支持。
- 不应执行 `curl | bash`。若决定安装，应先下载并审计 installer、固定 release、核对 SHA-256，再安装到个人目录。

#### 当前建议

- 不在当前 SSH 服务器安装原版 GUI。
- 若用户确认需要 CC Switch，优先进一步审计 `SaladDay/cc-switch-cli` 的固定版本 Linux x64 musl release。
- 建议程序和配置均使用明确的个人隔离目录，避免覆盖现有 Claude Code 配置；先以 `--dry-run`/临时启动方式测试，再决定是否启用全局 provider switch 或 daemon routing。
- 当前仅完成研究，未下载、安装或写入任何第三方凭据。

### 2026-07-25 16:20–16:26——CC-Switch CLI 审计与个人安装

#### 固定源码审计

- 仓库：`https://github.com/SaladDay/cc-switch-cli.git`
- 固定 tag：`v5.7.0`
- 检出 commit：`8c29cfe68c6373945307e9902a60c38edbe8146d`
- 审计目录：
  `/bigbig_nfs_share/lijunhui/tmp/cc-switch-cli-review/source-v5.7.0`
- 完整阅读该 tag 的 `install.sh`（372 行）和仓库 `CLAUDE.md`。
- 该 tag 不包含 `AGENTS.md`；`CLAUDE.md` 明确要求测试或审计时隔离 `CC_SWITCH_CONFIG_DIR`、`CLAUDE_CONFIG_DIR` 和 `CODEX_HOME`。

安装器审计结果：

- 支持通过 `CC_SWITCH_INSTALL_DIR` 自定义安装位置。
- 使用 `mktemp` 下载并解压一个平台二进制。
- 仅复制到目标目录，不调用 `sudo` 或系统包管理器。
- 不自动编辑 shell profile，只打印 PATH 建议。
- 安装器会清理自己的临时目录。
- 重要缺陷：安装器本身不校验 Release SHA-256。因此没有运行安装器，而是采用固定产物手工校验安装。

源码安全边界确认：

- `CC_SWITCH_CONFIG_DIR` 可以定向 SQLite、settings、backups 和 skills 状态目录。
- Claude live 配置默认是 `~/.claude/settings.json`。
- provider switch 或 proxy takeover 会修改 live 配置。
- daemon/worker 只在相关命令显式启用时运行。
- daemon runtime 目录和 socket 的源码目标权限分别为 `700` 和 `600`。
- 供应商配置可能包含 API Key 并进入 SQLite，因此必须额外使用私有 umask 和文件权限。

#### Release 下载与校验

- GitHub Release API 元数据：
  `/bigbig_nfs_share/lijunhui/tmp/cc-switch-cli-review/release-v5.7.0.json`
- 固定产物：
  `cc-switch-cli-v5.7.0-linux-x64-musl.tar.gz`
- 大小：6,445,091 bytes
- GitHub Release 声明 SHA-256：
  `2131c2e49896f97872bbada056f9546d291a6a3c57733689ee40e5738d2df413`
- 本地计算 SHA-256：
  `2131c2e49896f97872bbada056f9546d291a6a3c57733689ee40e5738d2df413`
- 结果：完全一致。
- 归档内容检查：仅包含一个名为 `cc-switch` 的文件，无路径穿越条目。

#### 安装布局

```text
/bigbig_nfs_share/lijunhui/.tools/cc-switch-cli/bin/cc-switch
/bigbig_nfs_share/lijunhui/.tools/cc-switch-cli/bin/cc-switch-real
/bigbig_nfs_share/lijunhui/.config/cc-switch-cli/
```

- `cc-switch-real`：固定 v5.7.0 Linux x64 musl 静态 PIE 二进制。
- `cc-switch`：个人启动脚本，设置 `umask 077` 和私有 `CC_SWITCH_CONFIG_DIR` 后调用 `cc-switch-real`。
- `activate.sh` 将 CC-Switch bin 目录加入 PATH。
- 没有使用 `sudo`，没有写入 `/usr`、`/usr/local` 或 `/etc`。

安装过程中首次尝试使用名为 `cc-switch()` 的 shell 函数，但 `/bin/sh`（dash）不允许带连字符的函数名，验证时报 `Syntax error: Bad function name`。该方案立即撤销，改为独立 POSIX `sh` 启动脚本；随后 `sh -n activate.sh` 和实际加载均通过。保留此失败记录，不将其表述为成功。

#### 验证

```text
command -v cc-switch
/bigbig_nfs_share/lijunhui/.tools/cc-switch-cli/bin/cc-switch

cc-switch --version
cc-switch 5.7.0
```

配置初始化：

```text
DB file: /bigbig_nfs_share/lijunhui/.config/cc-switch-cli/cc-switch.db
Database exists
Database validation passed
```

权限：

```text
755 .../.tools/cc-switch-cli/bin/cc-switch
755 .../.tools/cc-switch-cli/bin/cc-switch-real
700 .../.config/cc-switch-cli
600 .../.config/cc-switch-cli/cc-switch.db
```

工具检测：

- Claude：`ok (2.1.212)`
- Codex：`ok (0.145.0)`
- Gemini/OpenCode/Hermes/OpenClaw：未安装

现有 Claude 配置保护：

- 安装前 `/home/lijunhui/.claude/settings.json` SHA-256：
  `a13ae344e442549caad7572a2b4bcb6cd4ceab8a3628c631a21cb550436838f5`
- 安装及配置初始化后 SHA-256：相同
- 结论：现有 Claude settings 未被修改。

后台状态：

- 未发现 CC-Switch daemon 或 proxy 进程。
- 未添加第三方供应商。
- 未写入 API Key。
- 未切换当前 provider。
- 未启用 proxy takeover。

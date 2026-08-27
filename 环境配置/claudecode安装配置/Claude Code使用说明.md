# Claude Code 使用说明

## 当前安装

- 版本：Claude Code `2.1.212`
- 渠道：`stable`
- 命令：`/home/lijunhui/.local/bin/claude`
- 版本目录：`/home/lijunhui/.local/share/claude/versions/`
- 个人配置：`/home/lijunhui/.claude/`
- 项目目录建议：`/bigbig_nfs_share/lijunhui` 下的具体项目

这是 `lijunhui` 用户的个人安装，不需要 `sudo`，不会安装到系统目录。

## 第一次使用

打开一个新终端，先确认命令：

```sh
command -v claude
claude --version
```

预期输出路径为：

```text
/home/lijunhui/.local/bin/claude
```

个人 shell 已配置同名 `claude` 函数。直接运行 `claude` 时，会自动让该进程通过 `127.0.0.1:10425` 的 Clash HTTP 代理，并为该进程移除不兼容的 SOCKS 变量。无需再手动运行 `personal_proxy_on` 或 `unset ALL_PROXY`。

建议先执行健康检查：

```sh
claude doctor
```

然后进入需要工作的项目，而不是直接在整个个人目录根部启动：

```sh
cd /bigbig_nfs_share/lijunhui/你的项目目录
claude
```

首次启动会引导登录。需要 Claude Pro、Max、Team、Enterprise 或 Anthropic Console 等受支持的账户/API 方式；免费 Claude.ai 账户通常不包含 Claude Code。

## 网络或代理

Claude Code 登录和模型调用需要联网。个人 `activate.sh` 已为 `claude` 命令配置自动代理，因此日常使用直接运行：

```sh
claude
```

查看代理状态：

```sh
personal_proxy_status
```

关闭代理：

```sh
personal_proxy_off
```

这些函数来自：

`/bigbig_nfs_share/lijunhui/activate.sh`

自动入口只为 Claude Code 子进程设置 HTTP/HTTPS 代理并移除 SOCKS 变量，不会关闭 Clash，不会永久改变当前终端，也不会改变其他程序的代理环境。

## 常用命令

启动交互会话：

```sh
claude
```

带初始问题启动：

```sh
claude "先阅读这个项目，概括目录结构和主要入口，不要修改文件"
```

单次询问并退出：

```sh
claude -p "解释这个项目的测试命令"
```

继续当前目录最近一次会话：

```sh
claude --continue
```

选择历史会话：

```sh
claude --resume
```

查看版本：

```sh
claude --version
```

检查安装：

```sh
claude doctor
```

查看完整帮助：

```sh
claude --help
```

## CC-Switch CLI

已安装个人工作区版本：

```text
版本：5.7.0
命令：/bigbig_nfs_share/lijunhui/.tools/cc-switch-cli/bin/cc-switch
配置：/bigbig_nfs_share/lijunhui/.config/cc-switch-cli
```

打开新终端后检查：

```sh
cc-switch --version
cc-switch config path
cc-switch config validate
cc-switch env tools
```

进入交互式 TUI：

```sh
cc-switch
```

只查看供应商，不切换：

```sh
cc-switch provider list
cc-switch provider current
```

在正式配置第三方供应商前，不要执行以下操作：

- 不要启用 `proxy enable`
- 不要启动 `daemon`
- 不要切换 provider
- 不要把 API Key 粘贴进聊天、Markdown、Git 仓库或 shell history

CC-Switch 的个人启动脚本会自动设置私有配置目录并以 `umask 077` 运行。不要绕过启动脚本直接调用 `cc-switch-real`。

本安装使用经过 SHA-256 核对的固定版本。不要使用 CC-Switch 内置更新或网络上的 `curl | bash` 一键安装；升级应重新审计固定 Release。

## 推荐使用习惯

1. 先 `cd` 到明确的项目目录，再运行 `claude`。
2. 第一次接触项目时，先要求它只读分析，不要立即修改文件。
3. 修改前检查 Claude Code 展示的权限请求和命令目标。
4. 修改后查看 `git diff` 并运行相关测试。
5. 不使用 `--dangerously-skip-permissions`，尤其不要在个人目录根部或共享目录运行该选项。
6. 不把 API Key、Token、密码直接写进项目的 `CLAUDE.md`、Git 仓库或对话提示。
7. 对共享仓库，个人设置优先写入 `.claude/settings.local.json`，不要未经确认提交团队共享的 `.claude/settings.json`。

## CLAUDE.md 的用途

Claude Code 会读取项目内的 `CLAUDE.md` 作为长期项目说明。适合记录：

- 项目结构和关键入口
- 安装、测试、格式化命令
- 代码风格
- 禁止修改的目录
- 数据集和模型路径约定

不要在其中记录密码、私钥或访问令牌。

一个简短示例：

```md
# Project instructions

- Run tests with `pytest tests/`.
- Do not modify generated files under `build/`.
- Keep datasets outside the Git repository.
- Ask before changing dependency versions.
```

## 更新

Native Install 会在当前用户范围内检查并安装更新。当前选择的是 `stable` 渠道。

手动检查或更新：

```sh
claude update
```

更新只应写入：

```text
/home/lijunhui/.local/share/claude/versions/
```

更新后验证：

```sh
claude --version
claude doctor
```

## 退出与登出

交互界面中可按界面提示退出，通常也可以使用 `Ctrl-D`。

若需要退出账户，在 Claude Code 交互界面使用：

```text
/logout
```

## 故障排查

如果提示 `claude: command not found`：

```sh
. /bigbig_nfs_share/lijunhui/activate.sh
command -v claude
```

也可以直接运行：

```sh
/home/lijunhui/.local/bin/claude --version
```

如果登录或请求失败：

1. 运行 `personal_proxy_status` 检查代理。
2. 视网络环境运行 `personal_proxy_on`。
3. 运行 `claude doctor`。
4. 不要反复重新安装；先保存完整错误信息。

如果版本链接异常：

```sh
ls -l /home/lijunhui/.local/bin/claude
ls -l /home/lijunhui/.local/share/claude/versions/
```

## 卸载位置说明

当前安装相关的主要路径是：

```text
/home/lijunhui/.local/bin/claude
/home/lijunhui/.local/share/claude/
/home/lijunhui/.claude/
/home/lijunhui/.claude.json
```

配置目录可能包含登录状态、设置和会话历史。除非明确决定彻底卸载并清除数据，否则不要删除。卸载或删除前应先检查路径和备份需求。

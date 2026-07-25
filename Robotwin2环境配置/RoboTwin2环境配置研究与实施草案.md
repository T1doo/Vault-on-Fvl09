# RoboTwin 2.0 环境配置研究与实施草案

> 状态：仅研究与规划，尚未开始配置  
> 记录日期：2026-07-25  
> 工作区边界：所有代码、环境、缓存、模型、数据及配置必须位于 `/bigbig_nfs_share/lijunhui/`

## 1. 目标与本轮结论

本轮只做官方资料研究、工作区内的只读盘点和实施方案设计，不克隆仓库、不创建 Python 环境、不下载资产、不安装依赖。

建议先完成一个“最小可运行的 RoboTwin 2.0 仿真环境”，验证官方示例任务能够渲染和运行；策略训练环境（ACT、DP、DP3、RDT、Pi0 等）随后按研究目标单独创建，避免把互相冲突的 PyTorch、CUDA 和 Python 依赖塞进同一个环境。

官方目前给出的核心要求如下：

- 最佳支持平台是 Linux + NVIDIA GPU。
- Python 固定使用 3.10。
- CUDA 推荐 12.1。
- 渲染需要 Vulkan；GPU 仿真需要 NVIDIA GPU。
- 光线追踪要求 NVIDIA 驱动至少 470；OIDN 降噪要求至少 520。
- 官方基本流程是创建 Conda 环境、克隆仓库、运行 `script/_install.sh`，再运行 `script/_download_assets.sh`。
- 如果不使用 3D 数据，PyTorch3D 安装失败不会阻塞基本功能。
- 官方提醒 A/H 系列 GPU 的数据采集偶尔可能卡住，需要留意 RoboTwin issue #83 与 SAPIEN issue #219。

## 2. 官方资料与可信来源

优先依据以下一手资料：

1. [RoboTwin 2.0 官方安装文档](https://robotwin-platform.github.io/doc/usage/robotwin-install.html)
2. [RoboTwin-Platform/RoboTwin 官方 GitHub 仓库](https://github.com/RoboTwin-Platform/RoboTwin)
3. [RoboTwin 2.0 官方使用文档入口](https://robotwin-platform.github.io/doc/usage/)
4. [官方任务列表](https://robotwin-platform.github.io/doc/tasks/)
5. [官方 Common Issue](https://robotwin-platform.github.io/doc/common_issue/)

官方仓库主页将安装说明指向官方文档。官方安装页最后标注的更新时间为 2025-08-05；实际执行前仍应再次核对仓库当前的 `script/_install.sh`、requirements 文件和最新 issues，不能只照搬旧教程。

## 3. 本机/工作区当前已确认的信息

在不越过 `/bigbig_nfs_share/lijunhui/` 读取边界的前提下，本轮确认：

- 当前工作目录：`/bigbig_nfs_share/lijunhui`
- 研究笔记目录：`/bigbig_nfs_share/lijunhui/Vault-on-Fvl09/Robotwin2环境配置`
- 该目录在本文件创建前为空。
- 工作区位于 NFS 文件系统。
- 文件系统容量约 87 TB，已使用约 58 TB，可用约 30 TB。
- 工作区顶层暂未发现名称含 `robotwin`、`conda`、`miniforge` 或 `mamba` 的现有目录。
- 工作区已有 `activate.sh`，用于配置工作区内的 Git/GitHub CLI 与代理辅助函数；它不是 RoboTwin 的环境激活脚本。

尚未核验的信息：

- Linux 发行版、内核和 glibc 版本
- GPU 型号、数量、显存
- NVIDIA 驱动版本及其支持的最高 CUDA 版本
- Vulkan ICD、`vulkaninfo` 和图形能力
- 现有 Conda/Mamba、Python、编译器、CMake、Ninja、ffmpeg
- 服务器是否为容器/无显示节点，以及 EGL/headless 渲染能力

原因：用户给出的 `AGENTS.md` 禁止读取工作区外文件；这些检查通常会读取 `/proc`、`/etc`、`/usr` 或驱动相关系统路径。正式配置前需要用户明确许可进行这些只读系统检查，或者由用户提供相应命令输出。

## 4. 建议的目录布局

所有可控内容均放在个人工作区中：

```text
/bigbig_nfs_share/lijunhui/
├── projects/
│   └── RoboTwin/                 # 官方代码仓库
├── envs/
│   └── robotwin2/                # Python/Conda 环境
├── caches/
│   ├── pip/
│   ├── conda/
│   ├── torch/
│   └── huggingface/
├── datasets/
│   └── RoboTwin2/                # 大规模采集数据（如需要）
├── models/
│   └── RoboTwin2/                # 策略权重（如需要）
└── tmp/
    └── robotwin2/                # 编译临时文件
```

官方资产默认下载到仓库的 `assets/`，建议第一阶段遵循默认结构，减少路径补丁。若资产体积或共享需求要求外置，再使用工作区内的符号链接或配置项；实施前先确认官方脚本是否会安全处理符号链接。

建议显式设置以下变量，防止缓存落入系统 Home 或其他目录：

```bash
export ROBOTWIN_ROOT=/bigbig_nfs_share/lijunhui/projects/RoboTwin
export CONDA_PKGS_DIRS=/bigbig_nfs_share/lijunhui/caches/conda/pkgs
export PIP_CACHE_DIR=/bigbig_nfs_share/lijunhui/caches/pip
export TORCH_HOME=/bigbig_nfs_share/lijunhui/caches/torch
export HF_HOME=/bigbig_nfs_share/lijunhui/caches/huggingface
export TMPDIR=/bigbig_nfs_share/lijunhui/tmp/robotwin2
```

注意：环境管理器本身也必须安装或配置到工作区内，不能默认写入工作区外的 `~/.conda`、`~/.cache` 等位置。

## 5. 推荐实施路线

### 阶段 A：配置前只读核验

在获得系统信息只读检查许可后，记录：

1. 操作系统、CPU 架构和 glibc。
2. `nvidia-smi`：GPU、显存、驱动、CUDA compatibility。
3. `vulkaninfo --summary`：Vulkan loader、ICD、物理设备。
4. `conda`/`micromamba`、Python、GCC/G++、CMake、Ninja、ffmpeg 的版本和实际路径。
5. 是否已有可用的 CUDA toolkit；区分“驱动支持的 CUDA 版本”和本地 `nvcc` toolkit 版本。
6. headless 节点能否创建 SAPIEN/Vulkan 渲染上下文。

准入条件建议：

- Linux x86_64；
- NVIDIA 驱动满足官方要求，优先选择能稳定支持 CUDA 12.1 runtime 的版本；
- Vulkan 能识别目标 NVIDIA GPU；
- 工作区内可创建环境、缓存和临时编译目录。

### 阶段 B：审计官方安装脚本

克隆仓库后先不执行脚本，检查：

- 当前 commit SHA、分支和仓库 remote；
- `script/_install.sh` 与 `script/_download_assets.sh`；
- requirements 中 Python、SAPIEN、mplib、PyTorch、CuRobo、PyTorch3D 的版本约束；
- 是否包含 `sudo`、`apt`、写入绝对路径、写入用户 Home、修改已安装包源码、递归删除等行为；
- 资产 URL、预计大小、校验方式和解压目标。

只有脚本确认不会越界写入后，才进入安装。必要时复制/补丁一个“工作区安全版安装脚本”，并保留差异记录。

### 阶段 C：创建隔离的基础环境

建议：

- 环境位置：`/bigbig_nfs_share/lijunhui/envs/robotwin2`
- Python：3.10
- 不修改系统 Python，不使用系统级 `sudo pip`
- 先安装基础环境，再按官方顺序安装 CuRobo
- PyTorch/CUDA wheel 的选择以阶段 A 的驱动核验结果为准，不能仅根据 `nvidia-smi` 显示的 CUDA compatibility 数字盲选

官方快速安装的逻辑是：

```bash
conda create -n RoboTwin python=3.10 -y
conda activate RoboTwin
git clone https://github.com/RoboTwin-Platform/RoboTwin.git
cd RoboTwin
bash script/_install.sh
```

实际执行时会改成基于绝对路径的工作区环境，并在运行 `_install.sh` 前完成脚本审计。

### 阶段 D：下载资产

官方命令为：

```bash
bash script/_download_assets.sh
```

下载后预期至少包含：

```text
assets/
├── background_texture/
├── embodiments/
└── objects/
```

下载前应确认资产体积、Hugging Face 登录/限流需求和解压后的实际磁盘占用。当前空间充足，但 NFS 上大量小文件与并发读取可能影响仿真和训练性能；如果运行性能异常，应将“元数据/小文件延迟”列入排查，而不能只看总带宽。

### 阶段 E：分层验收

建议按以下顺序验收，每一步记录命令、版本和输出：

1. Python 可以导入 `sapien`、`mplib`、`torch` 和 RoboTwin 依赖。
2. `torch.cuda.is_available()` 为真，并核对实际 GPU。
3. Vulkan 能识别 GPU。
4. 无窗口/headless 最小渲染测试通过。
5. 运行一个官方 clean demo 的单次仿真。
6. 少量轨迹采集成功，检查图像、状态、动作和日志。
7. 再测试 randomized 配置。
8. 只有基础仿真稳定后，才创建具体策略的训练环境。

## 6. 已知风险与处理原则

### 系统 Vulkan 依赖可能是硬阻塞

官方建议用 `apt` 安装 `libvulkan1`、`mesa-vulkan-drivers`、`vulkan-tools`。这会修改系统且超出个人工作区，本方案不会擅自执行。优先检查服务器是否已经安装；若缺失，需要管理员支持，或研究能否在工作区内提供兼容 loader/工具，但不能保证无需系统级驱动/ICD。

### 官方脚本可能写入环境之外

Conda、pip、编译工具和 Hugging Face 默认会使用 Home 下的缓存。正式执行前必须固定缓存、临时目录和环境前缀，并审计安装脚本。

### NFS 对编译与仿真性能的影响

NFS 空间充足，但源码编译、Conda 解包、纹理/mesh 小文件访问可能较慢。可将所有临时文件放到工作区的 `tmp/robotwin2`；如果仍然很慢，再在不突破边界的前提下调整缓存布局。

### mplib 手工修改

官方手动安装说明要求在特定情况下修改 `mplib/planner.py`，删除碰撞判断条件中的 `or collide`。这是侵入式变更，只应作为明确复现相关问题后的 fallback，并记录包版本、文件差异与原因，不应预先无条件修改。

### 策略依赖冲突

RDT、OpenVLA-oft、DexVLA、TinyVLA、DP/DP3 等各有独立的 PyTorch、flash-attn、数据格式和训练依赖。基础 RoboTwin 环境只承担仿真/评测；训练环境按策略拆分。

## 7. 建议我们先达成一致的决策

开始配置前需确认：

1. 第一阶段目标是否定为“跑通基础仿真 + 一个 clean demo + 少量数据采集”，暂不安装策略训练栈。
2. 是否允许只读访问工作区外的系统信息，用于执行 `nvidia-smi`、`vulkaninfo`、系统版本及工具链检查；仍然保证所有修改只发生在 `/bigbig_nfs_share/lijunhui/`。
3. 代码目录是否采用 `/bigbig_nfs_share/lijunhui/projects/RoboTwin`。
4. 环境是否采用前缀路径 `/bigbig_nfs_share/lijunhui/envs/robotwin2`。
5. 是否优先使用已有 Conda/Mamba；如果不存在，再选择工作区内安装 Miniforge/Micromamba。
6. 后续主要目标是哪一种：仿真与数据采集、策略评测，还是某个具体策略训练。该选择会决定额外依赖和模型/数据下载规模。

## 8. 获批后的拟执行清单

- [ ] 获得只读系统检查授权并补全机器信息
- [ ] 再次核对官方文档、仓库最新 commit 和已知 issues
- [ ] 在工作区内克隆官方仓库
- [ ] 审计两个官方脚本并记录风险
- [ ] 创建工作区专用缓存、临时目录和 Python 3.10 环境
- [ ] 安装基础依赖与 CuRobo
- [ ] 下载并检查官方资产
- [ ] 完成导入、CUDA、Vulkan、headless 渲染测试
- [ ] 跑通最小 clean demo 与少量数据采集
- [ ] 将实际版本、命令、问题与解决方案追加到本目录的新日志中
- [ ] 另行讨论并部署目标策略环境

本清单必须在讨论确认后才执行。

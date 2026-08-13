# RoboTwin 2 环境配置实时日志

> 项目根目录：`/bigbig_nfs_share/lijunhui/Robotwin2`  
> 研究笔记目录：`/bigbig_nfs_share/lijunhui/Vault-on-Fvl09/Robotwin2环境配置`  
> 日志原则：按时间追加，真实记录命令、结果、失败、决策和文件变更，不事后美化历史。

## 当前状态

- 阶段：**基础仿真环境 + 渲染 + 数据采集链路已端到端打通（7 卡方案，排除故障 GPU 2）**
- 基础环境：已创建，Python 3.10.20
- 官方代码：已克隆，RoboTwin commit `c3ddfa8b97d5519efa828b075999bd0006778e5e`
- Python/Conda 依赖：官方 requirements 已安装，`pip check` 通过
- 本地 CUDA：12.1.1，位于 `tools/cuda-12.1`，未使用共享 CUDA Toolkit
- CuRobo：v0.7.8 已使用本地 CUDA 编译安装，五个扩展可加载
- PyTorch3D：0.7.8 已使用本地 CUDA 编译安装，`pytorch3d._C` 可加载
- SAPIEN/MPLib：官方兼容补丁已应用并验证
- RoboTwin 资产：三个官方 ZIP 已下载、校验、解压并完成 embodiment 路径生成
- GPU 方案：**物理 GPU 2（UUID `GPU-4329227f-…`）确认故障并永久屏蔽**；激活脚本按 UUID 默认只暴露 7 张健康卡
- CUDA 验证：屏蔽 GPU 2 后 `torch.cuda.is_available()==True`、`device_count()==7`
- 渲染验证：官方 `script/test_render.py` 输出 **Render Well**
- 数据采集验证：`beat_block_hammer` clean demo 冒烟采集 3 episode 成功，HDF5（4 相机 RGB + 关节/末端动作）+ 视频 + 指令产物结构完整
- 策略训练环境：尚未规划到具体策略（下一阶段按策略分别建独立环境）
- 系统侧遗留（不阻塞）：GPU 2 硬件需管理员 reset/冷启动，交接单已备；系统 `vulkaninfo` 因全局枚举仍会失败，但不作为渲染判据

## 目录约定

```text
/bigbig_nfs_share/lijunhui/Robotwin2/
├── project/
│   └── RoboTwin/
├── env/
├── cache/
│   ├── conda/
│   ├── pip/
│   ├── torch/
│   └── huggingface/
├── datasets/
├── models/
├── tmp/
└── tools/
```

这些目录已经创建并投入使用。

## 配置纪律

- 所有可控写入必须位于 `/bigbig_nfs_share/lijunhui/Robotwin2/`。
- 执行任何官方脚本前，先审计其写入位置、系统命令和破坏性操作。
- 不使用 `sudo`、系统包管理器或系统级 `pip`。
- 若必须读取工作区外的 GPU、驱动、Vulkan、操作系统或工具链信息，先获得用户明确许可。
- 每次配置动作都在本日志中记录时间、工作目录、命令、结果、变更和验证情况。
- 研究文档或日志的编辑不自动授权 Git 提交和推送。

## 时间线

### 2026-07-25：用户授权开始配置

- 用户明确回复“全部同意，开始配置”。
- 获得以下授权：
  - 只读检查工作区外的系统、GPU、驱动、Vulkan和工具链信息。
  - 在 `/bigbig_nfs_share/lijunhui/Robotwin2/` 内创建和修改项目目录、隔离环境、缓存、数据与临时文件。
  - 联网克隆官方仓库、下载 Python 依赖和官方资产。
  - 第一阶段目标为基础仿真环境、一个 clean demo 和少量数据采集。
- 持续限制：
  - 不使用 `sudo`，不修改系统。
  - 若缺少系统级依赖，只记录并报告。
  - 修改官方源码、改变重要依赖版本或采用非官方补丁前，先与用户商议。
- 当前动作：开始进行只读系统核验。

### 2026-07-25：完成初步研究

- 查阅了 RoboTwin 2 官方安装文档、官方 GitHub 仓库和使用文档。
- 官方基线要求包括 Linux、Python 3.10、推荐 CUDA 12.1 和 Vulkan 渲染支持。
- 确认工作区位于 NFS，约有 30 TB 可用空间。
- 创建研究文档：
  - `Vault-on-Fvl09/Robotwin2环境配置/RoboTwin2环境配置研究与实施草案.md`
- 未克隆代码、未创建环境、未安装依赖、未下载资产。

### 2026-07-25：研究笔记首次推送

- 将初版研究文档提交并推送到 `Vault-on-Fvl09` 的 `origin/main`。
- 提交：`ce73ccc docs: add RoboTwin 2 environment setup research`
- 此次 Git 操作不包含 RoboTwin 2 环境配置。

### 2026-07-25：收拢目录规划

- 用户提出避免将项目内容散落在 `/bigbig_nfs_share/lijunhui` 顶层。
- 将规划改为统一根目录 `/bigbig_nfs_share/lijunhui/Robotwin2/`。
- 研究文档已更新为新的 `project/env/cache/datasets/models/tmp` 布局。
- 新目录尚未创建；此次文档修改尚未提交或推送。

### 2026-07-25：建立长期配置约束与实时日志

- 更新工作区根目录 `AGENTS.md`，加入 RoboTwin 2 专用目录边界、脚本审计要求、禁止系统级安装、缓存约束和日志维护要求。
- 创建本实时日志。
- 当前仍未开始实际环境配置。

## 当前下一步

1. 获得用户对官方 SAPIEN/MPLib 包内补丁的明确确认。
2. 应用补丁后重新验证 imports 和 requirements。
3. 由服务器管理员修复 NVIDIA 驱动/NVML 与 NVIDIA Vulkan 设备可见性。
4. 驱动修复后运行官方 render test、clean demo 和少量数据采集。
5. 讨论是否删除三个已验证 ZIP，以回收约 13.9 GiB；未获许可前保留。

### 2026-07-25 15:03 +08:00：只读系统核验

- 用户已授权本次只读系统检查。
- 操作系统：Ubuntu 22.04.5 LTS，内核 `5.19.0-50-generic`，x86_64，glibc 2.35。
- CPU：2 × Intel Xeon Gold 6326，共 32 个在线 CPU 核。
- 内存：约 503 GiB，总可用约 477 GiB；Swap 2 GiB。
- CUDA Toolkit：`nvcc` 位于 `/share/apps/cuda/12.2/bin/nvcc`，版本 12.2。
- Python：系统 `/usr/bin/python3` 为 3.10.12；系统 pip 为 22.0.2。不会使用系统 pip 安装。
- 编译器：GCC/G++ 11.4.0。
- 已有工具：Git 2.34.1、`vulkaninfo`。
- 未找到：Conda、Mamba、Micromamba、CMake、Ninja、ffmpeg。
- GPU 检查失败：`nvidia-smi` 无法与 NVIDIA 驱动通信，因此尚不能确认 GPU 型号、显存或驱动版本。
- Vulkan loader 可运行，Instance Version 为 1.3.204，但只识别到 CPU 设备 `llvmpipe`；NVIDIA ICD `libGLX_nvidia.so.0` 初始化失败。
- `DISPLAY` 未设置，当前为 headless 会话。
- `vulkaninfo` 尝试创建 `/home/lijunhui/.cache/mesa_shader_cache`，因该目录只读而失败并禁用缓存；没有成功写入工作区外。后续运行前必须设置工作区内的 `XDG_CACHE_HOME`。
- 结论：
  - CPU、内存、Python 和编译器基线基本适合。
  - NVIDIA 驱动/设备可见性与 NVIDIA Vulkan 是当前硬阻塞，预计会阻止 GPU 仿真和正式渲染。
  - 可以继续进行工作区目录创建、仓库克隆和脚本审计，但在 GPU/Vulkan 问题解决前不能宣称基础仿真配置成功。

### 2026-07-25：创建目录并克隆官方仓库

- 已创建统一目录树：`project`、`env`、`cache`、`datasets`、`models`、`tmp` 和 `tools`。
- 官方仓库克隆到 `/bigbig_nfs_share/lijunhui/Robotwin2/project/RoboTwin`。
- Remote：`https://github.com/RoboTwin-Platform/RoboTwin.git`
- 当前 commit：`c3ddfa8b97d5519efa828b075999bd0006778e5e`
- Commit 说明：`Merge pull request #457 from FlowsMple/main`
- Commit 时间：2026-05-23 11:16:41 +08:00。
- 克隆后工作树干净。
- NFS 将仓库所有者报告为 `nobody:nogroup`，Git 触发 dubious ownership 保护。
- 仅在工作区专用 Git 配置 `/bigbig_nfs_share/lijunhui/.config/git/config` 中加入该仓库的精确 `safe.directory`，未修改系统 Git 配置。

### 2026-07-25：审计官方安装与资产脚本

- `script/_install.sh` 的行为：
  - 从 `script/requirements.txt` 安装依赖。
  - 从 GitHub `stable` 分支安装 PyTorch3D；没有锁定 commit。
  - 直接修改隔离环境中的 `sapien/wrapper/urdf_loader.py`。
  - 直接修改隔离环境中的 `mplib/planner.py`，删除 `or collide` 判断。
  - 将 CuRobo v0.7.8 克隆到仓库 `envs/curobo` 并 editable 安装。
  - 安装 `warp-lang==1.12.0` 和 `setuptools==69.5.1`。
- `script/requirements.txt` 的主要固定版本：
  - `torch==2.4.1`
  - `sapien==3.0.0b1`
  - `scipy==1.10.1`
  - `mplib==0.2.1`
  - `gymnasium==0.29.1`
  - `open3d==0.18.0`
  - `huggingface_hub==0.25.0`
- `_download_assets.sh` 在仓库 `assets/` 中下载并解压 `background_texture.zip`、`embodiments.zip` 和 `objects.zip`，随后删除这三个 ZIP。
- 资产下载器仅允许上述三个文件，来源为 Hugging Face 数据集 `TianxingChen/RoboTwin2.0`。
- 路径更新脚本会在 `assets/embodiments` 下根据 `*_tmp.yml` 生成带绝对路径的 `.yml` 文件。
- 未发现 `sudo` 或系统包管理器命令。
- 决策：不会直接盲跑官方脚本；先建立隔离环境并固定所有缓存，再逐步执行和验证。

### 2026-07-25：安装项目专用 Miniforge

- 系统未提供 Conda/Mamba，因此选择 Miniforge。
- 安装位置：`/bigbig_nfs_share/lijunhui/Robotwin2/tools/miniforge3`。
- 首次通过 GitHub `latest` 别名下载的安装器内部版本为 `26.3.2-3`，但通用 SHA-256 链接返回 404，官方发布索引未列出可校验 artifact。
- 安全决策：没有执行未能用官方哈希验证的 `26.3.2-3` 安装器；文件暂时保留在 `tmp/`。
- 改为下载官方明确列出哈希的 `Miniforge3-26.3.2-2-Linux-x86_64.sh`。
- 官方 SHA-256：`42260ffe3830fb953d5eee1bbb32229ff06aa7c3833c1ed7a9a0420a95685d94`。
- 本地校验结果：`OK`。
- 第一次执行安装器时，受限执行环境无法连接 `127.0.0.1` 代理，安装未完成，`conda` 尚未生成；所有残留均位于项目 `tools/miniforge3` 内。
- 随后在获准联网的执行环境中以 `-u` 模式续装同一前缀，成功完成。
- 安装结果：
  - Conda 26.3.2
  - Mamba 2.6.0
  - Miniforge base Python 3.13.13（只供环境管理器自身使用）
- 未运行 `conda init`，未修改 Shell 配置。

### 2026-07-25：创建 RoboTwin 2 Python 3.10 基础环境

- 创建项目配置：
  - `/bigbig_nfs_share/lijunhui/Robotwin2/config/condarc`
  - `/bigbig_nfs_share/lijunhui/Robotwin2/config/pip.conf`
  - `/bigbig_nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh`
- 所有 Conda、pip、PyTorch、Hugging Face、XDG 和临时缓存均固定到 `/bigbig_nfs_share/lijunhui/Robotwin2/`。
- 环境前缀：`/bigbig_nfs_share/lijunhui/Robotwin2/env`。
- 使用 Mamba 从 conda-forge 安装 Python、pip、CMake、Ninja、ffmpeg 和 unzip。
- 验证结果：
  - Python 3.10.20
  - pip 26.1.2
  - CMake 4.4.0
  - Ninja 1.13.2
  - ffmpeg 8.1.2
- 未使用系统 Python 或系统 pip。

### 2026-07-25：安装官方 Python requirements

- 在 `/bigbig_nfs_share/lijunhui/Robotwin2/env` 内执行：
  - `python -m pip install -r script/requirements.txt`
- 安装成功，`pip check` 输出 `No broken requirements found`。
- 关键实际版本：
  - PyTorch 2.4.1+cu121
  - TorchVision 0.19.1+cu121
  - SAPIEN 3.0.0b1
  - MPLib 0.2.1
  - Open3D 0.18.0
- 环境运行时首次导入 PyTorch 失败：
  - 系统预设 `LD_LIBRARY_PATH` 使其优先加载 `/share/apps/cuda/12.2/lib64/libnvJitLink.so.12`。
  - 读取该系统库返回 `Input/output error`。
- 对照测试临时移除 `LD_LIBRARY_PATH` 后，PyTorch 2.4.1+cu121 与 TorchVision 0.19.1+cu121 可以导入，证明 wheel 本体可用。
- 已在项目激活脚本中取消继承系统 `LD_LIBRARY_PATH`；需要 host CUDA Toolkit 的构建命令将单独显式设置路径。
- 随后的 SAPIEN 导入曾因缺少 `pkg_resources` 失败。
- 按官方 `_install.sh` 的固定版本安装 `setuptools==69.5.1` 后，`pkg_resources` 已恢复。
- 本次 requirements 完成后：
  - 环境占用约 6.2 GiB。
  - 项目缓存占用约 3.9 GiB。
  - 所有内容均位于 `/bigbig_nfs_share/lijunhui/Robotwin2/`。

### 2026-07-25：Codex 连接中断后的断点核验

- 用户报告 Codex 连接意外中断并要求继续。
- 上一条工具调用在界面中标记为 aborted，但只读核验确认 `setuptools==69.5.1` 已实际安装成功。
- `pip check` 仍通过。
- 官方仓库工作树干净，commit 仍为 `c3ddfa8b97d5519efa828b075999bd0006778e5e`。
- 没有将未返回的导入验证误记为成功；从导入测试重新继续。

### 2026-07-25：基础依赖导入验证

- 成功导入：
  - PyTorch 2.4.1+cu121
  - TorchVision 0.19.1+cu121
  - SAPIEN 3.0.0b1
  - MPLib 0.2.1
  - Open3D 0.18.0
  - Gymnasium 0.29.1
  - Trimesh 4.4.3
  - SciPy 1.10.1
  - h5py 3.16.0
  - Zarr 2.18.3
- PyTorch wheel 自带 CUDA runtime 版本为 12.1。
- `torch.cuda.is_available()` 为 `False`，设备数为 0；与此前 `nvidia-smi`/NVML 失败一致，GPU 仍不可用。
- Open3D 导入触发 Matplotlib 默认配置目录 `/home/lijunhui/.config/matplotlib` 不可写警告，实际临时缓存回退到项目 `tmp/`，没有成功写入工作区外。
- 已将 `MPLCONFIGDIR` 固定到 `/bigbig_nfs_share/lijunhui/Robotwin2/cache/matplotlib`，后续不再尝试默认 Home 配置目录。

### 2026-07-25：下载与核验官方资产

- 使用仓库自带 `assets/_download.py` 下载 Hugging Face 数据集 `TianxingChen/RoboTwin2.0` 中的三个目标 ZIP。
- 下载前通过 Hugging Face API 核验文件元数据：
  - `background_texture.zip`：10,970,687,027 bytes（约 10.217 GiB）
  - `embodiments.zip`：219,859,313 bytes（约 0.205 GiB）
  - `objects.zip`：3,737,778,549 bytes（约 3.481 GiB）
  - 总计：14,928,324,889 bytes（约 13.903 GiB）
- 下载耗时约 25 分 37 秒，支持断点续传。
- Hugging Face Hub 0.25.0 的 `local_dir` 模式在 `assets/.cache/huggingface` 创建了断点元数据；该位置与集中缓存规划不同，但仍严格位于 `/bigbig_nfs_share/lijunhui/Robotwin2/` 内。
- 下载完成后的三个文件字节数与远端元数据完全一致。
- 使用 `unzip -tq` 逐个验证，三个 ZIP 均报告 `No errors detected in compressed data`。
- 没有执行官方包装脚本中的 ZIP 删除操作，三个已验证压缩包目前仍保留在 `assets/`。

### 2026-07-25：解压与配置官方资产

- 解压前统计：
  - embodiments：943,612,753 uncompressed bytes，500 entries
  - objects：4,636,111,726 uncompressed bytes，10,070 entries
  - background textures：11,025,457,080 uncompressed bytes，11,003 entries
- 三个 ZIP 均成功解压，没有 CRC、权限或空间错误。
- 解压后的实际统计：
  - `assets/embodiments`：223 个普通文件，约 420 MiB
  - `assets/objects`：9,368 个普通文件，约 4.0 GiB
  - `assets/background_texture`：11,000 个普通文件，约 11 GiB
- ZIP 内自带 `__MACOSX` 元数据目录，按原始资产保留，没有擅自删除。
- 执行官方 `script/update_embodiment_config_path.py`：
  - 找到 6 个 `*_tmp.yml` 模板。
  - 成功生成 6 个 CuRobo 配置文件。
  - 写入的资产根路径为 `/bigbig_nfs_share/lijunhui/Robotwin2/project/RoboTwin`。
- 未解析的 `${ASSETS_PATH}` 只存在于原始 `*_tmp.yml` 模板中；生成的目标 `.yml` 未发现残留占位符。

### 2026-07-25：克隆并审计 CuRobo

- 按官方 `_install.sh` 固定的 tag 浅克隆 CuRobo v0.7.8 到：
  - `/bigbig_nfs_share/lijunhui/Robotwin2/project/RoboTwin/envs/curobo`
- 精确 commit：`d64c4b005459db10c5dd867d8b30a87d5bda9bdb`。
- NFS 同样将仓库所有者显示为 `nobody:nogroup`；已在工作区专用 Git 配置中加入该精确目录的 `safe.directory`。
- 安装审计结果：
  - `setup.py` 使用 PyTorch `CUDAExtension` 编译 5 个 CUDA 扩展。
  - 构建必须调用 host CUDA Toolkit 的 `nvcc`。
  - Python 依赖包括 pybind11、numpy-quaternion、yourdfpy、warp-lang、scikit-image 等。
  - 未发现 `sudo` 或系统包管理器调用。
- 尚未执行 CuRobo editable build；因为调用 `/share/apps/cuda/12.2/bin/nvcc` 超出工作区执行边界，需要用户专项许可。

### 2026-07-25：安装 CuRobo 纯 Python 依赖

- 安装官方固定 `warp-lang==1.12.0` 及 CuRobo 的纯 Python 依赖。
- 首次命令显式请求未固定的最新 scikit-image，解析器安装 scikit-image 0.25.2，并将 RoboTwin 固定的 SciPy 1.10.1 升级到 1.15.3。
- 该偏离被立即识别，没有继续编译或运行测试。
- 修复：
  - 重新固定 `scipy==1.10.1`
  - 选择与之兼容的 `scikit-image==0.21.0`
- 修复后 `pip check` 通过。
- 当前验证版本：
  - SciPy 1.10.1
  - scikit-image 0.21.0
  - warp-lang 1.12.0
  - numpy-quaternion 2024.0.13
  - yourdfpy 0.0.60

### 2026-07-25：用户要求 CUDA 工具链完全位于个人目录

- 用户明确要求：“你要用啥还是都在我的目录里装好，不要用 share 的”。
- 决策：
  - 不使用 `/share/apps/cuda/12.2`。
  - 不使用 `/usr/local/cuda-12.2`。
  - 在 `/bigbig_nfs_share/lijunhui/Robotwin2/tools/cuda-12.1` 安装项目专用 CUDA 12.1 编译器、头文件和开发库。
  - CUDA 12.1 与当前 PyTorch 2.4.1+cu121 保持一致。
- 已更新工作区 `AGENTS.md`，将“不使用共享 CUDA Toolkit”设为长期约束。
- 已更新项目激活脚本：
  - `CUDA_HOME` 固定为项目内 CUDA 12.1。
  - 从运行时 `PATH` 中过滤 `/share/apps/cuda/*` 和 `/usr/local/cuda*`。
  - 不继承系统 `LD_LIBRARY_PATH`。
- 说明：NVIDIA 内核驱动和设备接口属于系统层，不能安装在个人目录；本项目只会检查，不会修改。

### 2026-07-25：安装并验证项目本地 CUDA 12.1

- 使用项目内 Mamba，从 NVIDIA 官方 `nvidia/label/cuda-12.1.1` channel 创建独立工具链前缀：
  - `/bigbig_nfs_share/lijunhui/Robotwin2/tools/cuda-12.1`
- 安装 CUDA Toolkit 12.1.1，共 64 个包，下载约 4 GiB。
- 内容包括 `nvcc`、headers、CUDART、cuBLAS、cuFFT、cuSPARSE、cuSOLVER 等编译和开发库；不包含 NVIDIA 内核驱动。
- 验证：
  - `nvcc` 路径：`/bigbig_nfs_share/lijunhui/Robotwin2/tools/cuda-12.1/bin/nvcc`
  - `nvcc` 版本：12.1.105
  - `CUDA_HOME`：`/bigbig_nfs_share/lijunhui/Robotwin2/tools/cuda-12.1`
  - `PATH` 中不存在 `/share/apps/cuda/*` 或 `/usr/local/cuda*`
  - 本地 CUDA 工具链占用约 4.4 GiB
- 只读 PCI 检查识别到 8 张 NVIDIA GeForce RTX 3090（GA102）。
- RTX 3090 的 CUDA compute capability 为 8.6，因此项目激活脚本固定 `TORCH_CUDA_ARCH_LIST=8.6`，避免驱动不可用时 PyTorch 构建系统无法自动判断架构。

### 2026-07-25：使用本地 CUDA 12.1 编译 CuRobo

- 工作目录：
  - `/bigbig_nfs_share/lijunhui/Robotwin2/project/RoboTwin/envs/curobo`
- 构建命令摘要：
  - `MAX_JOBS=8 python -m pip install -e . --no-build-isolation --no-deps`
- 环境要点：
  - `CUDA_HOME=/bigbig_nfs_share/lijunhui/Robotwin2/tools/cuda-12.1`
  - `TORCH_CUDA_ARCH_LIST=8.6`
  - `PATH` 中无 `/share/apps/cuda` 或 `/usr/local/cuda`
- 结果：成功构建并安装 `nvidia_curobo-0.7.8` editable wheel。
- 生成五个 CUDA 扩展：
  - `geom_cu`
  - `kinematics_fused_cu`
  - `lbfgs_step_cu`
  - `line_search_cu`
  - `tensor_step_cu`
- 首次直接导入扩展时出现 `libc10.so` 未找到；这是因为测试没有先导入 PyTorch。
- 按正确顺序先 `import torch` 后，CuRobo 0.7.8 和五个扩展均成功加载。
- `torch.cuda.is_available()` 仍为 `False`，说明编译产物有效，但系统 NVIDIA 驱动问题仍阻止实际 GPU 执行。

### 2026-07-25：PyTorch3D 安装尝试与当前进度

- 官方命令直接从 `git+https://github.com/facebookresearch/pytorch3d.git@stable` 安装。
- 第一次尝试：
  - pip 将源码克隆到项目 `tmp/`。
  - 因 NFS 所有权映射为 `nobody:nogroup`，Git 在临时目录触发 dubious ownership。
  - 未进入编译。
- 安全处理：
  - 没有添加通配符 `safe.directory`。
  - 将官方 stable 分支固定克隆到 `/bigbig_nfs_share/lijunhui/Robotwin2/project/pytorch3d`。
  - 精确 commit：`75ebeeaea0908c5527e7b1e305fbc7681382db47`。
  - 上游 commit 说明：`update version to 0.7.8`。
- 第二、第三次尝试：
  - 工作区 global 和项目重定向 system Git 配置都能让直接 `git status` 通过。
  - 但 pip 的 setuptools_scm 文件发现子进程仍忽略这些配置并报 dubious ownership。
  - 两次均停在 metadata 阶段，未进入编译。
- 当前安全方案：
  - 从精确 commit 使用 `git archive` 导出不含 `.git` 的源码快照：
    `/bigbig_nfs_share/lijunhui/Robotwin2/tmp/pytorch3d-75ebeea-src`
  - 不修改上游源码，不放宽 Git 安全策略。
  - 显式设置：
    - `FORCE_CUDA=1`
    - `CUB_HOME=/bigbig_nfs_share/lijunhui/Robotwin2/tools/cuda-12.1/include`
    - `SETUPTOOLS_SCM_PRETEND_VERSION=0.7.8`
    - `MAX_JOBS=8`
  - metadata 已成功生成，`iopath`/`portalocker` 依赖已解析。
  - 当前状态：PyTorch3D 0.7.8 CUDA wheel 正在编译，尚未得出成功或失败结论。

### 2026-07-25：PyTorch3D 编译完成

- 上一条“正在编译”状态随后正常结束。
- 成功构建：
  - `pytorch3d-0.7.8-cp310-cp310-linux_x86_64.whl`
  - wheel SHA-256：`5ea2360aec2717d5eaaac8ed30f2b8014a403553fd9808a7e9796d50a1cc07e4`
  - `iopath-0.1.10-py3-none-any.whl`
- 成功安装：
  - PyTorch3D 0.7.8
  - iopath 0.1.10
  - portalocker 3.2.0
- wheel 缓存位于项目 `cache/pip/wheels`。
- 下一步：验证 `pytorch3d._C` 扩展加载；尚未宣称 GPU 运算可用。

### 2026-07-25：PyTorch3D 加载验证

- 成功导入：
  - PyTorch 2.4.1+cu121
  - PyTorch3D 0.7.8
  - `pytorch3d._C` 编译扩展
- `pip check` 通过。
- `torch.cuda.is_available()` 仍为 `False`；扩展编译和动态加载成功不等于 GPU 运行可用。

### 2026-07-25：驱动、Vulkan、SAPIEN 与渲染验证

- `nvidia-smi` 复测仍失败：无法与 NVIDIA 驱动通信。
- `vulkaninfo --summary`：
  - Vulkan Instance Version 1.3.204
  - 唯一设备为 CPU `llvmpipe`
  - 没有 NVIDIA Vulkan 物理设备
- 首次 SAPIEN 场景测试：
  - `sapien.Scene()` 默认同时创建 PhysX 与 RenderSystem。
  - 创建 Vulkan device 时抛出 `vk::PhysicalDevice::createDeviceUnique: ErrorExtensionNotPresent`。
  - 随后进程发生 segmentation fault。
  - 工作区根目录未发现生成的 `core*` 文件。
- 官方 `python script/test_render.py`：
  - 输出 `Render Error`
  - 没有通过渲染验证
- 第一次 CPU-only 复测：
  - 显式只创建 `PhysxCpuSystem`，但使用 `scene.add_ground()`。
  - 该便利函数仍隐式创建 visual material，因此再次触发 Vulkan `ErrorExtensionNotPresent`。
- 第二次真正 CPU-only 复测：
  - 只创建 `PhysxCpuSystem`。
  - 只添加 plane collision，不创建任何 visual。
  - `scene.step()` 成功。
- 结论：
  - SAPIEN PhysX CPU 物理核心可用。
  - 所有涉及 RenderSystem/visual 的功能当前不可用。
  - RoboTwin 基础仿真、clean demo 和数据采集依赖渲染，仍被系统 NVIDIA 驱动/NVIDIA Vulkan 可见性阻塞。

### 2026-07-25 16:39 CST：应用用户批准的官方兼容性补丁

- 用户明确批准应用此前审阅过的 SAPIEN/MPLib 官方安装补丁。
- 修改范围严格位于隔离环境：
  `/bigbig_nfs_share/lijunhui/Robotwin2/env/lib/python3.10/site-packages/`
- SAPIEN `wrapper/urdf_loader.py`：
  - URDF/SRDF 文本读取显式使用 UTF-8。
  - 将自动推导 SRDF 文件名时缺失句点的 `urdf_file[:-4] + "srdf"` 修正为
    `urdf_file[:-4] + ".srdf"`。
- MPLib `planner.py`：
  - 按官方 RoboTwin 安装说明移除 screw planning 中
    `status != "Success" or collide` 的额外 `or collide` 失败判定。
- 首次验证命令误用了并不存在的
  `/bigbig_nfs_share/lijunhui/Robotwin2/activate.sh`，因此 shell 在运行 Python
  前即退出；这是验证命令入口错误，不是补丁导入失败。
- 已确认实际激活脚本是
  `/bigbig_nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh`。
- 下一步：用正确入口验证两个模块导入和补丁文本，然后继续只读诊断系统 NVIDIA
  驱动；不会修改工作区外文件。

### 2026-07-25 16:40 CST：补丁验证与 GPU 可见性结论纠正

- 使用正确激活入口后：
  - SAPIEN `urdf_loader.py` 导入成功。
  - MPLib `planner.py` 导入成功。
  - SAPIEN 的 UTF-8 与 `.srdf` 修正均已在实际加载文件中确认。
  - MPLib screw planning 实际代码已不再用 `collide` 作为返回失败条件；首次文本
    断言因要求完全匹配 `if status != "Success":` 而显示 False，但该断言检查的是
    另一处代码格式，不代表官方补丁未应用。后续上下文检查确认目标逻辑已移除。
- 沙箱内只读观察：
  - NVIDIA 535.247.01 内核模块已加载。
  - 8 张 RTX 3090 均绑定 `nvidia` 驱动，`/proc/driver/nvidia/gpus` 可列出 0–7。
  - 但 Codex 文件沙箱中的 `/dev` 没有映射 `/dev/nvidia0…7` 和
    `/dev/nvidiactl`，因此沙箱内 `nvidia-smi` 必然失败。
- 经用户批准，在沙箱外进行同一台宿主机的只读复核：
  - 真实 `/dev/nvidia0…7`、`/dev/nvidiactl`、`/dev/nvidia-uvm` 全部存在。
  - `nvidia-smi` 成功，驱动版本 535.247.01，8 张 RTX 3090 全部可枚举。
  - 因此此前“服务器 NVIDIA 驱动整体不可用/缺失”的结论不准确；根因之一是
    Codex 沙箱设备隔离造成的假阴性。此处正式追加纠正，不改写旧记录。
- 同时发现真实宿主机故障：
  - GPU 2（PCI `0000:39:00.0`）显示风扇和功耗 `ERR!`。
  - 详细查询显示 `GPU Reset Status: Reset Required: Yes`、
    `System is not in ready state`，编码器/解码器与功率查询均为 Unknown Error。
  - NVIDIA-only Vulkan 能加载 ICD，但 `vkCreateDevice` 返回
    `ERROR_INITIALIZATION_FAILED`。
  - PyTorch 在真实 GPU 可见环境能枚举 8 张卡，但 CUDA driver initialization
    仍失败；SAPIEN `get_device_summary()` 返回 `RuntimeError: invalid PCI string`。
- 当前更准确的判断：
  - 驱动已经安装且正在运行，并非缺驱动。
  - GPU 2 处于需要 reset 的异常状态，很可能使 CUDA/Vulkan 多 GPU 初始化链整体
    失败；还需逐卡隔离验证后才能把因果关系定为最终结论。
- 所有上述系统侧操作均为只读；未安装、卸载、重载驱动，也未创建系统文件。

### 2026-07-25 16:41 CST：逐卡隔离确认故障卡与修复建议

- 在用户批准的真实 GPU 可见上下文中，分别以单独进程设置
  `CUDA_VISIBLE_DEVICES=0` 至 `7` 进行 PyTorch 初始化：
  - GPU 0、1、3、4、5、6、7：`torch.cuda.is_available() == True`，均可识别为
    NVIDIA GeForce RTX 3090。
  - 仅 GPU 2：CUDA driver initialization failed。
- 该结果与 GPU 2 的 `Reset Required: Yes`、`System is not in ready state`、
  风扇/功耗 `ERR!` 相互印证，足以确认当前 CUDA 初始化故障来自物理 GPU 2
  （PCI `0000:39:00.0`），不是本地 CUDA 12.1、PyTorch 或 RoboTwin 安装错误。
- 在真实 GPU 可见上下文补跑官方 `python script/test_render.py`，仍输出
  `Render Error`。原因是 `CUDA_VISIBLE_DEVICES` 只控制 CUDA 应用的设备枚举，
  不保证 Vulkan/SAPIEN 不枚举异常的物理卡。
- NVIDIA 官方文档核对结果：
  - `CUDA_VISIBLE_DEVICES` 可控制 CUDA 应用可见设备及枚举顺序。
  - `nvidia-smi --gpu-reset -i 2` 可尝试清除 GPU 硬件/软件异常状态，但需要
    root，且目标设备不能被 CUDA、X server、监控程序等任何客户端占用。
  - 当前 `nvidia-smi` 显示 Xorg 正在使用 GPU 2，因此不能直接在线 reset。
  - 若 reset 不成功或 reset 后仍不健康，官方建议对节点做完整 power cycle。
- 推荐恢复顺序（需要服务器管理员执行，当前未执行）：
  1. 停止/迁移该节点上的 GPU 任务，停止占用 GPU 2 的图形/监控客户端。
  2. 管理员尝试 `nvidia-smi --gpu-reset -i 2`，随后重新检查
     `nvidia-smi -i 2 -q`、逐卡 CUDA 和 NVIDIA Vulkan。
  3. 如果无法释放 Xorg、reset 被拒绝或 reset 后仍异常，安排节点重启/断电重启。
  4. 若完整冷启动后 GPU 2 再次进入相同状态，检查该卡供电线、PCIe 插槽/转接、
     散热和硬件本体，并由管理员收集完整 NVRM/Xid 日志评估驱动升级或换卡。
- 当前没有执行 reset、停止进程、重启、驱动修改等系统变更。
- 后续验收条件：8 张卡逐卡 CUDA 均通过；NVIDIA-only `vulkaninfo` 能创建逻辑
  设备；SAPIEN 官方 render test 输出 `Render Well`；再继续 clean demo 与数据采集。

### 2026-07-25 16:59 CST：为服务器管理员复核并形成独立问题单

- 按用户要求再次进行当前状态核查，结果与上一轮一致：
  - 驱动 535.247.01 正常加载，真实 NVIDIA 设备节点齐全。
  - GPU 2（PCI `0000:39:00.0`）持续显示 `Reset Required: Yes`、
    `System is not in ready state`、功耗 Unknown Error 和风扇 `ERR!`。
  - GPU 0、1、3、4、5、6、7 单卡 CUDA 全部通过；仅 GPU 2 失败。
  - 全部 8 张卡可见时，PyTorch CUDA 整体初始化失败。
  - NVIDIA-only Vulkan 仍为 `ERROR_INITIALIZATION_FAILED`。
  - RoboTwin2 官方 `script/test_render.py` 仍输出 `Render Error`。
- 当前 Xorg PID 3023 使用 GPU 0–7，包括故障 GPU 2；管理员进行在线 reset 前必须
  先协调并释放图形/其他客户端占用，不能直接结束未知进程。
- 新建面向师哥/管理员的独立交接文档：
  `Robotwin2环境配置/需要师哥协助处理的GPU与Vulkan问题.md`
- 文档包含：明确结论、设备唯一标识、现场证据、影响范围、管理员处理顺序、风险提示、
  复现命令和恢复后的五项验收标准。
- 本轮仍未执行 sudo、reset、停止进程、重启或任何系统修改。

### 2026-07-26 19:48 CST：用户确认 GPU 2 不可用，决定改用剩余 7 卡

- 用户已就 GPU 2 问题与师哥/管理员求证：**确认 GPU 2 当前不可用**，短期内不会修复。
- 用户明确决定：**后续所有实验不使用 GPU 2，只用剩余 7 张卡（物理索引 0、1、3、4、5、6、7）运行。**
- 用户同时强调操作边界：所有动作只停留在个人工作目录 `/bigbig_nfs_share/lijunhui`，只做只读系统检查，不影响其他同学正在跑的 GPU 作业。
- 因此本项目的策略从「等待管理员修复 GPU 2」调整为「在环境层面稳定屏蔽 GPU 2、用 7 卡继续推进渲染与仿真验证」。GPU2 交接单继续保留，供将来硬件修复参考。

### 2026-07-26 19:48 CST：本会话（Claude Code）真实 GPU 上下文只读复核

- 本会话运行于宿主机 `fvl09` 的真实 GPU 可见上下文（与此前 Codex 文件沙箱不同），`/dev/nvidia0…7`、`/dev/nvidiactl`、`/dev/nvidia-uvm` 等设备节点齐全，`nvidia-smi` 正常。
- 复核时刻的现场状态（只读）：
  - 驱动 535.247.01，8 × RTX 3090。
  - **GPU 2（PCI `00000000:39:00.0`）风扇与功耗仍显示 `ERR!`**，异常状态与此前记录一致，未恢复。
  - GPU 0 当时有其他同学的作业在运行（利用率约 52%、约 3.5 GiB 显存占用）；本项目验证刻意避免在他人占用的卡上分配显存或跑重负载。
- 稳定的 GPU 索引 / PCI / UUID 映射（用于屏蔽 GPU 2 时优先用 UUID，避免重启后索引漂移）：
  - GPU 0 `00000000:35:00.0` `GPU-1a315960-e3fc-f69d-fa25-8c6210f754ac`
  - GPU 1 `00000000:36:00.0` `GPU-d8638855-cdda-c2cd-1857-ff509bdb585f`
  - **GPU 2 `00000000:39:00.0` `GPU-4329227f-0eb2-20ca-97c6-e97253d558cf`（故障，屏蔽）**
  - GPU 3 `00000000:3D:00.0` `GPU-67e93345-89b9-771f-c340-cdc751a7bee4`
  - GPU 4 `00000000:9C:00.0` `GPU-be754450-1883-d497-fcfe-29774fb1b09a`
  - GPU 5 `00000000:9D:00.0` `GPU-0834bd1a-820c-6d59-d755-161b31cea28b`
  - GPU 6 `00000000:A0:00.0` `GPU-e4ae94ff-288b-6d93-3af6-a0e9c975ce8e`
  - GPU 7 `00000000:A4:00.0` `GPU-b2b3d6b3-ac20-bb94-2203-06ab2d6abb3a`

### 2026-07-26 19:48 CST：CUDA 侧屏蔽 GPU 2 后 7 卡全部可用（关键突破）

- 在 RoboTwin2 环境中对照测试（均为瞬时只读式 CUDA 初始化，未做重负载分配）：
  - 8 卡全可见：`torch.cuda.is_available()` = **False**，并伴随 `CUDA driver initialization failed` 警告——异常的 GPU 2 毒化了整个 CUDA 初始化链。
  - `CUDA_VISIBLE_DEVICES=0,1,3,4,5,6,7`（屏蔽 GPU 2）：`torch.cuda.is_available()` = **True**，`device_count()` = **7**，7 张卡均识别为 NVIDIA GeForce RTX 3090。
- 结论：只要在环境层稳定屏蔽物理 GPU 2，CUDA 计算侧即完全正常，无需等待硬件修复即可用 7 卡推进。
- 下一步：验证渲染侧（NVIDIA Vulkan / SAPIEN）是否也能通过屏蔽 GPU 2 绕开异常卡，力争官方 `test_render.py` 输出 `Render Well`。

### 2026-07-26 20:05 CST：定位 Vulkan 全局中毒并找到渲染侧绕过方案（关键突破）

- 先用系统 `vulkaninfo`（仅 NVIDIA ICD）诊断渲染侧：
  - `vkCreateDevice: Failed to create device chain` / `ERROR_INITIALIZATION_FAILED`，在打印任何物理设备前就失败。
  - 即便用 Vulkan loader 的设备过滤（`VK_LOADER_DEVICE_SELECT` 指向健康的 GPU 0 UUID）也仍然失败。
  - 结论：与 CUDA 不同，NVIDIA Vulkan ICD 在 `vkCreateDevice` 阶段会**急切地触碰所有物理 GPU**，只要异常的 GPU 2 还被驱动枚举，Vulkan 设备链创建就**全局失败**，因此 `vulkaninfo` 无法作为本机渲染可用性的判据。
  - 用非特权 mount namespace 隐藏 `/dev/nvidia2` 的尝试被执行环境的安全分类器拦截（涉及 mount，属系统相邻操作），未采用。
- 改从 SAPIEN 层面验证，发现 SAPIEN 用 CUDA 可见性来选择渲染设备，可绕过全局枚举：
  - `sapien.SapienRenderer(device=...)` 接受 `sapien.Device`；`sapien.Device("cuda:0")` 在屏蔽 GPU 2 后成功解析（映射到物理 GPU 3，PCI `0000:3d:00.0`）。
  - 用 `SapienRenderer(device=sapien.Device("cuda:0"))` 显式指定健康卡后，完整 ray-tracing 初始化路径输出 **Render Well**。
- 进一步验证**官方未改动的 `script/test_render.py`（默认不传 device）**，只调整 `CUDA_VISIBLE_DEVICES`：
  - `CUDA_VISIBLE_DEVICES=3`（单张健康空闲卡）：**Render Well** ✅
  - `CUDA_VISIBLE_DEVICES=3,1,4,5,6,7,0`（全部 7 张健康卡，排除 GPU 2）：**Render Well** ✅
  - 全 8 卡可见（基线）：**Render Error** ❌
- **最终结论（渲染侧修复方案，零代码改动）**：
  - SAPIEN 默认渲染器会依据 CUDA 可见设备来选择 Vulkan 物理设备并只在该卡上创建设备链；只要用 `CUDA_VISIBLE_DEVICES` 把 GPU 2 排除，**CUDA 计算与 SAPIEN 渲染同时恢复正常**，无需修改任何官方源码，也无需等待硬件修复。
  - 系统 `vulkaninfo` 仍会失败，但这只是它走全局枚举路径所致，不代表 RoboTwin2 渲染不可用；渲染可用性以官方 `test_render.py` 为准。
- 决策：把「排除 GPU 2」固化进项目激活脚本，作为 7 卡默认环境。所有操作均为只读诊断或用户目录内验证，渲染测试仅短暂使用空闲的健康卡（物理 GPU 3），未干扰他人作业，未做任何系统修改。

### 2026-07-26 20:10 CST：将 GPU 2 屏蔽固化进激活脚本并端到端验证

- 修改 `config/activate_robotwin2.sh`（仅用户目录内文件），新增「屏蔽故障 GPU 2」段：
  - 定义 `ROBOTWIN_BAD_GPU_UUID`（GPU 2 的 UUID）与 `ROBOTWIN_GOOD_GPUS`（7 张健康卡的 UUID 列表）。
  - 当用户未显式设置 `CUDA_VISIBLE_DEVICES` 时，默认 `export CUDA_VISIBLE_DEVICES="$ROBOTWIN_GOOD_GPUS"`；若用户已设置则尊重其选择（脚本注释提醒切勿包含 GPU 2）。
  - 使用稳定 UUID 而非物理索引，避免重启后索引漂移误伤好卡。
- 端到端验证（source 更新后的激活脚本、未手动设置 CUDA_VISIBLE_DEVICES）：
  - 激活脚本自动把 `CUDA_VISIBLE_DEVICES` 设为 7 张健康卡 UUID。
  - `torch.cuda.is_available()` = **True**，`device_count()` = **7**。
  - 官方未改动的 `python script/test_render.py` 输出 **Render Well**。
- 里程碑：此前长期阻塞的「渲染不可用」在不修复 GPU 2 硬件、不改官方源码、不做系统修改的前提下已解除；RoboTwin2 现可在 7 张健康卡上进行渲染与 GPU 仿真。
- 使用约定（供后续训练/采集）：
  - 每次实验优先挑选空闲的健康卡，避免占用同学正在使用的卡（如复核时 GPU 0 有他人作业）。
  - 手动指定设备时，用逻辑索引（激活后 cuda:0..6 对应 7 张健康卡）或健康卡 UUID，**绝不使用物理索引 2 或 GPU 2 UUID**。
- 下一步：跑通一个 clean demo（单任务、少量 episode 数据采集），验证完整仿真+渲染+存储链路。

### 2026-07-26 20:00 CST：clean demo 冒烟采集（进行中）

> 执行上下文：Claude Code，宿主机 fvl09 真实 GPU 上下文。RoboTwin 2 当前由 Claude Code 作为主动执行方推进。

- 目的：在 7 卡（排除 GPU 2）方案下，端到端验证「仿真 + 运动规划 + SAPIEN 渲染 + 存储」链路。
- 审计 `collect_data.sh`：它内部 `export CUDA_VISIBLE_DEVICES=${gpu_id}`（**用物理索引直接覆盖**激活脚本的 UUID 默认值）；因此手动跑采集时 `gpu_id` 必须传健康卡的物理索引，**绝不能传 2**。其调用的 `./script/.update_path.sh` 实际不存在（被 `2>/dev/null` 静默跳过），无副作用。
- 只读检查当时 GPU 占用后，选空闲健康卡 **物理 GPU 3** 采集，避开他人作业（GPU 0 当时有他人任务）。
- 新建冒烟配置 `task_config/demo_clean_smoke.yml`（复制自 `demo_clean.yml`，仅把 `episode_num` 由 50 改为 3、`save_freq` 改为 3），不改动官方 `demo_clean.yml`。
- 运行：`bash collect_data.sh beat_block_hammer demo_clean_smoke 3`（后台，日志 `Robotwin2/tmp/clean_demo_smoke.log`）。
- 已观察到的进度：
  - nvidia-smi 确认采集进程落在 GPU 3（UUID `GPU-67e93345…`），未占用 GPU 0/GPU 2。
  - 种子搜索完成：episode 0 seed=0 失败→seed=1 成功；episode 1 seed=2 成功；episode 2 seed=3 成功（4 次尝试失败 1 次）。
  - 已写出 `seed.txt`、`scene_info.json`、`_traj_data/episode0..2.pkl`。
  - 进入 `[Start Data Collection]`，正在逐帧渲染并保存 episode 0 的相机观测（head/wrist D435，RGB）。
- 结论待定：等待 3 个 episode 全部渲染保存完成后，再核验产物结构并追加最终结果。

### 2026-07-26 20:04 CST：clean demo 冒烟采集成功（端到端链路打通）

> 执行上下文：Claude Code，宿主机 fvl09 真实 GPU 上下文，采集落在物理 GPU 3。

- 采集全部完成，进程正常退出（期间一次 `pgrep` 显示 running 是与退出清理的瞬时竞态，随后确认进程已结束，GPU 3 上只剩他人作业）。
- 3 个 episode 全部成功：
  - 种子：`seed.txt` = `1 2 3`（episode 0 seed=0 失败后用 seed=1）。
  - 视频：`video/episode0.mp4`(517 帧)、`episode1.mp4`(556 帧)、`episode2.mp4`(508 帧)，均 320×240 @ 30 FPS。
  - `.cache/episode*` 已按流程自动清理。
- 产物结构（`data/beat_block_hammer/demo_clean_smoke/`，共约 67 MiB）：
  - `data/episode0..2.hdf5`（约 27–31 MiB/个）
  - `instructions/episode0..2.json`（语言指令）
  - `_traj_data/episode0..2.pkl`、`scene_info.json`、`seed.txt`
- 用 h5py 核验 `episode0.hdf5`（只读），结构完整且符合预期：
  - `joint_action/`：`left_arm`(517,6)、`right_arm`(517,6)、左右 gripper、`vector`(517,14)。
  - `endpose/`：左右 `endpose`(517,7) 与左右 gripper。
  - `observation/{front,head,left,right}_camera/`：每视角 `rgb`(517, 变长编码字节) + `intrinsic_cv`/`extrinsic_cv`/`cam2world_gl`。共 4 路相机、517 个时间步。
  - `pointcloud`(517,0)：本配置关闭点云，符合预期。
- **里程碑结论**：在排除 GPU 2 的 7 卡方案下，RoboTwin 2 的「场景仿真 + CuRobo 运动规划 + SAPIEN 多相机光追渲染 + HDF5/视频/指令存储」完整链路已端到端验证通过，无需修复 GPU 2 硬件、无需改动官方源码、无任何系统级修改。
- 备注：冒烟数据（约 67 MiB，`data/beat_block_hammer/demo_clean_smoke/`）与冒烟配置 `task_config/demo_clean_smoke.yml` 暂时保留在项目内，是否删除或改跑完整 `demo_clean`（50 episode）等用户决定。
- 下一步（待用户确认）：1) 视需要跑完整 `demo_clean` 或更多任务的数据采集；2) 再按具体策略（ACT/DP/DP3/RDT/Pi0 等）分别创建互不冲突的独立训练环境。

### 2026-07-26 20:20 CST：编写零基础进度报告并更新长期记忆

- 按用户要求编写面向零基础同学的阶段性进度报告：
  `Vault-on-Fvl09/Robotwin2环境配置/2026-07-26环境配置进度报告.md`
  - 内容：RoboTwin 2 是什么、当前进度总览（打勾表）、做过的工作通俗版、坏卡 GPU 2 的坑与解决、
    手把手使用步骤（激活/自检/采集/数据位置/常见坑）、下一步计划、遵守的纪律。
- 更新长期项目记忆 `CLAUDE.md` 的 §4.4「当前状态」：
  - 阶段改为「基础仿真 + 渲染 + 数据采集全链路已端到端打通（7 卡方案）」。
  - 补充 clean demo 采集已验证、`collect_data.sh` 用物理索引覆盖 CVD 的注意事项、进度报告路径。
  - 「当前下一步」改为完整 `demo_clean`/多任务采集 与 按策略建独立训练环境。
- 本轮仅编辑用户目录内的笔记与项目记忆文件，未做 Git 提交，未改动环境或系统。

### 2026-08-04：从 fvl09 迁移到 fvl05 后的首轮路径修复与 GPU 盘点

> 执行上下文：Codex，当前服务器 `fvl05`，个人工作区 `/nfs_share/lijunhui`。用户授权修复个人工作区内的迁移配置；未执行系统级修改、GPU 作业、Git commit 或 push。

- 背景：fvl09 故障后，工作区整体迁移到 fvl05。原根路径 `/bigbig_nfs_share/lijunhui` 已失效，当前根路径为 `/nfs_share/lijunhui`。
- 编辑前重新检查了仓库状态：
  - `Robotwin2/project/RoboTwin`：`main...origin/main`，工作树干净。
  - `Vault-on-Fvl09`：存在用户原有的 `Idea/README.md` 修改和一份未跟踪的长动作理解笔记；本轮不覆盖、不暂存这些改动。
  - `clash-for-linux`：存在大量迁移前已有改动；本轮不吸收或回退它们。
- 已修复路径：
  - `Robotwin2/config/activate_robotwin2.sh`、`condarc`、`pip.conf`、`git-system`。
  - 工作区 `.config/git/config` 的精确 `safe.directory` 与 GitHub CLI credential helper 路径；修复后迁移来的三个仓库均可正常执行 `git status`。
  - `Robotwin2/tools/miniforge3/_conda` 的旧绝对软链接。
  - RoboTwin Python 环境中 73 个命令脚本的 shebang/前缀，以及 CuRobo/PyTorch3D editable/direct-url 元数据和 Tcl/Tk 配置内的旧根路径。
  - `AGENTS.md` 与 `CLAUDE.md` 已改用 fvl05 当前根路径，并把 fvl09 运行结论明确降级为历史记录。
- 激活与 Python 验证：
  - 未激活项目时，继承的系统 `/share/apps/cuda/12.2` 动态库会使 PyTorch 导入命中 `libnvJitLink.so.12` I/O error。
  - 通过唯一入口 `source /nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh` 后，`LD_LIBRARY_PATH` 被清理，Python 前缀为迁移后的 `Robotwin2/env`，PyTorch `2.4.1+cu121` 可正常导入。
- fvl05 GPU/驱动只读盘点：
  - PCI 枚举到 8 张 NVIDIA RTX A6000，bus ID 为 `01:00.0`、`23:00.0`、`41:00.0`、`61:00.0`、`81:00.0`、`a1:00.0`、`c1:00.0`、`e1:00.0`。
  - NVIDIA 内核模块已加载，版本 `535.274.02`；但当前执行上下文不存在 `/dev/nvidia*` 设备节点，`nvidia-smi` 报无法与驱动通信。
  - 项目激活后 PyTorch 报 `torch.cuda.is_available() == False`、`device_count() == 0`，并警告无法初始化 NVML。
  - 因此目前只能确认 PCI 硬件与内核模块存在，不能确认 GPU UUID、健康、占用、CUDA 或 Vulkan 可用性，也不能判定为某一张物理卡故障。
- 安全修正：已从项目激活脚本移除 fvl09 的坏 GPU 2 UUID 与七卡白名单。fvl05 不再继承旧索引/UUID 假设，且在完成新服务器 GPU 验收前不运行渲染、采集或训练。
- 当前阻塞与下一步：需要在能够映射 `/dev/nvidia*` 的宿主机/会话上下文中重新运行 `nvidia-smi`，确认八卡 UUID、健康与占用；随后依次验证 PyTorch CUDA、官方 `script/test_render.py`，最后才考虑受控 smoke collection。

### 2026-08-04：fvl05 宿主机 GPU 与官方渲染复核通过（对前条沙箱观察的补充更正）

- 进入获批的宿主机只读设备上下文后，`nvidia-smi` 正常；前条 `/dev/nvidia*` 缺失和 CUDA 不可用仅发生在 Codex 默认文件沙箱中，不代表宿主机驱动故障。
- fvl05 有 8 张 NVIDIA RTX A6000（每张 49140 MiB），驱动 535.274.02。索引与 UUID：
  - 0 `GPU-2c620e6c-9639-2022-b573-9847dfa33769`
  - 1 `GPU-414c52ba-72c6-fc45-95d6-1e9750bbc21b`
  - 2 `GPU-4306d28e-0eeb-2e26-bda4-b1b44058f63e`
  - 3 `GPU-d5b84492-c467-0080-206f-2456cef0c338`
  - 4 `GPU-6a2b7387-0c6e-f68d-4f88-92e859c27da7`
  - 5 `GPU-9dd3c02d-192d-3536-b12e-b1be3a605be2`
  - 6 `GPU-8678470b-2ef8-1672-7c4c-8b55d183216d`
  - 7 `GPU-4c836e67-fb8e-a993-002c-cb83b10a6ead`
- 查询时 GPU 1 与 GPU 3 有大显存任务，GPU 0 有约 1.2 GiB 任务，GPU 4–7 各有约 266 MiB Ray worker；没有停止或干扰任何进程。GPU 2 当时仅 14 MiB、0% 利用率，因此被选作最小验证卡。
- 在激活项目环境并把 `CUDA_VISIBLE_DEVICES` 设为 GPU 2 UUID 后：
  - PyTorch `2.4.1+cu121` / CUDA 12.1 识别 1 张 RTX A6000；成功在 CUDA 上创建并读取单元素 tensor。
  - 官方未修改的 `python script/test_render.py` 输出 **`Render Well`**。
- 结论：fvl05 上迁移后的 RoboTwin 基础 Python、PyTorch CUDA 和 SAPIEN 官方渲染链已通过最小验收。尚未在 fvl05 重跑数据采集 smoke test，因此不把完整采集链标记为新服务器已验证。

### 2026-08-04：迁移配置收尾验证

- 补充迁移了 `env/conda-meta`、`tools/cuda-12.1/conda-meta` 与 `tools/miniforge3/conda-meta` 中的旧安装前缀；运行相关配置、命令 shebang 和 Conda 元数据中已无 `/bigbig_nfs_share/lijunhui` 引用。
- `micromamba --version` = 2.6.0；`env/bin/pip` shebang 指向新的 `/nfs_share/lijunhui/Robotwin2/env/bin/python3.10`；`tools/miniforge3/_conda` 指向新的工作区内目标。
- 项目激活脚本通过 `sh -n`；激活环境后 `pip check` 输出 `No broken requirements found.`。
- RoboTwin 官方仓库仍为 `main...origin/main` 且工作树干净；本次运行配置修改位于仓库外的 `Robotwin2/config` 和迁移环境中。未 commit、未 push。

### 2026-08-09 23:46 CST：启动 fvl05 迁移环境完整复核与可重建修正

- 用户要求对从 fvl09 直接迁移来的 RoboTwin 2 环境进行完整检查，并明确授权：若有问题或可靠性不足，可删除并重建个人目录内现有 RoboTwin 环境、项目专用 CUDA 等可再生成组件，不影响服务器系统环境和其他用户。
- 新建专项实时记录：`Robotwin2环境配置/环境重新修正检查.md`。本日志同步记录关键里程碑，详细命令、证据与逐步结果写入专项文档。
- 开始前复核：官方 `RoboTwin` 仓库为 `main...origin/main` 且工作树干净；Vault 仓库有本轮之外的既存修改，全部保留，不暂存、不提交、不覆盖。
- 本轮先审计再决定精确重建范围；保留源码、数据集、模型、已有 smoke 配置和产物。所有写入/删除限定在 `/nfs_share/lijunhui`，不使用 `sudo`，不修改系统驱动或共享 CUDA。

### 2026-08-09 23:52 CST：发现大量旧前缀残留，决定干净重建

- fvl05 GPU 与 fvl09 不同；本轮明确不继承 fvl09 的索引、UUID、坏卡或 Vulkan 结论，将按 fvl05 RTX A6000、实时占用和实际运行重新验证。
- 虽然当前 `pip check`、本地 CUDA 12.1 `nvcc` 以及两个环境内补丁表面正常，但精确审计发现：迁移后的 `env`/Miniforge 中至少 1,361 个文件仍嵌有旧根路径，且 6 份实际 embodiment CuRobo 配置全部仍指向 `/bigbig_nfs_share/lijunhui`。
- 结论：手工迁移修补不足以保证 Conda 前缀和完整采集链可靠，采用干净重建，不再继续逐文件打补丁。
- 保留官方 assets、源码、数据、模型和既有 smoke 产物；删除范围将在专项文档中逐项核验并限定为可再生成环境、项目工具链、依赖构建产物与缓存。

### 2026-08-09 23:59 CST：完成删除前保护核验并冻结重建范围

- fvl05 实时盘点仍为 8×RTX A6000 48 GiB、驱动 535.274.02；当时 GPU 0/1 空闲，GPU 2–7 满载。GPU 复测必须临运行前再次检查，无空闲卡就暂停，不影响其他项目。
- 三个保留的官方资产 ZIP 字节数匹配历史记录且均通过完整 CRC；既有 3-episode smoke 全部产物仍在。
- 官方在线 `main` 已于 2026-08 引入 XPolicyLab 和新数据布局。本轮为保护既有代码、配置与数据兼容性，固定本地已验证 commit `c3ddfa8...`，不把环境重建扩大为源码/数据格式升级。
- 已校验保留的 Miniforge 安装器 SHA-256，个人 NFS 空间充足，且用户本人没有活动进程占用目标环境。
- 冻结删除范围：`env`、`tools/miniforge3`、`tools/cuda-12.1`、`cache` 以及 CuRobo 仓库内已预览的编译/字节码产物；源码、assets、数据、模型、配置、日志与校验安装器全部保留。

### 2026-08-10 00:04 CST：旧迁移环境与项目工具链精确删除完成

- 顺序删除 `env`、`tools/miniforge3`、`tools/cuda-12.1`、`cache`，并在干净的 CuRobo 固定源码仓库内仅清理 5 个旧扩展及 `__pycache__`。
- 所有删除正常完成；源码、assets、数据、模型、配置、日志、Miniforge 校验安装器及既有 smoke 产物均保留，主仓库仍干净。
- 下一阶段从零安装，不再复用任何迁移来的 Conda/Python/CUDA 前缀或包缓存。

### 2026-08-10 00:12 CST：Miniforge 合规断点续装成功

- 官方自解压安装器硬编码忽略 `CONDARC`、创建 `~/.conda` 并强制登记环境；两次均在该边界处停止，没有写入 home 或系统。
- 未改动已校验安装器/payload；从准确断点以 `CONDA_REGISTER_ENVS=false` 执行同一固定 base transaction。沙箱代理失败后在获准联网上下文重试，89 个包链接成功；随后完成 post-install 解包与中间文件清理，未运行 `conda init`。
- 验证：Conda 26.3.2、Mamba 2.6.0、base Python 3.13.13；前缀均在 `Robotwin2/tools/miniforge3`；无 fvl09 旧根路径，且 `/home/lijunhui/.conda` 不存在。
- `config/condarc` 新增 `register_envs: false`，后续 Conda 环境也不登记到 home。

### 2026-08-10 00:17 CST：Python 3.10 基础前缀创建成功

- 在 `Robotwin2/env` 从零安装 165 个 conda-forge 包；Python 3.10.20、pip 26.2.1、CMake 4.4.2、Ninja 1.13.2、ffmpeg 8.1.2、UnZip 6.00 均验证可执行，且无 fvl09 旧根路径。
- Mamba 2.6.0 忽略 `register_envs: false`，新建了只含本轮前缀的 `/home/lijunhui/.conda/environments.txt`；已精确删除该本轮残留。后续 CUDA 前缀改用 Conda CLI 创建。

### 2026-08-10 00:26 CST：个人 CUDA 12.1.1 工具链重建成功

- 从 NVIDIA 固定 `cuda-12.1.1` channel 在 `Robotwin2/tools/cuda-12.1` 从零安装 64 个用户态 Toolkit 包；未安装驱动，未改系统或共享 CUDA。
- 验证 `nvcc` 为 CUDA 12.1 / V12.1.105，编译头和主要开发库齐全；激活脚本将 Python、pip、CUDA、缓存与临时目录全部指向 `Robotwin2`，目标架构为 RTX A6000 对应的 `8.6`。
- 新 CUDA 元数据无 fvl09 旧根路径。Conda 生成的空 `~/.conda/environments.txt` 已在确认无既有状态后精确清理，最终 `~/.conda` 不存在。
- 下一阶段安装 Python 依赖并从固定源码重编译 CuRobo 与 PyTorch3D。

### 2026-08-10 00:45 CST：基础 Python requirements 安装完成，首轮导入发现兼容项

- `script/requirements.txt` 全部安装完成；核心版本为 torch 2.4.1、torchvision 0.19.1、SAPIEN 3.0.0b1、MPLib 0.2.1、NumPy 1.26.4、SciPy 1.10.1、Open3D 0.18.0、Zarr 2.18.3，且 `pip check` 无依赖冲突。
- 首轮导入 `sapien` 失败于缺少 `pkg_resources`，定位为 Setuptools 84.0.0 与旧版 SAPIEN 的兼容问题；仓库官方安装脚本已明确要求 Setuptools 69.5.1，下一步按该固定版本修复后复测。
- 已核对 SAPIEN 与 MPLib 待应用补丁的原始代码上下文均与上游说明一致，尚未提前修改。

### 2026-08-10 00:54 CST：核心导入与两处环境内补丁验证通过

- 默认沙箱内固定 Setuptools 的首次联网命令被本机代理隔离拦截，无变更；在已授权项目联网范围重试后，Setuptools 84.0.0 成功替换为上游固定的 69.5.1。
- `pip check` 无冲突，torch 2.4.1+cu121、torchvision 0.19.1+cu121、SAPIEN、MPLib、Open3D 等完整核心导入通过。沙箱中的 CUDA false 仅反映设备未直通，不作为宿主 GPU 结论。
- 已用 `apply_patch` 修改隔离环境：SAPIEN 的 URDF/SRDF 读取增加 UTF-8，MPLib screw plan 删除 `or collide`；`py_compile`、导入与源码上下文复核均通过。
- 核对确认原有 `urdf_file[:-4] + "srdf"` 已生成正确的单点 `.srdf` 路径，官方实际命令不修改它；未照搬脚本注释中会导致双点路径的错误写法。
- 组合验证命令最后的只读 `rg` 因 shell 尾部引号错误未执行；Python 验证已完成，剩余上下文检查随后独立重跑通过，无状态损坏。

### 2026-08-10 00:58 CST：CuRobo 依赖完成，首次构建停在 NFS Git 安全边界

- 安装并固定 warp-lang 1.12.0、scikit-image 0.21.0、SciPy 1.10.1、Setuptools 69.5.1 及其余 CuRobo 依赖；预检确认个人 CUDA 12.1.105、sm_86 与 GCC 11.4.0 组合。
- 从干净 `envs/curobo` editable 构建时，Setuptools-SCM 子进程触发 NFS `dubious ownership`，在元数据阶段退出，未进入 CUDA 编译；源码和环境未损坏。
- CuRobo 仍为干净 commit `d64c4b005459db10c5dd867d8b30a87d5bda9bdb` / v0.7.8。不会放宽 Git 安全检查；改从该 commit 导出无 `.git` 快照，构建固定版本 wheel 后安装。

### 2026-08-10 01:06 CST：CuRobo v0.7.8 / sm_86 编译安装成功

- 从固定 commit 的无 Git 快照使用个人 CUDA 12.1、sm_86、最多 8 个并行任务构建并安装 53,854,123-byte wheel；构建 SHA-256 `113c2e702b6d2b457496c4656d187526bf1c3fee3c8188b850052260aadf82ed`。
- 五个 CUDA 扩展全部存在，`cuobjdump` 明确显示代表性扩展包含 sm_86 cubin。
- 直接先加载底层扩展曾报 `libc10.so` 未预载；按实际顺序先导入 torch 后，五个扩展全部加载成功，说明构建和链接有效。`pip check` 无冲突，两个源码仓库仍干净。

### 2026-08-10 01:13 CST：PyTorch3D 0.7.8 / sm_86 重编译验证成功

- 安装固定 iopath 0.1.10 / portalocker 3.2.0；从 commit `75ebeeaea0908c5527e7b1e305fbc7681382db47` 新导出无 Git 快照，不复用迁移构建物。
- 通过个人 CUDA 12.1、CUB、sm_86 和 8 路并行构建安装 3,950,721-byte wheel；构建 SHA-256 `2526219d67c066ec72da6a078f4e07c3fcc64bee6f22400966ad0bd749b6e793`，`cuobjdump` 确认 `_C` 含 sm_86 cubin。
- 从源码目录做首次导入时被当前目录同名源码遮蔽，未加载到环境 `_C`；切到 RoboTwin 实际工作目录后，`pytorch3d._C`、CPU KNN 数值测试和 Meshes 结构测试全部通过。`pip check` 无冲突，源码仓库干净。

### 2026-08-10 01:14 CST：embodiment 生成配置完成 fvl05 路径迁移

- 审计后运行官方路径生成脚本，ARX-X5、aloha 左/右、franka、piper、ur5-wsg 共六份配置全部重新生成。
- 独立比对确认生成内容等于模板替换结果，12 个绝对资源路径全部存在，旧 `/bigbig_nfs_share/lijunhui` 引用清零；主仓库仍干净。

### 2026-08-10 01:18 CST：新环境路径纯净性全扫描通过

- 对约 9 GB 的 Python、Miniforge、个人 CUDA、配置与 embodiment 文件做二进制文本扫描，旧 fvl09 根路径命中为 0；运行前缀无坏软链接、旧目标或错误 shebang。
- Miniforge 下载包缓存内有 4 个包自身的相对链接未闭合，但不在运行前缀、无旧根且不影响命令；未误改缓存内容。
- 激活后 Python/pip/nvcc、CUDA_HOME、sm_86、临时目录与各缓存全部定位在 `Robotwin2`，共享 CUDA PATH 被排除，LD_LIBRARY_PATH unset，`~/.conda` 不存在。
- `/home/conda/feedstock_root` 只出现在 conda-forge 构建 provenance，不是本机路径；两个新编译 wheel 的 provenance 位于本项目 tmp 快照。

### 2026-08-10 01:38 CST：fvl05 宿主 CUDA、任务导入与官方渲染通过

- 685 个第一方 Python 文件语法编译通过；DexVLA 可选代码有一处非阻断 SyntaxWarning。7 份 task YAML、5 个 embodiment registry 目标和三棵资产树检查通过。
- 文件沙箱中的任务导入因 CuRobo 模块定义阶段需要 CUDA 而失败，符合设备不直通边界；移到宿主 GPU 验证，不误记为环境失败。
- 23:59 时 GPU 2–7 满载，未触碰；01:37:30 重新检查时 8 张卡均为 12–15 MiB 基线、0%（GPU 0 瞬时 1%）、P8，compute-app 列表为空。使用当时空闲的 fvl05 GPU 2 UUID `GPU-4306d28e-0eeb-2e26-bda4-b1b44058f63e`。
- torch 2.4.1+cu121 成功识别 RTX A6000 并完成 CUDA tensor 求和 1024.0；CuroboPlanner 与 50 个 task 模块全部导入/构造成功。
- 每一步退出后都复核 GPU 2 回到 14 MiB、0%、P8、无 compute process。官方 `script/test_render.py` 在约 6 秒内输出 `Render Well`；只有 SAPIEN 弃用警告。
- 驱动、PyTorch、CuRobo、task import 和 SAPIEN 光追渲染链已在 fvl05 实机通过；下一步为独立一集数据采集 smoke。

### 2026-08-10 01:45 CST：独立 fvl05 一集端到端采集 smoke 通过

- 新建忽略型 `demo_clean_fvl05_recheck.yml`，1 集 clean aloha 配置，输出到全新 `data/beat_block_hammer/demo_clean_fvl05_recheck/`，未覆盖历史 smoke。指令生成链审计确认只用本地文件，不访问云端。
- 长测试使用从早期到运行前都保持空闲的 GPU 1 UUID `GPU-414c52ba-72c6-fc45-95d6-1e9750bbc21b`；运行期间该卡唯一 PID 为本次 collect_data。后来出现在 GPU 3 的其他任务完全未触碰。
- seed 0 规划失败一次、seed 1 成功，属于正常随机重试；随后完整采集 1510 帧并正常退出，生成 HDF5、H.264 MP4、左右轨迹、scene info、seed 和 seen/unseen 各 100 条指令。GPU 1 退出后回到 14 MiB、0%、P8。
- 未激活 shell 的 ffprobe 曾命中共享 CUDA 12.2 坏 libOpenCL；激活项目后视频验证为 320×240、30 FPS、1510 帧、50.33 秒。说明运行入口必须是项目激活脚本。
- 内容验收确认 4 路相机首尾 JPEG 可解码、相机矩阵有限、14 维动作拼接精确、左右 7 维 endpose 有效、轨迹/scene/seed/指令完整。首版验收脚本因 h5py None indexing 写法失败，改为 NumPy 扩维后全套通过，产物无误。
- SHA-256：HDF5 `c91b1983...cf192`；MP4 `4e073466...b4b2`；PKL `4f14f304...2b08`；instructions `fa50d97a...9775`。
- fvl05 从零重建环境的规划、仿真、渲染、采样与存储完整 pipeline 已实机验证成功。

### 2026-08-10 01:49 CST：最终复核完成，fvl05 基础环境正式验收通过

- 激活路径、个人 CUDA 12.1、sm_86、缓存/临时目录、核心包版本、动态扩展加载及 `pip check` 最终复核均通过；三个固定源码仓库保持干净，历史 3 集 smoke 与本轮 1 集 fvl05 recheck 产物均完整保留。
- GPU 状态按时间点记录：23:59 GPU 2–7 忙；01:37:30 八卡曾全部回到基线，因而只在即时复核空闲的 GPU 2/1 上完成短测和长测；01:48:45 GPU 3 又出现 PID `3861183`、约 7.5 GiB 占用，说明 GPU 空闲不能跨时间推断。本轮没有停止、占用或影响该任务，GPU 1 已回到 14 MiB/P8 基线。
- 长期 workspace memory 已补充本轮固定版本、源码 commit、安装陷阱、fvl05 smoke 路径和“基础 simulator 已端到端可用”的验证边界。
- 最终结论：RoboTwin 2 基础环境已在 fvl05 完成干净重建和实际端到端验收，可通过唯一入口 `. /nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh` 使用。上游 XPolicyLab 迁移、大规模采集、训练和 policy 专用环境均为后续独立工作；本轮未执行 Git commit 或 push。

### 2026-08-10 01:50 CST：GPU 快照时效性补充

- 01:49:48 再查时，前一分钟占用 GPU 3 的 PID `3861183` 已结束；八卡均为 14–15 MiB、0%、无 compute process，GPU 3–7 的 P-state 暂未从 P0 回落。这不是长期空闲承诺，只证明该查询瞬间没有计算进程；后续仍必须临启动前复查。

### 2026-08-10 01:54 CST：fvl05 环境操作手册与长期记忆完成

- 新建 `Robotwin2环境配置/RoboTwin2环境操作手册.md`，系统记录当前验收边界、目录与固定版本、唯一激活方式、无 GPU 健康检查、实时 GPU 选择、CUDA/官方渲染验证、独立配置与数据采集、续跑语义、HDF5/视频/轨迹/指令结构、结果检查、常见故障和维护规则。
- 手册明确保护 `demo_clean_smoke` 与 `demo_clean_fvl05_recheck`，要求不同实验使用独立配置名和输出目录，并记录当前 `collect_data.sh` 静默调用缺失 `.update_path.sh` 的源码细节及经过实测的直接 Python 入口。
- `/nfs_share/lijunhui/AGENTS.md` 已同步手册的规范路径、维护要求和上述固定 commit 入口细节。此次只编写文档和长期记忆，没有再次启动 GPU、修改基础环境、执行 Git commit 或 push。

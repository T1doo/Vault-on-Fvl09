# RoboTwin 2 环境配置实时日志

> 项目根目录：`/bigbig_nfs_share/lijunhui/Robotwin2`  
> 研究笔记目录：`/bigbig_nfs_share/lijunhui/Vault-on-Fvl09/Robotwin2环境配置`  
> 日志原则：按时间追加，真实记录命令、结果、失败、决策和文件变更，不事后美化历史。

## 当前状态

- 阶段：基础环境基本完成，等待包内补丁确认与系统 GPU/Vulkan 修复
- 基础环境：已创建，Python 3.10.20
- 官方代码：已克隆，RoboTwin commit `c3ddfa8b97d5519efa828b075999bd0006778e5e`
- Python/Conda 依赖：官方 requirements 已安装，`pip check` 通过
- 本地 CUDA：12.1.1，位于 `tools/cuda-12.1`，未使用共享 CUDA Toolkit
- CuRobo：v0.7.8 已使用本地 CUDA 编译安装，五个扩展可加载
- PyTorch3D：0.7.8 已使用本地 CUDA 编译安装，`pytorch3d._C` 可加载
- RoboTwin 资产：三个官方 ZIP 已下载、校验、解压并完成 embodiment 路径生成
- 仿真验证：纯 PhysX CPU 碰撞场景通过；渲染失败
- 策略训练环境：尚未规划到具体策略
- 当前系统阻塞：NVIDIA 驱动/NVML 不可用，Vulkan 只识别 CPU llvmpipe
- 待确认动作：按官方脚本修改隔离环境内的 SAPIEN 与 MPLib 文件

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

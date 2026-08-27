# RoboTwin 2 环境操作手册（fvl05）

> 适用服务器：fvl05  
> 环境根目录：/nfs_share/lijunhui/Robotwin2  
> 当前状态：基础 simulator 已完成端到端验收，可正常使用  
> 最后核对：2026-08-10  
> 适用源码：RoboTwin commit c3ddfa8b97d5519efa828b075999bd0006778e5e

本文是已经配好的 RoboTwin 2 环境的日常操作手册。它说明如何进入环境、选择空闲 GPU、做健康检查、运行渲染和数据采集、理解输出文件，以及遇到常见问题时如何判断。

本手册描述的是当前 fvl05 上已经实际验证过的版本，不等同于 RoboTwin 在线仓库最新 main。完整重建过程、失败记录和校验依据见 [环境重新修正检查](./环境重新修正检查.md)，项目历次配置时间线见 [RoboTwin2环境配置实时日志](./RoboTwin2环境配置实时日志.md)。

## 1. 当前环境到底验证到了什么程度

2026-08-10 在 fvl05 上完成了以下实际验证：

- 迁移自 fvl09、含旧绝对路径的 Conda/Python/CUDA 前缀已删除并从零重建。
- 约 9 GB 的新环境与配置中，旧根路径 /bigbig_nfs_share/lijunhui 命中为 0。
- Python 依赖完整，python -m pip check 无冲突。
- PyTorch 能在 fvl05 RTX A6000 上创建 CUDA tensor。
- CuRobo 与 PyTorch3D 的 CUDA 扩展已用个人 CUDA 12.1 重新编译，目标架构为 sm_86。
- 50 个 RoboTwin task 类全部可以导入和构造。
- 官方未修改的 script/test_render.py 输出 Render Well。
- beat_block_hammer 完成了一集真实端到端采集：规划、仿真、四相机渲染、动作与末端位姿、HDF5、视频、轨迹和指令均生成并通过内容校验。

因此，“基础 simulator 可用”已经被实机验证。下面这些内容尚不能由本轮验收自动推出：

- 每一个任务、每一种 embodiment 都已经完成长时间采集；
- 大规模或多任务数据生产已经压测；
- DP、ACT、RDT、PI0、DexVLA 等 policy 环境已经配置；
- 当前本地源码已经升级到在线最新 XPolicyLab 代码和新数据格式。

这些应作为独立工作分别配置和验证，尤其不要把相互冲突的 policy 依赖直接塞进当前基础环境。

## 2. 目录结构

所有可控内容都集中在 /nfs_share/lijunhui/Robotwin2：

| 路径 | 用途 |
|---|---|
| project/RoboTwin | 当前使用的官方 RoboTwin 源码、assets、任务配置和采集输出 |
| env | 独立 Python/Conda 运行环境 |
| tools/cuda-12.1 | 个人 CUDA 12.1.1 Toolkit，不是服务器共享 CUDA |
| tools/miniforge3 | 项目专用 Miniforge/Conda |
| cache | Conda、pip、PyTorch、Hugging Face、Matplotlib 等缓存 |
| datasets | 预留的数据集目录 |
| models | 模型权重目录 |
| tmp | 编译和运行临时目录 |
| config/activate_robotwin2.sh | 唯一的 RoboTwin 2 激活入口 |

不要在 /nfs_share/lijunhui 根目录另建 RoboTwin 环境、缓存或模型目录，也不要把项目包安装到系统 Python。

## 3. 已固定的主要版本

| 组件 | 当前版本或 commit |
|---|---|
| RoboTwin | c3ddfa8b97d5519efa828b075999bd0006778e5e |
| Python | 3.10.20 |
| Conda | 26.3.2 |
| Mamba | 2.6.0 |
| CUDA Toolkit | 12.1.1 |
| nvcc | 12.1.105 |
| PyTorch | 2.4.1+cu121 |
| TorchVision | 0.19.1+cu121 |
| SAPIEN | 3.0.0b1 |
| MPLib | 0.2.1 |
| CuRobo | 0.7.8，commit d64c4b005459db10c5dd867d8b30a87d5bda9bdb |
| PyTorch3D | 0.7.8，commit 75ebeeaea0908c5527e7b1e305fbc7681382db47 |
| Open3D | 0.18.0 |
| NumPy | 1.26.4 |
| SciPy | 1.10.1 |
| Setuptools | 69.5.1 |

Setuptools 69.5.1 是有意固定的：SAPIEN 3.0.0b1 仍依赖 pkg_resources。不要顺手把它升级到当前最新版。

## 4. 每次使用时的标准进入方式

打开一个新 shell 后执行：

    cd /nfs_share/lijunhui/Robotwin2/project/RoboTwin
    . /nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh

第二行最前面是英文句点加空格，等价于 source。必须把脚本加载到当前 shell；直接执行脚本不会让父 shell 保留环境变量。

不要使用工作区级的 /nfs_share/lijunhui/activate.sh 代替项目激活脚本。前者是 Git/GitHub 等工作区工具入口，不是 RoboTwin 2 环境入口。

激活脚本会完成这些事情：

- 把 Python 指向 /nfs_share/lijunhui/Robotwin2/env；
- 把 CUDA_HOME 和 nvcc 指向个人 tools/cuda-12.1；
- 设置 TORCH_CUDA_ARCH_LIST=8.6；
- 把 Conda、pip、torch、Hugging Face、Matplotlib 和临时文件定位到 Robotwin2 内；
- 清除继承来的 LD_LIBRARY_PATH；
- 从 PATH 中过滤 /share/apps/cuda 和 /usr/local/cuda；
- 保留调用者已经显式设置的 CUDA_VISIBLE_DEVICES，但不会自动替用户选 GPU。

激活后建议先确认：

    command -v python
    command -v pip
    command -v nvcc
    python -V
    nvcc --version
    printf 'ROBOTWIN_ROOT=%s\nCUDA_HOME=%s\nTORCH_CUDA_ARCH_LIST=%s\n' \
      "$ROBOTWIN_ROOT" "$CUDA_HOME" "$TORCH_CUDA_ARCH_LIST"

正确结果的路径前缀应分别是：

- /nfs_share/lijunhui/Robotwin2/env/bin
- /nfs_share/lijunhui/Robotwin2/tools/cuda-12.1/bin

这个项目的“激活”主要是当前 shell 的环境变量和 PATH 设置，并不是 conda activate。结束使用时最干净的做法是关闭该 shell 或另开一个新 shell，不要依赖 conda deactivate 还原全部变量。

## 5. 不占 GPU 的基础健康检查

以下检查不会主动使用 GPU：

    cd /nfs_share/lijunhui/Robotwin2/project/RoboTwin
    . /nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh
    sh -n /nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh
    python -m pip check
    CUDA_VISIBLE_DEVICES='' python -c \
      'import torch, sapien, mplib, curobo, pytorch3d; from pytorch3d import _C; print(torch.__version__, sapien.__version__, mplib.__version__)'

预期：

- pip check 输出 No broken requirements found；
- 最后一条打印 torch 2.4.1+cu121、SAPIEN 3.0.0b1 和 MPLib 0.2.1；
- 不出现旧路径 /bigbig_nfs_share/lijunhui。

CUDA_VISIBLE_DEVICES 为空时 torch.cuda.is_available() 为 false 是预期现象，不能据此判断宿主机 GPU 或驱动损坏。

## 6. GPU 使用规则

fvl05 有 8 张 RTX A6000 48 GiB。GPU 占用会在一分钟内明显变化，因此没有“永久空闲卡”或“固定推荐卡”。每一次 GPU 命令都必须在启动前重新检查。

### 6.1 查看实时状态

    nvidia-smi --query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu,pstate \
      --format=csv,noheader,nounits
    nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory \
      --format=csv,noheader,nounits

选择 GPU 时至少同时看：

- 显存是否接近驱动基线；
- utilization.gpu 是否接近 0；
- compute-app 列表是否为空；
- P-state 是否已经回落；
- 状态是否是在命令启动前刚刚读取的。

0% 利用率不代表一定空闲：一个任务可能暂时没有计算，但仍持有大量显存。P0 也可能是刚结束任务后的短暂状态。因此只看单列是不够的。

绝对不要停止、kill 或挤占不属于自己的进程。不能确定时就不运行长 demo。

### 6.2 选择一张当时空闲的卡

假设刚刚确认物理 GPU 1 空闲：

    export CUDA_VISIBLE_DEVICES=1

设置后，Python 进程内部通常会把这张唯一可见的物理卡编号为 cuda:0，这是 CUDA 的正常重映射。

不要照抄这里的 GPU 1 作为未来默认选择；它只是命令格式示例。

### 6.3 最小 CUDA 验证

只在刚确认空闲的 GPU 上运行：

    python -c \
      'import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0)); x=torch.ones(1024, device="cuda"); print(x.sum().item())'

预期最后输出 1024.0。结束后再次运行 nvidia-smi，确认进程退出且显存释放。

## 7. 官方渲染测试

先激活环境、选择刚确认空闲的 GPU，然后从源码根目录运行：

    cd /nfs_share/lijunhui/Robotwin2/project/RoboTwin
    python script/test_render.py

成功标志：

    Render Well

出现 SAPIEN 旧 API 的 DeprecationWarning 不等于渲染失败；应以进程退出码和 Render Well 为准。

渲染会实际使用 GPU。运行前和运行后都应检查 nvidia-smi。

## 8. 数据采集标准流程

### 8.1 先认识任务名和配置名

采集入口接受两个字符串：

- task_name：envs 下的任务模块名，例如 beat_block_hammer；
- task_config：task_config 下 YAML 文件的文件名，但不带 .yml。

查看当前配置：

    find task_config -maxdepth 1 -type f -name '*.yml' -printf '%f\n' | sort

查看任务模块：

    find envs -maxdepth 1 -type f -name '*.py' -printf '%f\n' | sort

运行命令必须从 /nfs_share/lijunhui/Robotwin2/project/RoboTwin 根目录发出，因为当前源码大量使用相对路径。

### 8.2 为新实验创建独立配置

不要直接修改或复用下面两个已验证输出：

- task_config/demo_clean_smoke.yml：从 fvl09 迁移保留的 3 集历史 smoke；
- task_config/demo_clean_fvl05_recheck.yml：本轮 fvl05 重建后通过验收的 1 集 smoke。

也不要随意用 demo_clean.yml 做小测试，因为它是正式配置，默认采集量更大。

建议从模板或 fvl05 recheck 配置复制，并使用一个从未用过的新名字：

    robotwin_config_name=my_demo_clean_001
    test ! -e "task_config/$robotwin_config_name.yml"
    test ! -e "data/beat_block_hammer/$robotwin_config_name"
    cp task_config/demo_clean_fvl05_recheck.yml \
      "task_config/$robotwin_config_name.yml"

然后编辑新 YAML。改动配置后应使用新的配置名和输出目录；不要把不同配置产生的数据续写进同一目录。

### 8.3 重要 YAML 字段

| 字段 | 含义 |
|---|---|
| episode_num | 目标成功 episode 数；首次 smoke 建议 1 |
| use_seed | false 时先寻找成功 seed；true 时从已有 seed.txt 重放 |
| embodiment | 机器人配置，例如 [aloha-agilex] |
| language_num | seen/unseen 指令生成数量 |
| render_freq | 0 表示无交互 viewer 的采集方式 |
| domain_randomization | 背景、杂物、光照、相机距离、桌高等随机化 |
| camera | 是否采集头部和腕部相机、相机类型 |
| data_type.rgb | 是否保存 RGB |
| data_type.depth | 是否保存深度 |
| data_type.pointcloud | 是否保存点云 |
| data_type.endpose | 是否保存左右末端位姿 |
| data_type.qpos | 是否保存关节动作 |
| save_path | 基础输出路径；当前通常为 ./data |
| clear_cache_freq | 清理渲染缓存频率 |
| collect_data | 是否在成功 seed 后实际回放并写数据 |
| eval_video_log | 是否写评估视频 |

新增 depth、pointcloud、分割或更高采集量会显著增加时间、显存和磁盘使用，应先做一集小测。

### 8.4 推荐的、已经实际验收过的运行入口

先实时选择空闲 GPU并设置 CUDA_VISIBLE_DEVICES，然后直接运行 Python：

    export CUDA_VISIBLE_DEVICES=1
    python script/collect_data.py beat_block_hammer my_demo_clean_001

对于仅用于健康检查的一集 smoke，可以在外层加合理超时：

    timeout 1200 python script/collect_data.py \
      beat_block_hammer my_demo_clean_001

正式长采集不应机械套用 20 分钟超时；应按任务和集数估算。

当前源码也提供官方包装脚本：

    bash collect_data.sh beat_block_hammer my_demo_clean_001 1

第三个参数会直接覆盖 CUDA_VISIBLE_DEVICES。包装脚本最后只清理该任务/配置目录中的 .cache。

当前固定 commit 的 collect_data.sh 仍尝试调用已经不存在的 script/.update_path.sh，并把该错误输出隐藏；因为 embodiment 路径已经由实际存在的 script/update_embodiment_config_path.py 正确生成，所以本轮不受影响。日常操作优先使用上面经过实际验收的 Python 入口。若项目根路径以后再次移动，应从源码根目录显式运行：

    python script/update_embodiment_config_path.py

运行后必须检查生成配置里的绝对路径，不能仅相信脚本成功提示。

### 8.5 seed 搜索失败是否正常

use_seed 为 false 时，程序先尝试不同 seed，只有规划和任务成功才记入 seed.txt。因此偶尔看到某个 seed 的 simulate data fail 并不表示环境坏了。

本轮 fvl05 smoke 中 seed 0 失败、seed 1 成功，随后完整采集正常完成。如果大量 seed 连续失败、出现相同异常堆栈或始终无法写出成功 seed，才应停止并检查任务配置、资产、规划器和 GPU 状态。

### 8.6 新采集和续跑的区别

程序发现已有 seed.txt 时会读取已有成功 seed，并从后续 seed 继续；发现已有 episodeN.hdf5 时会从第一个缺失的 episode 序号继续。

因此：

- 同一配置、同一任务的意外中断可以谨慎续跑；
- 修改过 YAML、代码、资产或 embodiment 后不要在旧输出目录续跑；
- 不确定输出目录来源时，使用新的 task_config 名；
- 续跑前先备份或核对 seed.txt、_traj_data、data、scene_info.json；
- 不要删除已经验收的 demo_clean_smoke 或 demo_clean_fvl05_recheck。

## 9. 采集产物在哪里

当 YAML 中 save_path 为 ./data 时，实际输出目录为：

    data/<task_name>/<task_config>/

本轮 fvl05 验收产物位于：

    data/beat_block_hammer/demo_clean_fvl05_recheck/

典型结构：

    seed.txt
    scene_info.json
    _traj_data/episode0.pkl
    data/episode0.hdf5
    video/episode0.mp4
    instructions/episode0.json

各文件含义：

- seed.txt：成功规划并用于回放的 seed；
- scene_info.json：每集对象、使用手臂等场景信息；
- _traj_data/episodeN.pkl：每次规划得到的左右关节轨迹段；
- data/episodeN.hdf5：相机、动作、末端位姿等逐帧数据；
- video/episodeN.mp4：可视化视频；
- instructions/episodeN.json：seen 和 unseen 指令列表。

本轮 1 集样例为 1510 帧。HDF5 中已验证的主要结构：

| 数据集 | 样例形状 | 说明 |
|---|---:|---|
| joint_action/vector | 1510 × 14 | 左 6 轴 + 左夹爪 + 右 6 轴 + 右夹爪 |
| joint_action/left_arm | 1510 × 6 | 左臂关节动作 |
| joint_action/right_arm | 1510 × 6 | 右臂关节动作 |
| endpose/left_endpose | 1510 × 7 | xyz + quaternion |
| endpose/right_endpose | 1510 × 7 | xyz + quaternion |
| observation/*_camera/rgb | 1510 | 每帧是 JPEG 编码字节，不是直接的 H×W×3 数组 |
| observation/*_camera/intrinsic_cv | 1510 × 3 × 3 | 相机内参 |
| observation/*_camera/extrinsic_cv | 1510 × 3 × 4 | 相机外参 |
| observation/*_camera/cam2world_gl | 1510 × 4 × 4 | camera-to-world |
| pointcloud | 1510 × 0 | 当前 smoke 关闭点云，因此为空 |

该 commit 的 HDF5 没有 step_name 或逐帧语义标签。不要在下游代码里假定这些字段存在。

## 10. 快速检查采集结果

列出文件与大小：

    find "data/beat_block_hammer/my_demo_clean_001" \
      -maxdepth 3 -type f -printf '%P\t%s bytes\n' | sort

查看视频信息时要先激活项目环境，避免未激活 shell 命中服务器共享 CUDA/OpenCL：

    ffprobe -v error -select_streams v:0 \
      -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames \
      -of default=noprint_wrappers=1 \
      data/beat_block_hammer/my_demo_clean_001/video/episode0.mp4

用 Python 查看 HDF5 数据集：

    python - <<'PY'
    import h5py

    path = "data/beat_block_hammer/my_demo_clean_001/data/episode0.hdf5"
    with h5py.File(path, "r") as f:
        def show(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(name, obj.shape, obj.dtype)
        f.visititems(show)
    PY

至少确认：

- episode 数量符合预期；
- HDF5、MP4、PKL、JSON 和 seed.txt 均存在；
- 四相机帧数与动作/endpose 帧数一致；
- 视频能解码；
- 指令 JSON 不再包含未替换占位符；
- 进程退出后目标 GPU 的显存已释放。

## 11. 常见问题

### 11.1 python、pip 或 nvcc 指向错误位置

现象：command -v 输出 /usr、/home 或 /share/apps/cuda。

处理：

    cd /nfs_share/lijunhui/Robotwin2/project/RoboTwin
    . /nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh
    command -v python
    command -v nvcc

在路径仍不正确前不要安装包或编译。

### 11.2 torch.cuda.is_available() 为 false

依次检查：

- 当前执行上下文是否暴露 GPU；
- CUDA_VISIBLE_DEVICES 是否被设为空或指向错误设备；
- nvidia-smi 是否可用；
- 是否确实加载了项目激活脚本；
- 是否从另一个不带设备的沙箱或作业环境运行。

默认文件沙箱看不到 GPU 时，false 是上下文限制，不是环境损坏证据。

### 11.3 ffprobe 或其他命令报共享 libOpenCL / CUDA 错误

通常是没有加载项目激活脚本，shell 继承了共享 CUDA 12.2 的 LD_LIBRARY_PATH。重新打开 shell并加载唯一激活入口，再检查：

    printf '%s\n' "$LD_LIBRARY_PATH"
    command -v ffprobe

项目激活后 LD_LIBRARY_PATH 应为空，ffprobe 应来自项目 Python/Conda 前缀。

### 11.4 SAPIEN 报缺少 pkg_resources

检查 Setuptools：

    python -c 'import setuptools; print(setuptools.__version__)'

应为 69.5.1。不要直接升级 Setuptools；如果已经被改动，应先记录变化并按本轮日志恢复固定版本。

### 11.5 CuRobo 底层扩展直接加载时报 libc10.so 不存在

对 PyTorch C++/CUDA 扩展做底层检查时应先 import torch，让 PyTorch 动态库进入进程：

    python -c 'import torch; import curobo; print("CuRobo import OK")'

这与 RoboTwin 正常入口的加载顺序一致。

### 11.6 资产路径仍指向 fvl09

从源码根目录运行：

    python script/update_embodiment_config_path.py

然后搜索旧路径：

    rg -n '/bigbig_nfs_share/lijunhui' assets/embodiments

正常应无输出。若项目并未移动，不要无故重复改写生成配置。

### 11.7 collect_data.sh 看起来没执行路径更新

这是当前固定源码的已知细节：脚本调用的 script/.update_path.sh 不存在且错误被重定向。当前六份 embodiment 配置已经正确生成；优先用 python script/collect_data.py。若路径确实迁移，显式运行实际存在的 update_embodiment_config_path.py。

### 11.8 某个 seed 规划失败

少量随机 seed 失败是设计允许的，程序会继续尝试。先看是否随后找到成功 seed。只有持续失败、重复异常或 GPU/资产错误才需要中止排查。

### 11.9 GPU 显示 0%，但显存很高

仍视为正在被占用，不要使用。结合 compute-app、显存、P-state 和连续两次即时检查判断。

## 12. 安装包和维护环境时的规则

- 永远先确认 command -v python 指向 Robotwin2/env。
- 使用 python -m pip，而不是裸 pip 或系统 pip。
- 不使用 sudo、apt、yum 或系统级 pip。
- 不使用 /share/apps/cuda 或 /usr/local/cuda 编译 RoboTwin 扩展。
- 不盲跑上游 script/_install.sh；先审计其下载、系统写入、源码修改和未固定版本。
- 不盲跑 Miniforge 安装器。当前安装器会尝试创建 ~/.conda 并登记环境；Mamba 也曾忽略 register_envs: false。
- 修改依赖后立即运行 python -m pip check、核心导入、渲染测试和最小采集；仅 pip check 通过不足以证明 simulator 可用。
- CuRobo 或 PyTorch3D 需要重编译时，必须使用个人 CUDA 12.1 和 TORCH_CUDA_ARCH_LIST=8.6。
- policy 专用依赖使用独立环境，不污染当前基础 simulator。
- 源码升级到新的 XPolicyLab/main 应作为源码、子模块、配置和数据格式迁移处理，不是简单 git pull。
- 配置、验证、失败和修复应继续追加到实时日志，不要改写过去的历史记录。
- 笔记编辑不代表允许 Git commit 或 push；需要用户单独明确要求。

## 13. 已验证产物与保护边界

历史 fvl09 smoke：

    /nfs_share/lijunhui/Robotwin2/project/RoboTwin/data/beat_block_hammer/demo_clean_smoke/

本轮 fvl05 smoke：

    /nfs_share/lijunhui/Robotwin2/project/RoboTwin/data/beat_block_hammer/demo_clean_fvl05_recheck/

这两份都是环境迁移与验收的重要证据。不要删除、覆盖或把 smoke 配置替换成正式 demo_clean.yml，除非用户明确要求。

本轮 fvl05 产物的完整 SHA-256、逐字段验收和 GPU 时间线记录在 [环境重新修正检查](./环境重新修正检查.md)。

## 14. 日常最短流程

每次日常运行可以按下面的顺序：

1. 进入 RoboTwin 源码根目录。
2. 加载 config/activate_robotwin2.sh。
3. 确认 python、nvcc 和 CUDA_HOME 路径。
4. 实时查看 GPU 显存、利用率、P-state 和计算进程。
5. 只选择刚确认空闲的 GPU，并设置 CUDA_VISIBLE_DEVICES。
6. 新任务先运行 script/test_render.py。
7. 新配置先做 1 集、独立配置名和独立输出目录的 smoke。
8. 检查 HDF5、视频、轨迹、指令、帧数和 GPU 释放情况。
9. smoke 通过后再扩大 episode_num 或开启更多数据类型。
10. 把重要配置、命令、结果和失败追加到实时日志。

最关键的三条是：只用唯一激活脚本；GPU 每次临启动前重查；不同实验使用不同配置名和输出目录。

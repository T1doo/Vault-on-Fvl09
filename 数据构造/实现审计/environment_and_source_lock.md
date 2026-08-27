# F1–F4 环境与源码锁

生成时间：2026-08-27T11:26:06+08:00

用途：`implementation_audit`

正式数据：否

Stage 0 数据：否

## 结论

```yaml
source_lock_match: true
source_worktree_clean: true
cpu_environment_check: passed
gpu0_live_status: busy_external_jobs
gpu_runtime_probe_this_session: not_run_gpu0_busy
environment_reinstall_required: false
stage0_readiness: blocked_pending_code_asset_mapping_and_pilot_budget
```

服务器上的 RoboTwin2 官方 baseline 与 `controlled_multi_future_f1_f4_v1_2` 文档记录的 commit 完全一致，工作树干净。基础 Python/CUDA Toolkit 及核心包的 CPU-only 导入和依赖闭包通过，不需要重新安装环境。物理 fvl05 GPU 0 在本次 live snapshot 中被两个外部计算进程占用，显存 45,696/49,140 MiB、利用率 100%、P2，因此没有启动 CUDA tensor、SAPIEN render、CuRobo planner 或任何其他 GPU child，也没有换用 GPU 1–7。

## RoboTwin2 源码锁

| 字段 | 值 |
|---|---|
| repo path | `/nfs_share/lijunhui/Robotwin2/project/RoboTwin` |
| remote | `origin https://github.com/RoboTwin-Platform/RoboTwin.git` |
| branch | `main` |
| actual commit | `c3ddfa8b97d5519efa828b075999bd0006778e5e` |
| expected commit | `c3ddfa8b97d5519efa828b075999bd0006778e5e` |
| source lock match | `true` |
| Git tree | `9999c16155e733b62e85c105e4bc3b00c8510af6` |
| `git status --short` | empty |
| dirty entry count | `0` |

关键 tracked 文件 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `script/requirements.txt` | `6067cd88e56d302ec2811924efab48a7c5d7d66cf17d5a91cb22d88a86edb05d` |
| `script/test_render.py` | `4426c0e313e51995d28858bc2c264ba01ce28fcc56275a56e9efff682f2f84f8` |
| `script/collect_data.py` | `e51d8dca1afd843206187a72537dc467d1db07bd1c860055ad59e47b181c81ab` |
| `envs/_base_task.py` | `448f7152b65cb9102217cf5463aa821d72810ca56f63d5a797ec7bd43e23e101` |
| `envs/utils/create_actor.py` | `6bababee8e70da2460b2bbf47d3b5fbb20ccf73368782a7be596a63c962dce6d` |

## 规范文档锁

| 文件 | SHA-256 | 当前标识 |
|---|---|---|
| `Vault-on-Fvl09/Idea/项目核心Idea.md` | `1214c97c234d0e990137d9761b6c9ec088b1ecade73210cd0e6a49375ac3eb18` | canonical |
| `Vault-on-Fvl09/数据构造/数据构造方案.md` | `b59e469e9a7975eef24d0d4b50127ecdb66f3e6578effdedd4269ff41476d0d6` | `controlled_multi_future_f1_f4_v1_2` / `merged_master_v1` |

旧 Mouse 实现位于 `/nfs_share/lijunhui/Robotwin2/archive/mouse_three_destination_mvp_20260810_20260820/`，不在当前 worktree，也不作为本轮 F1–F4 source lock 的实现输入。

## Python、CUDA 与核心依赖

| 字段 | 值 |
|---|---|
| activation entry | `. /nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh` |
| Python executable | `/nfs_share/lijunhui/Robotwin2/env/bin/python` |
| environment form | isolated prefix；未依赖 shell `CONDA_PREFIX`/`VIRTUAL_ENV` |
| Python | `3.10.20` |
| PyTorch | `2.4.1+cu121` |
| Torch CUDA build | `12.1` |
| TorchVision | `0.19.1+cu121` |
| CUDA Toolkit | `12.1.105` |
| `CUDA_HOME` | `/nfs_share/lijunhui/Robotwin2/tools/cuda-12.1` |
| `TORCH_CUDA_ARCH_LIST` | `8.6` |
| `LD_LIBRARY_PATH` after activation | unset |
| SAPIEN | `3.0.0b1` |
| MPLib | `0.2.1` |
| nvidia-curobo | `0.7.8` |
| PyTorch3D | `0.7.8` |
| NumPy / SciPy / h5py | `1.26.4` / `1.10.1` / `3.16.0` |
| `pip check` | passed: `No broken requirements found.` |

Dependency source commits：

- CuRobo：`d64c4b005459db10c5dd867d8b30a87d5bda9bdb`，worktree clean；
- PyTorch3D：`75ebeeaea0908c5527e7b1e305fbc7681382db47`，worktree clean。

Activation/config hashes：

| 文件 | SHA-256 |
|---|---|
| `Robotwin2/config/activate_robotwin2.sh` | `3a70daeafb49f161d1ad571e5de6d4455060ab56fdc1838ff2c540cff9b0feea` |
| `Robotwin2/config/condarc` | `2599b9f3786781145cc38b2facceddbdafb6e861b00dd59756b93a619d7d1e50` |
| `Robotwin2/config/pip.conf` | `834d74731288610e79f837a03d10d3180257bc84f0a3b303a4ccfb9304e392f1` |

## GPU live 状态

主机：`fvl05`；kernel：`Linux 5.15.0-43-generic x86_64`；NVIDIA driver：`535.274.02`；设备为 8 × RTX A6000 49,140 MiB。

本项目被限定为物理 GPU 0：

```yaml
physical_index: 0
uuid: GPU-2c620e6c-9639-2022-b573-9847dfa33769
memory_used_mib: 45696
memory_total_mib: 49140
utilization_percent: 100
pstate: P2
external_compute_process_count: 2
idle: false
decision: no_gpu_probe_launched
```

首次在默认文件沙箱中运行 `nvidia-smi` 因设备未直通而返回 driver communication error；随后在获准的宿主只读上下文取得上述 live snapshot。该差异是执行上下文可见性，不是驱动故障。

## RoboTwin2 路径

| 项目 | 路径／状态 |
|---|---|
| official env modules | `/nfs_share/lijunhui/Robotwin2/project/RoboTwin/envs`；53 个顶层 Python env 文件 |
| official task config root | `/nfs_share/lijunhui/Robotwin2/project/RoboTwin/task_config` |
| config template | `task_config/_config_template.yml` |
| clean config | `task_config/demo_clean.yml` |
| assets root | `/nfs_share/lijunhui/Robotwin2/project/RoboTwin/assets` |
| object model families | `assets/objects`；125 个顶层目录 |
| embodiments | `assets/embodiments` |
| background textures | `assets/background_texture` |

CPU-only import 已验证 `torch`、`torchvision`、`sapien`、`mplib`、`curobo`、`h5py`、`numpy`、`scipy` 和 `trimesh`。需要 GPU 初始化的 RoboTwin task construction、CuRobo planner、SAPIEN render 和 CUDA tensor 本轮因 GPU0 忙而保持 `not_run_gpu0_busy`；不能用 CPU import 代替这些运行时验证，也不能用 2026-08-10 的历史成功冒充本次 live probe。

## 当前决定

1. 不重新安装或重建环境。
2. 继续执行 CPU-only 官方 task/asset/primitive 审计和 additive skeleton。
3. 所有需要渲染、实际物理属性读取、planner、V/H/neutral block 的 probe 等待某次运行前 GPU0 live idle；不使用 GPU 1–7。
4. 当前状态保持 `BLOCKED_BEFORE_STAGE_0`，本文件不构成 Stage 0 授权。

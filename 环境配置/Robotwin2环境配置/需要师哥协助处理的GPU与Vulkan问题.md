# RoboTwin2 配置阻塞：GPU 2 异常及 Vulkan 初始化失败

> 交接对象：服务器管理员 / 师哥  
> 服务器：`fvl09`  
> 最后复核时间：2026-07-25 16:59 CST  
> 系统内核：Ubuntu Linux `5.19.0-50-generic`  
> NVIDIA 驱动：`535.247.01`  
> GPU：8 × NVIDIA GeForce RTX 3090

## 一句话结论

服务器并非缺少 NVIDIA 驱动。驱动、内核模块和 8 张 GPU 的设备节点都存在，但物理
GPU 2（PCI `0000:39:00.0`）当前处于 NVIDIA 驱动明确标记的
`Reset Required: Yes` / `System is not in ready state` 异常状态。

逐卡 CUDA 验证中只有 GPU 2 失败；当全部 8 张卡同时可见时，异常卡会使整个 CUDA
初始化失败。NVIDIA Vulkan 也无法创建逻辑设备，继而阻塞 SAPIEN 和 RoboTwin2 渲染。

## 需要协助处理的对象

| 项目 | 值 |
|---|---|
| GPU 索引 | `2` |
| PCI Bus ID | `00000000:39:00.0` |
| GPU UUID | `GPU-4329227f-0eb2-20ca-97c6-e97253d558cf` |
| 型号 | NVIDIA GeForce RTX 3090 |
| 当前状态 | `Reset Required: Yes` |
| 当前占用 | Xorg PID `3023`，约 10 MiB |

执行管理操作时建议优先使用 PCI Bus ID 或 UUID，避免重启后 GPU 索引发生变化。

## 已确认的现场证据

### 1. 驱动和设备节点存在

宿主机上的 `nvidia-smi` 能正常运行：

```text
NVIDIA-SMI 535.247.01
Driver Version: 535.247.01
CUDA Version: 12.2
```

以下设备节点均存在：

```text
/dev/nvidia0 ... /dev/nvidia7
/dev/nvidiactl
/dev/nvidia-uvm
/dev/nvidia-uvm-tools
/dev/nvidia-modeset
```

因此问题不是“未安装驱动”或“设备节点缺失”。

### 2. GPU 2 明确处于异常状态

`nvidia-smi -i 2 -q` 的关键输出：

```text
GPU Reset Status
    Reset Required                    : Yes
    Drain and Reset Recommended       : No

Fan Speed                             : System is not in ready state
Performance State                     : P0
Power Draw                            : Unknown Error
Graphics                              : System is not in ready state
SM                                    : System is not in ready state
Memory                                : System is not in ready state
Video                                 : System is not in ready state
Encoder                               : Unknown Error
Decoder                               : Unknown Error
```

同时，普通 `nvidia-smi` 中 GPU 2 的风扇和功耗显示为 `ERR!`。该异常在两次间隔约
20 分钟的复核中持续存在，并非瞬时采样错误。

### 3. 逐卡 CUDA 验证将问题定位到 GPU 2

在同一个 RoboTwin2 Python/PyTorch 环境中，分别只暴露一张物理 GPU：

```text
physical_gpu=0 PASS NVIDIA GeForce RTX 3090
physical_gpu=1 PASS NVIDIA GeForce RTX 3090
physical_gpu=2 FAIL CUDA driver initialization failed
physical_gpu=3 PASS NVIDIA GeForce RTX 3090
physical_gpu=4 PASS NVIDIA GeForce RTX 3090
physical_gpu=5 PASS NVIDIA GeForce RTX 3090
physical_gpu=6 PASS NVIDIA GeForce RTX 3090
physical_gpu=7 PASS NVIDIA GeForce RTX 3090
```

全部 GPU 可见时：

```text
available False count 8
CUDA driver initialization failed
```

这说明本地 CUDA Toolkit、PyTorch 和其余 7 张 GPU 都可以工作，失败点集中在 GPU 2。

### 4. Vulkan 与 RoboTwin2 渲染被阻塞

只加载 NVIDIA Vulkan ICD：

```bash
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json \
  vulkaninfo --summary
```

结果：

```text
vkCreateDevice: Failed to create device chain
vkCreateDevice failed with ERROR_INITIALIZATION_FAILED
```

RoboTwin2 官方渲染测试：

```bash
cd /bigbig_nfs_share/lijunhui/Robotwin2/project/RoboTwin
source /bigbig_nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh
python script/test_render.py
```

结果：

```text
Render Error
```

`CUDA_VISIBLE_DEVICES` 可以绕开 GPU 2 做纯 CUDA 计算，但它不保证 NVIDIA Vulkan
和 SAPIEN 不枚举异常物理卡，因此不是完整解决方案。

## 对 RoboTwin2 的实际影响

- SAPIEN 的纯 CPU 碰撞/物理步进已验证可用。
- 任何需要 RenderSystem、相机画面、材质或视觉资产的功能当前不可用。
- RoboTwin2 官方 render test 未通过。
- clean demo、图像观测和数据采集暂时不能做可靠验收。
- 当前不应把故障归因于 RoboTwin2 Python 环境或用户目录内的 CUDA 12.1。

补充说明：`nvidia-smi` 中的 `CUDA Version: 12.2` 表示驱动支持的最高 CUDA API
版本，不表示 RoboTwin2 在使用服务器 `/share/apps/cuda/12.2`。本项目使用的是用户
目录内的 CUDA 12.1：

```text
/bigbig_nfs_share/lijunhui/Robotwin2/tools/cuda-12.1
```

## 希望师哥执行的处理

以下操作需要管理员权限，并会影响服务器上的图形会话或 GPU 作业。请先与正在使用
该节点的同学协调，不要直接结束未知任务。

### 方案 A：释放占用后尝试单卡 reset

1. 确认 GPU 2 当前占用：

   ```bash
   nvidia-smi
   sudo fuser -v /dev/nvidia2
   ```

2. 停止或迁移 GPU 作业，并正确停止占用 GPU 2 的 Xorg/显示管理器及监控客户端。
   当前 Xorg PID `3023` 同时使用多张 GPU，不能在图形会话运行时直接 reset。

3. 使用稳定标识对 GPU 2 执行 reset：

   ```bash
   sudo nvidia-smi --gpu-reset \
     -i GPU-4329227f-0eb2-20ca-97c6-e97253d558cf
   ```

4. reset 后重新验证下文“验收标准”。

NVIDIA 官方说明要求：执行 GPU reset 时，目标 GPU 不能被 CUDA、X server、监控程序
或其他客户端占用；reset 也不保证在所有硬件故障状态下都能成功。

### 方案 B：维护窗口重启或断电冷启动

如果 Xorg 无法安全释放、在线 reset 被拒绝，或 reset 后 GPU 仍显示异常，建议在维护
窗口重启节点。若普通重启不能恢复，则进行完整断电冷启动。

### 方案 C：冷启动后仍复发时检查硬件

如果 GPU 2 冷启动后再次出现同样状态，建议检查：

- GPU 2 的独立供电线和电源负载；
- PCIe 插槽、延长线或转接板；
- 显卡散热、风扇及温度；
- 显卡本体稳定性；
- 内核日志中的 NVRM/Xid 记录；
- 是否需要在维护窗口升级到管理员认可的 NVIDIA 驱动版本。

建议管理员在故障复现时保存：

```bash
sudo journalctl -k -b | grep -Ei 'NVRM|Xid|fallen off|RmInitAdapter'
nvidia-smi -i GPU-4329227f-0eb2-20ca-97c6-e97253d558cf -q
```

当前普通用户上下文未能读取到足够的内核 Xid 记录，因此尚不能仅凭现有证据判断最初
触发 reset-required 状态的是供电、PCIe、温度、驱动还是显卡硬件本身。可以确定的是：
GPU 2 当前需要恢复，且它直接导致 CUDA/Vulkan/RoboTwin2 验证失败。

## 恢复后的验收标准

### 1. GPU 2 健康状态

```bash
nvidia-smi -i GPU-4329227f-0eb2-20ca-97c6-e97253d558cf -q
```

至少应满足：

- 不再显示 `Reset Required: Yes`；
- 不再出现 `System is not in ready state`；
- 风扇、功耗和时钟查询不再显示 `ERR!` / `Unknown Error`。

### 2. GPU 2 单卡 CUDA

```bash
source /bigbig_nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh
CUDA_VISIBLE_DEVICES=GPU-4329227f-0eb2-20ca-97c6-e97253d558cf python -c \
  'import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))'
```

预期：

```text
True NVIDIA GeForce RTX 3090
```

### 3. 全卡 CUDA

```bash
source /bigbig_nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh
python -c \
  'import torch; print(torch.cuda.is_available(), torch.cuda.device_count())'
```

预期：

```text
True 8
```

### 4. NVIDIA Vulkan

```bash
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json \
  vulkaninfo --summary
```

预期：能够列出 NVIDIA 物理设备，不再出现
`vkCreateDevice failed with ERROR_INITIALIZATION_FAILED`。

### 5. RoboTwin2 官方渲染测试

```bash
source /bigbig_nfs_share/lijunhui/Robotwin2/config/activate_robotwin2.sh
cd /bigbig_nfs_share/lijunhui/Robotwin2/project/RoboTwin
python script/test_render.py
```

预期：

```text
Render Well
```

通过以上检查后，再继续验证 clean demo 和数据采集。

## 操作边界说明

本次排查只进行了只读检查和用户目录内的 RoboTwin2 验证，没有执行 `sudo`、GPU
reset、停止系统进程、重启、驱动安装/卸载或系统文件修改。

# 同步原生高清多视角录像wrapper（未GPU验证）

入口 `runtime.run(manifest, meter=...)`，要求video_capture_required=true、video_mode=`native_HD_all_existing_views_v2`；kind/物理/数值Gate及6solver首资格预算不变。旧upright runtime/design及head-only_v1源不改。

head、left_wrist、right_wrist、observer、world1、world2按实际属性枚举；world1/2即使内部name相同仍保留不同对象的视角。额外static按6格一页另存MP4，不悄悄丢弃。每个视角新建独立960×720的纯render camera，复制源相机K的像素尺度及每次采样的entity/local姿态；**不读取/放大320×240 RGB**，不修改manager原相机列表、K、width/height/near/far或model current配置。

每页3×2拼图2880×1440、英语角度标签、25fps/每10控制步及精确初末帧；RGB直接来自新HD相机Color buffer，非重建、非重新执行轨迹。head-only旧版只是未执行历史，不应作为本次启动入口。编码H.264 CRF20/veryfast/每page2线程，FONT实际文件与SAPIEN camera API/ffmpeg路径已绑定CPU_AUDIT。

录像在原context返回（固定60settle之后）、standing和第一动作前开始，使用原dense trace钩子推进并由原context退出finalize；不声称包含60settle动态。如果standing立即失败，可能只有六角度初始静态帧，receipt明确initial-only，不冒充动作视频。物理资格基础终端原样保留，另写HD_video_qualification_terminal.json和真实MP4哈希；video失败保留physical_qualification_pass，不允许为补录像擅自重跑物理。

构造/首帧错误路径保证无论recorder.abort是否再抛错，都尝试inner.__exit__；HD_start_failure.json分别保留主异常和cleanup异常。debug cameras在close/abort移除，原相机配置再次核验，视频首次解码检查2880×1440。Renderer新增内存/时间尚未实测：仍900s child/1080s lease，最多24view/602帧每page，超界或超时失败留证，不放宽预算。普通6view下为一页，6张原生960×720 render buffers，不新增solver/scene/物理动作。

6项CPU fixture测试0.648s通过（handle59237），没有Scene/CUDA/GPU录制。fixture编码只是测试字节，不作为真实诊断视频。下一步须主线程版本化替代尚未launch清单并绑定本目录/依赖，再在同一次真实资格中录制、核验后收录Vault；本代理未reserve、未签manifest或GPU执行。

# F3 shared-prefix no-suffix diagnostic v1 result

## FAILED_PHYSICAL_WITH_EVIDENCE

唯一one-shot在第一张fresh scene即被未改的pre-shared-V physical Gate拒绝，因此按fail-fast合同停止在`1/3`；scene2/3未启动，suffix planner、suffix execution、release与recovery均为0。该结果不修改Stage 0 seal，也不是accepted root或formal data。

`close=0.35`没有维持抓持。接触只在step 876–1089存在，step 1090首次丢失且不再恢复。更重要的是，impact review中`0.01575 m`只是未验证的静态映射估计；真实final drive target为`0.0092500001 m`，接触在drive target从`0.0122886589 m`降到`0.0121099092 m`时已丢失。这一新证据否定了repair hypothesis，但不回写或伪造旧review。

post-close settle结束step 1455后，抓取平移在1459首次超过5 mm，旋转在1468首次超过50 mrad；pre-shared-V漂移达到214.546 mm/427.264 mrad。最终50帧瓶子仍全部接触pad/table，EEF线速度在2605–2606超门限。失败仍明确位于shared prefix，早于shared V与任何suffix。

运行使用physical GPU4 / `GPU-6a2b7387-0c6e-f68d-4f88-92e859c27da7`。Admission与launch均12 MiB/0%/P8/无compute；Guard post为12 MiB/0%/P0 cooldown/无process且release verified，独立live postcheck恢复12 MiB/0%/P8/无process。Child PID 434792退出，task-owned orphan=0，source-lock、job-cache cleanup与lease release均通过。

依冻结合同，不允许第二次F3 diagnostic，也不开放post-Stage-0 F3 development root。F3 development template仍未ready；下一步转入F4 layout impact review与CPU geometry/IK/planner-only audit。

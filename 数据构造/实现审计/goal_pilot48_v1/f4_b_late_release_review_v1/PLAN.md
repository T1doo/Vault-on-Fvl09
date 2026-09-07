# F4 motion late-release：只追加，不改原Guard，不提前接受

原Goal数据/计数/科学结果通过，Guard child exit0、execution_errors空、cache_removed/lease_released true；唯一cleanup错误是CooldownExhausted。13轮selected GPU7都仅PID3963009。原task_owned_cleanup_pass=false是代码将baseline恢复纳入cleanup综合条件的真实结果，不能直接改true。

Guard记录没有UID/完整host process tree，不能只从compute PID断言foreign。MAIN_HOST_OBSERVATION_001由主线程host采集，绑定原GuardfileSHA、检查原Guard/child/PGID不存在、UID10201与GPU7占用UID10198不同；其selected_gpu_idle_now=false，仍pending。此main文件不由子代理写入或修改。

## 未来唯一可解封的证据链

1. 原source/input和全部motion raw/current/trace/video/cohort/index/Goal/Guard字节不变；pending review锁定这些hash。
2. 主线程新的真实host观测：全GPU0–7 snapshot、同physical7/UUID，原PID/PGID及所有已识别worker不存在，cache/lease已释放；不读取args/env、不杀foreign。
3. GPU7实际满足原Guard相同baseline谓词：memory≤max(64MiB,pre+32MiB)，util=0、P8/P12、compute列表空。不能仅“own PID没了”或“占用是foreign”就算idle。
4. verify_future_idle重新检查hash和host字段；默认用检查结束时真实UTC，观测必须晚于原cooldown且≤30s（更保守的freshness约束，不放宽原规则）。若hash审计使观测过期，重新获取观测，不重跑GPU job。测试时只有双CPU_TEST_FIXTURE才可传模拟时钟。
5. 新late_release_resolution写原Guard综合cleanup=false/POST_CHILD=false仍保留，并记录late_baseline_restoration_verified；不得输出伪造的改写Guard。主线程单独判断、保存不可覆盖receipt，再执行一次幂等预算reconcile。
6. 资源计费建议沿用原Guard实际1920.5208706855774s→ceil+1=1922s；原lease已释放后的foreign等待不是本GPU作业lease时间。无新Scene/solver/collection。该费用规则须由main明确记录，不在子代理改账。

## 接受入口需要同时版本化两处

当前f4_b_pilot_acceptance_v1.terminal_inputs要求原Guard综合pass；current_recovery V1/V2同样要求producer Guard cleanup。不能只绕开一个检查，也不能传一份flags被改true的virtual Guard冒充原件。应新建late-release-aware terminal predicate和current-recovery入口：读取原Guard + exact新增resolution + host snapshot/ownership/hash链，分别报告original_guard_cleanup_pass=false和late_release_resolved=true，再做原6格全量data/current/finalstate验收。所有其他阈值/源/分母保持不变。

本目录当前只产pending review和pure verifier方案/CPU负例，没有真实late-idle receipt，没有当前GPU idle声明，没有budget/pilot接受或GPU操作。主线程可在原GPU实际空闲前等待；foreign占用不是可以放宽规则、共享GPU或杀进程的理由。

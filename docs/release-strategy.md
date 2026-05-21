# 发布策略设计

## 发布层次

项目支持三个层次的发布能力：

1. `kubectl apply` + rollout guard：适合本地 kind 演示。
2. Helm Chart：适合参数化部署和多环境配置。
3. Argo CD + Argo Rollouts：适合 GitOps 和渐进式发布。

## 滚动发布

当前 Deployment 使用：

- `maxUnavailable: 0`：发布过程中不主动降低可用副本。
- `maxSurge: 1`：允许多创建一个 Pod 提升替换速度。
- `readinessProbe`：新 Pod 未就绪前不接流量。
- `progressDeadlineSeconds`：发布卡住时让控制器明确失败。

## 金丝雀发布

Argo Rollouts 示例采用 10% -> 30% -> 60% -> 100% 的流量递增策略。每个阶段通过 Prometheus 查询错误率和延迟：

- 错误率超过阈值则中止。
- P95 延迟超过阈值则中止。
- 指标正常才继续晋级。

## 回滚策略

自动回滚只解决恢复问题，不等于根因修复。回滚后仍需要：

1. 固化 incident report。
2. 关联 CI 构建、镜像 digest、安全扫描结果。
3. 复盘为什么质量门禁或灰度分析没有提前拦截。

## 发布准入

金丝雀发布和滚动发布都不应只依赖 Pod Ready。项目提供 `opsctl release-gate`，在发布后读取 Prometheus recording rules，并基于错误率、P95 延迟和故障模式状态输出决策：

```bash
python -m tools.opsctl release-gate --prometheus http://localhost:9090 --service cloudnative-devopslab
```

- `promote`：运行时 SLI 满足阈值，可以继续晋级或结束发布。
- `rollback_or_pause`：运行时指标不满足准入，应暂停放量、保留现场并触发回滚或排查。

该设计体现的是“指标即发布准入”，比单纯检查 Deployment rollout 成功更接近生产发布系统。

## 面试讲解重点

- 滚动发布保证基础可用性。
- 金丝雀发布降低 blast radius。
- GitOps 保证集群状态可审计、可回滚、可声明式管理。
- Prometheus AnalysisTemplate 把人工观察指标变成自动化发布决策。

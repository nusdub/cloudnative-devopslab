# SLO 与 Error Budget 设计

## SLI 选择

本项目选择两个核心用户体验指标：

| SLI | 说明 | Prometheus 实现 |
|---|---|---|
| Availability | 非 5xx 请求占比 | `1 - 5xx / total` |
| Latency | P95 请求延迟 | histogram p95 |

## SLO 目标

- Availability：99.9%。
- P95 latency：小于 300 ms。

99.9% 可用性意味着错误预算为 0.1%。在 30 天窗口内，理论不可用预算约 43.2 分钟。

## Burn-rate 告警

单窗口错误率容易误报或漏报，因此使用多窗口多燃烧率：

- Fast burn：5m + 1h，适合快速发现严重故障。
- Slow burn：30m + 6h，适合发现持续性退化。

## 设计权衡

- 短窗口灵敏，但容易被瞬时尖刺触发。
- 长窗口稳定，但发现速度慢。
- 多窗口组合可以同时控制发现速度和告警质量。

## 发布准入

发布阶段不只检查 Pod Ready，还应检查：

- 5xx error ratio 是否低于阈值。
- P95 latency 是否低于阈值。
- fault mode 是否关闭。
- 最近是否存在 critical alert。

这些规则可以用于 Argo Rollouts AnalysisTemplate 或 `opsctl` 发布守卫。

示例：

```bash
python -m tools.opsctl release-gate \
  --prometheus http://localhost:9090 \
  --service cloudnative-devopslab \
  --error-ratio-threshold 0.001 \
  --p95-latency-seconds-threshold 0.3
```

返回 `decision: promote` 才继续晋级；返回 `rollback_or_pause` 时应暂停放量、保留现场并执行回滚或根因排查。

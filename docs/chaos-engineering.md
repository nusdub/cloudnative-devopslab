# 混沌工程实验设计

## 目标

混沌实验不是为了制造故障，而是验证系统在受控故障下是否仍满足 SLO，验证告警、Runbook、PDB、HPA、发布准入和回滚流程是否形成闭环。

## 实验准入

执行任何实验前必须满足：

1. 当前 `release-gate` 为 `promote`。
2. 最近一次发布证据包已生成并归档。
3. 实验窗口内无真实线上事故。
4. 明确 blast radius：仅限 `devopslab` 命名空间和 `app=cloudnative-devopslab` 的 Pod。
5. 明确停止条件：错误率、P95 延迟、Pod Ready 数或告警超过阈值立即停止。

## 实验矩阵

| 实验 | 资产 | 假设 | 观测指标 | 停止条件 |
|---|---|---|---|---|
| Pod Kill | `chaos/pod-kill.yaml` | PDB、ReplicaSet 和 readiness 能保证单 Pod 被杀后服务仍可用 | Ready Pod 数、5xx、P95、重启数 | Ready Pod < 2 或 fast burn 触发 |
| Network Delay | `chaos/network-delay.yaml` | 250ms 延迟会触发 P95 告警但不应造成大面积 5xx | P95/P99、error ratio、burn rate | P95 > 1s 持续 3 分钟或错误率 > 1% |
| Fault Mode | `scripts/inject-fault.sh` | 故障配置能被 readiness、告警和 release-gate 拦截 | readiness、fault_mode_enabled、error ratio | fault_mode_enabled 告警触发后立即回滚 |

## 推荐流程

```bash
python -m tools.opsctl release-gate --prometheus http://localhost:9090
python -m tools.opsctl evidence-bundle --namespace devopslab --prometheus http://localhost:9090
kubectl apply -f chaos/pod-kill.yaml
kubectl -n devopslab get pods -w
python -m tools.opsctl release-gate --prometheus http://localhost:9090
```

## 复盘问题

- 告警是否在预期时间内触发？
- Runbook 是否能让非项目作者执行恢复？
- release-gate 是否能阻止继续放量？
- 证据包是否足够支撑根因分析？
- 是否需要新增回归测试、策略规则或容量阈值？

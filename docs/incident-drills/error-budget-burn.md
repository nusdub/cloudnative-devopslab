# 故障演练：错误率燃烧 Error Budget

## 目标

验证 99.9% availability SLO 的 fast burn 与 slow burn 告警。

## 注入方式

```bash
kubectl -n devopslab patch configmap cloudnative-devopslab-config --type merge -p '{"data":{"FAULT_MODE":"true"}}'
kubectl -n devopslab rollout restart deployment/cloudnative-devopslab
```

## 预期

- `/readyz` 返回 503。
- `/api/orders` 返回 500。
- `SLOFastBurnAvailability` 触发。
- Runbook 指向 `docs/runbooks/slo-fast-burn.md`。

## 恢复

```bash
kubectl -n devopslab patch configmap cloudnative-devopslab-config --type merge -p '{"data":{"FAULT_MODE":"false"}}'
kubectl -n devopslab rollout restart deployment/cloudnative-devopslab
kubectl -n devopslab rollout status deployment/cloudnative-devopslab --timeout=120s
```

# 故障演练：高延迟导致 SLO 告警

## 目标

验证 P95 latency SLO、Grafana 看板和 `HighP95Latency` 告警是否生效。

## 注入方式

```bash
kubectl -n devopslab patch configmap cloudnative-devopslab-config --type merge -p '{"data":{"SLOW_REQUEST_MS":"500"}}'
kubectl -n devopslab rollout restart deployment/cloudnative-devopslab
```

## 施压

```bash
k6 run loadtest/orders.js
```

## 预期

- P95 latency 超过 300 ms。
- `HighP95Latency` 告警触发。
- Grafana 延迟面板出现明显上升。

## 恢复

```bash
kubectl -n devopslab patch configmap cloudnative-devopslab-config --type merge -p '{"data":{"SLOW_REQUEST_MS":"0"}}'
kubectl -n devopslab rollout restart deployment/cloudnative-devopslab
```

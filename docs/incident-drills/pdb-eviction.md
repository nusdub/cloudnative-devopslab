# 故障演练：Pod 驱逐与 PDB 验证

## 目标

验证 PodDisruptionBudget 是否能在主动驱逐期间保护最小可用副本。

## 前提

Deployment 至少有 2 个副本，PDB `minAvailable: 1`。

## 操作

```bash
kubectl -n devopslab get pdb
kubectl -n devopslab get pods -l app=cloudnative-devopslab
kubectl -n devopslab drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

## 预期

- Kubernetes 不会同时驱逐所有可用 Pod。
- 服务仍至少保留一个可用副本。
- 如果副本数不足，驱逐会被 PDB 阻止。

## 复盘重点

PDB 只能处理 voluntary disruption，不能防止节点宕机等 involuntary disruption。因此仍需要多副本、跨节点调度和容量冗余。

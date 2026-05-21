# 故障演练：异常配置导致服务不可用

## 演练目标

验证发布过程中的健康检查、监控告警和回滚机制是否能发现并恢复异常版本。

## 故障注入方式

将 `FAULT_MODE` 设置为 `true`，应用启动后 `/readyz` 返回 503，业务接口 `/api/orders` 返回 500。

## 预期现象

- Kubernetes Deployment 新 Pod 无法通过 readinessProbe。
- `kubectl rollout status` 超时或失败。
- Prometheus 触发 `FaultModeEnabled` 或 `HighErrorRate` 告警。
- 部署脚本执行 `kubectl rollout undo` 回滚到上一稳定版本。

## 操作步骤

```bash
kubectl -n devopslab patch configmap cloudnative-devopslab-config --type merge -p '{"data":{"FAULT_MODE":"true"}}'
kubectl -n devopslab rollout restart deployment/cloudnative-devopslab
bash scripts/deploy.sh cloudnative-devopslab:local
```

Windows PowerShell：

```powershell
.\scripts\inject-fault.ps1
.\scripts\rollback.ps1
```

## 复盘模板

- 发现时间：Prometheus 告警触发时间。
- 影响范围：订单创建接口 5xx 增高，新版本 Pod 不就绪。
- 根因：异常配置开启故障模式，导致 readinessProbe 失败。
- 恢复动作：自动回滚上一稳定 ReplicaSet。
- 改进项：增加发布前 smoke test、配置校验和灰度阶段错误率观察。

# 容量规划与压测设计

## 目标

容量规划不是简单跑一次压测，而是回答三个问题：

1. 当前配置下服务能承载多少稳定 QPS？
2. 在错误率和 P95 延迟 SLO 约束下，资源水位应该控制在什么范围？
3. HPA 扩容、发布放量和告警阈值是否匹配真实负载？

本项目使用 k6、Prometheus、HPA 与 SLO 指标构建一个可复现的容量验证流程。

## 压测模型

`loadtest/orders.js` 模拟核心写请求：

- API：`POST /api/orders`
- 负载曲线：20 VU 预热，50 VU 稳态，再降为 0
- 门禁：错误率 `< 1%`，P95 延迟 `< 300ms`

运行方式：

```bash
BASE_URL=http://localhost:8000 k6 run loadtest/orders.js
```

Kubernetes 环境可以通过 NodePort 或 port-forward 指向服务：

```bash
kubectl -n devopslab port-forward service/cloudnative-devopslab 8000:80
BASE_URL=http://localhost:8000 k6 run loadtest/orders.js
```

## 容量评估步骤

### 1. 建立基线

在无故障模式、固定副本数下运行压测，记录：

- QPS / RPS
- P50 / P95 / P99 延迟
- HTTP 5xx 比例
- CPU throttling 和 memory working set
- Pod Ready 数与重启次数

基线的意义是确认服务本身和容器配置没有明显问题，不要一开始就依赖 HPA 掩盖单实例性能问题。

### 2. 找到饱和点

逐步提高 VU 或请求速率，观察哪一个指标先触发：

| 现象 | 可能瓶颈 | 处理方向 |
|---|---|---|
| P95 上升但错误率低 | CPU 饱和、队列排队、下游慢 | 优化代码路径、调大 CPU request、降低单 Pod 负载 |
| 5xx 上升且 readiness 波动 | 服务过载或故障配置 | 限流、降级、扩容、修正 probe 参数 |
| CPU 使用率高但吞吐不升 | CPU throttling | 检查 limits、requests 与 HPA 目标 |
| 内存持续上涨 | 泄漏或缓存无界 | 增加内存 profiling、设置缓存上限 |
| HPA 扩容慢 | 指标窗口或冷启动问题 | 调整 HPA behavior、预留容量、优化启动耗时 |

### 3. 校准 HPA

当前 Helm 默认：

- `minReplicas: 2`
- `maxReplicas: 5`
- `targetCPUUtilizationPercentage: 60`
- `scaleUp.stabilizationWindowSeconds: 60`
- `scaleDown.stabilizationWindowSeconds: 300`

设计取舍：

- 目标 CPU 不能太高，否则扩容发生时服务已接近饱和。
- `minReplicas` 不是越低越好，核心服务应保留基础冗余。
- `maxReplicas` 要结合命名空间 ResourceQuota 和节点容量，否则扩容只会变成 Pending。
- 扩容策略要和 P95 延迟 SLO 对齐，而不只是 CPU 指标。
- 缩容稳定窗口用于避免流量抖动、滚动发布和节点维护期间过早释放容量。

可以用 `opsctl capacity-advice` 把压测基线转成副本建议：

```bash
python -m tools.opsctl capacity-advice --observed-rps 200 --observed-replicas 2 --target-rps 350
```

### 4. 建立发布容量门禁

发布后不仅检查 Pod Ready，还要检查 SLI：

```bash
python -m tools.opsctl release-gate \
  --prometheus http://localhost:9090 \
  --service cloudnative-devopslab \
  --error-ratio-threshold 0.001 \
  --p95-latency-seconds-threshold 0.3
```

期望输出中的 `decision` 为 `promote`。如果为 `rollback_or_pause`，说明发布后运行时指标不满足稳定性准入，应暂停放量或回滚。

## 推荐容量结论模板

面试或项目展示时，可以用如下结构表达压测结果：

```text
在 2 副本、每 Pod 100m CPU request / 500m CPU limit、128Mi memory request / 512Mi limit 配置下，使用 k6 对核心下单接口进行阶梯压测。
在 N RPS 前，错误率低于 0.1%，P95 延迟低于 300ms；当负载升至 M RPS 时，P95 延迟先于错误率恶化，判断主要瓶颈是 CPU 饱和导致排队。
因此将 HPA 目标 CPU 设置为 60%，保留 2 个最小副本，并通过 release-gate 在发布后检查 5m 错误率和 P95 延迟，避免低容量版本继续放量。
```

## 面试讲解重点

- 压测不是为了给出一个绝对数字，而是为了找到容量边界和退化模式。
- 资源指标需要和用户体验指标关联，CPU 高不一定是事故，P95 和错误率恶化才影响 SLO。
- HPA 是缓解流量波动的手段，不是无限扩容能力；还要考虑冷启动、节点容量、配额和下游依赖。
- 发布门禁应使用运行时 SLI，而不是只看构建成功和 Pod Ready。

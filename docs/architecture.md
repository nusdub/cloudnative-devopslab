# 架构设计

## 设计目标

CloudNative DevOpsLab 的目标不是演示某个单点工具，而是构建一个小而完整的云原生发布稳定性平台，用一个 FastAPI 服务串联 CI/CD、Kubernetes、可观测性、SLO 和运维自动化。

## 核心链路

```text
Code -> CI Quality Gates -> Container Artifact -> Security Scan -> Registry
     -> GitOps Desired State -> Kubernetes Runtime -> Observability
     -> Alert + Runbook -> opsctl Automation -> Incident Review
```

## 关键设计决策

### 为什么拆分 CI Job

将 quality、test、container、security、deploy-verify 拆分，目的是让失败定位更清晰，并让质量门禁在构建镜像之前尽早失败，节省流水线资源。

### 为什么使用不可变镜像 tag

`latest` 无法准确表达发布版本，也不利于回滚和审计。项目使用 `sha-<commit>` 作为镜像 tag，确保运行中的版本能追溯到 Git commit、CI 记录和安全扫描结果。

### 为什么 readiness 和 liveness 分离

- readiness 决定 Pod 是否接流量，适合表达依赖未就绪、配置异常、灰度验证失败等状态。
- liveness 决定是否重启容器，应避免把短暂依赖抖动误判为进程不可恢复。

### 为什么需要 PDB

滚动升级、节点维护或主动驱逐时，PDB 保证最小可用副本，避免维护动作造成服务完全不可用。

### 为什么需要 NetworkPolicy

默认全通网络不符合最小权限原则。NetworkPolicy 用于限制服务只接受来自 ingress、monitoring 或同命名空间内允许来源的流量。

### 为什么需要 SLO 而不是只看 CPU/内存

CPU/内存是资源指标，不直接代表用户体验。SLO 使用请求成功率和延迟等用户视角指标衡量服务可靠性，更适合驱动发布准入、告警和故障响应。

# 大厂 SRE / 运维开发能力模型映射

## 项目定位

CloudNative DevOpsLab 不是单纯的 CI/CD Demo，而是围绕“稳定、可控、可审计地发布并运行服务”的 SRE 工程闭环。面试展示时应把它讲成一个小型平台能力：用流水线、制品治理、Kubernetes、GitOps、SLO、故障演练和运维工具把人工经验固化为系统。

## 招聘要求到项目能力的映射

| 大厂常见要求 | 项目对应实现 | 可讲出的深度 |
|---|---|---|
| 熟悉 Linux、容器、Kubernetes | Dockerfile、Helm、Deployment、Probe、HPA、PDB、NetworkPolicy、RBAC、安全上下文 | Pod 生命周期、优雅下线、资源隔离、调度与可用性权衡 |
| 熟悉 CI/CD 与发布系统 | GitHub Actions 多阶段流水线、不可变镜像、kind 部署验证、Argo CD、Argo Rollouts | 质量门禁前置、制品不可变、发布准入、渐进式放量、失败回滚策略 |
| 有可观测性建设经验 | Prometheus 指标、recording rules、burn-rate alerts、Grafana、结构化日志、OpenTelemetry | RED 方法、SLI/SLO、错误预算、告警降噪、指标与发布决策联动 |
| 有稳定性治理经验 | SLO 文档、Runbook、故障演练、PDB 驱逐演练、fault injection、Chaos Mesh 风格实验 | 从发现、定位、缓解、复盘到预防的闭环 |
| 有平台治理经验 | Kyverno/OPA 策略、变更风险分级、生产准入、发布证据包 | 把最佳实践从文档变成可执行的准入和治理机制 |
| 有运维开发能力 | `opsctl` 巡检、SLO 报告、release gate、风险分级、生产 readiness、证据包、回滚、incident report | 把手工操作产品化，形成平台工具而非个人经验 |
| 有安全与合规意识 | Trivy、Gitleaks、Semgrep、SBOM、Cosign、最小权限 RBAC/NetworkPolicy | 软件供应链威胁模型、漏洞准入、制品追溯与签名验真 |
| 能做容量与性能治理 | k6 压测、HPA、资源 requests/limits、延迟 SLO | 压测模型、容量水位、扩缩容触发、性能退化定位 |

## 技术画像强化点

### 1. 从“会用工具”升级为“能设计发布系统”

不要只说使用 GitHub Actions、Helm、Argo CD。要强调为什么流水线要分层：

- `quality` 和 `test` 在构建镜像前失败，节省构建与扫描成本。
- 镜像 tag 绑定 commit，避免 `latest` 导致回滚不可审计。
- 安全扫描和 SBOM 是制品准入的一部分，而不是上线后的补救动作。
- `release-gate` 用运行时 SLI 决定继续发布、暂停还是回滚。

### 2. 从“部署服务”升级为“Kubernetes 生产化治理”

可重点展开这些设计取舍：

- `readinessProbe` 控制接流量，`livenessProbe` 控制是否重启，二者不能混用。
- `maxUnavailable: 0` 适合小副本服务，降低滚动发布期间容量下降风险。
- `PDB` 能约束主动驱逐，但不能阻止节点故障，因此还要配合多副本与拓扑分布。
- `NetworkPolicy` 默认拒绝思维比默认全通更接近生产环境。
- `readOnlyRootFilesystem`、`runAsNonRoot`、`drop ALL capabilities` 降低容器逃逸影响面。

### 3. 从“有监控”升级为“SLO 驱动稳定性”

面试官通常会区分监控堆砌和稳定性设计。可以这样讲：

- CPU/内存是资源指标，不能直接表达用户体验。
- Availability 与 P95 latency 是面向用户体验的 SLI。
- Error Budget 把可靠性目标转化为发布节奏约束。
- burn-rate 多窗口告警兼顾快速发现和告警降噪。
- Runbook 把告警转化为可执行响应流程，避免只报警不闭环。

### 4. 从“脚本能力”升级为“运维平台化思维”

`opsctl` 的价值不是替代 `kubectl`，而是把跨系统判断固化成一个稳定接口：

- `doctor` 汇总核心资源状态，降低新人排障门槛。
- `release-status` 输出镜像、Ready 副本、可用副本，方便发布审计。
- `slo-report` 读取 Prometheus，形成稳定性快照。
- `release-gate` 根据 SLI 自动给出 `promote` 或 `rollback_or_pause` 决策。
- `change-risk` 根据变更路径输出风险等级和必须执行的门禁。
- `prod-readiness` 把生产 checklist 固化成可执行准入。
- `capacity-advice` 基于压测基线、目标 RPS 和预留 headroom 推导副本建议。
- `evidence-bundle` 固化发布证据，把镜像版本、副本状态、重启次数和 SLO 快照关联到一次发布。
- `incident-report` 固化复盘模板，推动故障处理标准化。

## 面试展示顺序

1. 用一句话说明项目目标：安全发布与稳定运行微服务。
2. 展示 CI/CD 图，强调质量门禁、制品治理、安全扫描、部署验证。
3. 展示 Helm/Kubernetes，讲生产化配置背后的取舍。
4. 展示策略即代码和风险分级，说明如何把人工 checklist 变成平台准入。
5. 展示 Prometheus/Grafana/SLO，讲如何把指标用于告警和发布准入。
6. 演示混沌实验、故障注入或 `release-gate`，说明如何自动暂停或回滚。
7. 总结为“我不只是会搭工具，而是能把稳定性目标落成工程机制”。

## 简历表述优化

推荐写法：

- 设计并实现基于 GitOps 与 SLO 的云原生发布稳定性平台，覆盖质量门禁、策略准入、风险分级、镜像构建、安全扫描、SBOM、制品签名、Helm 参数化部署、Argo Rollouts 金丝雀发布与 Prometheus 指标准入。
- 基于 RED 指标和 Error Budget 设计 99.9% 可用性 SLO 与 P95 延迟 SLO，落地 recording rules、multi-window burn-rate 告警、Grafana 看板、Runbook 和混沌实验，将告警、发布版本与故障复盘关联。
- 开发 `opsctl` 运维 CLI，封装巡检、发布状态审计、SLO 报告、发布准入、变更风险分级、生产 readiness、容量建议、发布证据包、回滚与 incident report 生成能力，将人工发布验证流程工具化、标准化。
- 完成 Kubernetes 生产化治理，包括 Probe、HPA、PDB、NetworkPolicy、RBAC、ResourceQuota、SecurityContext、优雅下线与故障演练，验证滚动发布失败、高延迟、错误预算燃烧和 Pod 驱逐场景。

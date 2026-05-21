# 平台治理与发布准入设计

## 设计目标

大厂 SRE / 运维开发岗位关注的不只是“能部署服务”，而是如何把发布风险、稳定性目标、安全基线和故障响应变成平台化机制。本项目在 CI/CD、Kubernetes、GitOps、SLO 之上增加治理层：策略即代码、变更风险分级、生产准入、发布证据包和混沌实验。

## 治理闭环

```text
代码变更
  -> change-risk 风险分级
  -> quality/test/security/policy gates
  -> Helm/Kubernetes 渲染与准入
  -> GitOps / Rollout 渐进式发布
  -> Prometheus release-gate
  -> evidence-bundle 证据归档
  -> chaos experiment / incident drill
  -> runbook / policy / test 反向固化
```

## 策略即代码

项目提供两类策略资产：

- `policies/release-gates.yaml`：项目级发布准入配置，用于 `opsctl prod-readiness` 和 `change-risk`。
- `policies/kyverno-production-guardrails.yaml`：集群准入控制示例，约束 non-root、只读根文件系统、资源 requests/limits、探针和不可变镜像标签。
- `policies/deployment.rego`：OPA/Rego 示例，用于表达 Deployment 级可靠性与安全规则。

策略不应只存在于文档中，而应进入 CI/CD 和集群准入路径。这样可以避免个人经验依赖，降低不同团队、不同环境之间的治理漂移。

## 变更风险分级

`opsctl change-risk` 根据变更路径给出风险等级和必需门禁：

```bash
python -m tools.opsctl change-risk Dockerfile policies/release-gates.yaml
```

| 风险 | 典型变更 | 需要门禁 |
|---|---|---|
| low | 文档、测试、不影响运行时的脚本 | quality、test |
| medium | 应用代码、Helm、监控、GitOps | quality、test、security、policy、deploy-verify |
| high | Dockerfile、RBAC、NetworkPolicy、生产 values、SLO/告警规则、策略文件 | quality、test、security、policy、deploy-verify、release-gate、evidence-bundle |

## 生产准入

`opsctl prod-readiness` 检查生产 values 是否满足基线：

```bash
python -m tools.opsctl prod-readiness --values helm/cloudnative-devopslab/values-prod.yaml
```

准入关注：

- 副本数是否满足最小冗余。
- HPA/PDB/ServiceMonitor/ResourceQuota 是否启用。
- 是否使用 non-root、只读根文件系统等安全上下文。
- SLO 阈值是否达到项目约定。

## 发布证据包

`release-plan` 用于在发布前生成结构化发布计划，回答“这次变更风险是什么、需要哪些门禁、生产准入是否满足、如何晋级、如何回滚、需要归档哪些产物”：

```bash
python -m tools.opsctl release-plan Dockerfile app/main.py \
  --image ghcr.io/example/cloudnative-devopslab:sha-demo1234 \
  --output reports/release-plan.json
```

`evidence-bundle` 用于将一次发布的关键事实固化为 JSON：

- 镜像与版本。
- Deployment 副本状态。
- Pod 重启次数。
- SLO 快照。
- 发布时间。

这使故障复盘不再只依赖聊天记录或人工截图，而是有结构化证据。

## 混沌实验治理

混沌工程必须有准入、假设、观测指标和停止条件。项目通过 `docs/chaos-engineering.md` 和 `chaos/` 目录表达：

- 实验前先运行 release-gate。
- 生成 evidence-bundle 作为基线。
- 限制实验 blast radius。
- 使用 SLO 和告警作为停止条件。
- 复盘后把缺口固化到 Runbook、策略或测试。

## 面试讲解重点

可以强调：

1. CI/CD 只是发布系统的执行层，策略和风险分级才是治理层。
2. 生产准入不能靠人肉 checklist，应变成可执行工具。
3. 发布证据包解决“出了问题之后如何快速还原现场”。
4. 混沌工程不是破坏系统，而是验证 SLO、告警、Runbook 和回滚能力。
5. 策略即代码使平台团队可以把最佳实践规模化复制到多个服务。

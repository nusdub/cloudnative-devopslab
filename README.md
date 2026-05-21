# CloudNative DevOpsLab

**基于 GitOps 与 SLO 的云原生发布稳定性平台。**

本项目面向大厂 SRE / 运维开发 / 云原生平台岗位，围绕“如何安全发布并稳定运行一个微服务”构建完整工程闭环：代码质量门禁、容器构建、安全扫描、SBOM、Kubernetes 生产化部署、渐进式发布、SLO/Error Budget、Prometheus 告警、Grafana 看板、故障演练、自动回滚与运维 CLI 工具化。

## 项目亮点

| 能力域 | 项目实现 | 面试价值 |
|---|---|---|
| 工程质量 | ruff、mypy、pytest coverage、pre-commit、分层 CI | 证明不是只会写 YAML，而是理解工程交付质量 |
| CI/CD | 多 Job GitHub Actions、Buildx cache、不可变镜像 tag、并发取消、最小权限、超时控制、kind 部署验证、策略准入 Job | 展示发布流水线设计、质量门禁分层与平台治理意识 |
| 供应链安全 | Trivy、Gitleaks、Semgrep、Syft SBOM、Cosign keyless signing 示例、发布证据模板 | 体现现代 DevSecOps 与制品可信思维 |
| Kubernetes | Probe、HPA、PDB、NetworkPolicy、RBAC、ResourceQuota、安全上下文、优雅下线、准入策略 | 体现生产化 Kubernetes 理解深度 |
| GitOps/渐进式发布 | Helm、Argo CD Application、Argo Rollouts Canary、Prometheus AnalysisTemplate | 从 kubectl apply 升级到声明式发布治理 |
| 平台治理 | Kyverno/OPA 策略、变更风险分级、生产准入、发布计划、发布证据包 | 体现大厂平台工程的规模化治理思维 |
| 可观测性 | Prometheus metrics、低基数路由标签、构建元数据、recording rules、burn-rate alerts、Grafana、OpenTelemetry tracing | 体现 RED/SLO/Error Budget 方法论与指标基数治理意识 |
| 故障演练 | 配置故障、高延迟、错误率、Pod 驱逐、Chaos Mesh 风格实验 | 展示稳定性工程闭环与复盘意识 |
| 运维开发 | `opsctl` CLI：巡检、SLO 报告、发布准入、风险分级、生产准入、容量建议、发布证据包、故障注入、回滚辅助、incident report | 体现把运维经验产品化、工具化的能力 |
| 发布准入 | `opsctl release-gate` 基于 Prometheus SLI 输出 promote / rollback_or_pause 决策 | 体现把 SLO 转化为自动化发布治理的能力 |
| 容量治理 | k6 压测、HPA behavior、资源水位、容量规划文档、`capacity-advice` 副本建议 | 展示性能容量评估、扩缩容设计与容量门禁能力 |

## 架构总览

```text
Developer Push / Pull Request
        |
        v
GitHub Actions
  quality: ruff + format + mypy
  policy: change risk + prod readiness + Helm guardrails
  test: pytest + coverage threshold
  container: Docker Buildx + immutable image tag + release plan
  security: Trivy + SARIF / SBOM / signing workflow
  deploy-verify: kind + rollout guard + smoke test
        |
        v
Container Registry / Signed Artifact
        |
        v
GitOps Desired State
  Helm Chart + Argo CD Application
  Argo Rollouts Canary + Prometheus analysis
        |
        v
Kubernetes Runtime
  Deployment + Service + HPA + PDB + NetworkPolicy
  RBAC + ResourceQuota + SecurityContext + graceful shutdown
        |
        v
Observability and Reliability
  Prometheus metrics + low-cardinality labels + build metadata
  recording rules + burn-rate alerts
  Grafana SLO dashboard + Alertmanager + Runbooks
  OpenTelemetry traces + structured JSON logs
        |
        v
Ops Automation
  opsctl doctor / release status / slo report / release gate
  change risk / prod readiness / release plan / capacity advice
  evidence bundle / rollback / incident report
```

## 项目结构

```text
.
├── app/                         FastAPI 示例服务、指标、日志、Tracing
├── tests/                       pytest 测试
├── k8s/                         Kubernetes 生产化 YAML
├── helm/cloudnative-devopslab/  Helm Chart
├── gitops/                      Argo CD 与 Argo Rollouts 示例
├── policies/                    Kyverno/OPA 策略与发布准入规则
├── chaos/                       Chaos Mesh 风格故障实验
├── monitoring/                  Prometheus、Alertmanager、Grafana 配置
├── docs/                        架构、发布、SLO、安全、可观测性、Runbook
├── tools/opsctl/                Python 运维开发 CLI
├── scripts/                     部署、回滚、故障注入脚本
├── reports/examples/            发布计划与发布证据包示例
├── loadtest/                    k6 压测脚本
└── .github/workflows/           CI/CD 与安全供应链流水线
```

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证：

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl -X POST http://localhost:8000/api/orders -H "Content-Type: application/json" -d '{"item":"book","quantity":1}'
curl http://localhost:8000/metrics
```

## 工程质量门禁

```bash
ruff check .
ruff format --check .
mypy app tests
pytest
```

测试默认启用 coverage 阈值，低于 80% 会失败。CI 将质量检查、测试、容器构建、安全扫描和部署验证拆成独立 Job，避免“构建成功但质量不可控”。

## Docker 与可观测性环境

```bash
docker build -t cloudnative-devopslab:local .
docker run --rm -p 8000:8000 cloudnative-devopslab:local
```

启动 Prometheus、Alertmanager、Grafana：

```bash
docker compose -f docker-compose.observability.yml up --build
```

访问：

- App: http://localhost:8000
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
- Grafana: http://localhost:3000，账号密码 `admin/admin`

## Kubernetes 部署

```bash
kind create cluster --config kind-config.yaml
docker build -t cloudnative-devopslab:local .
kind load docker-image cloudnative-devopslab:local --name devopslab
bash scripts/deploy.sh cloudnative-devopslab:local
kubectl -n devopslab get pods,svc,hpa,pdb,networkpolicy
```

Windows PowerShell：

```powershell
kind create cluster --config kind-config.yaml
docker build -t cloudnative-devopslab:local .
kind load docker-image cloudnative-devopslab:local --name devopslab
.\scripts\deploy.ps1 -Image cloudnative-devopslab:local
```

## SLI/SLO 设计

| SLI | SLO | 实现 |
|---|---:|---|
| Availability | 99.9% | `1 - 5xx / total` |
| P95 latency | < 300ms | Prometheus histogram p95 |
| Error budget | 0.1% monthly | multi-window burn-rate alerts |

Prometheus 配置包含：

- `monitoring/prometheus/recording-rules.yml`：请求率、错误率、P95/P99、错误预算燃烧率、构建元数据快照。
- `monitoring/prometheus/alert-rules.yml`：服务不可用、SLO 快慢燃烧、高延迟、故障模式、Pod 重启异常。
- `docs/runbooks/`：每个告警对应 Runbook。

其中 `PodRestartSpike` 依赖 kube-state-metrics 暴露的 `kube_pod_container_status_restarts_total`，本地 Docker Compose 只演示应用 SLI，集群环境建议补齐 kube-state-metrics。

## GitOps 与渐进式发布

项目提供两个层次：

1. **基础部署**：`scripts/deploy.sh` 使用 `kubectl apply` 并在 rollout 失败时回滚。
2. **平台化发布**：`gitops/` 提供 Argo CD Application 和 Argo Rollouts Canary 示例，使用 Prometheus 指标作为自动晋级/中止依据。

详见：`docs/release-strategy.md`。

## 运维开发 CLI

```bash
python -m tools.opsctl doctor --namespace devopslab
python -m tools.opsctl release-status --namespace devopslab
python -m tools.opsctl slo-report --prometheus http://localhost:9090
python -m tools.opsctl release-gate --prometheus http://localhost:9090 --service cloudnative-devopslab
python -m tools.opsctl change-risk Dockerfile policies/release-gates.yaml
python -m tools.opsctl prod-readiness --values helm/cloudnative-devopslab/values-prod.yaml
python -m tools.opsctl release-plan Dockerfile app/main.py --image cloudnative-devopslab:local --output reports/release-plan.json
python -m tools.opsctl capacity-advice --observed-rps 200 --observed-replicas 2 --target-rps 350
python -m tools.opsctl evidence-bundle --namespace devopslab --prometheus http://localhost:9090
python -m tools.opsctl incident-report --title "fault mode enabled"
```

`opsctl` 的价值不是替代 kubectl，而是把发布验证、巡检、SLO 报告、发布准入、变更风险分级、生产 readiness、发布计划、容量建议、发布证据留存和故障演练步骤沉淀成可复用工具，体现运维开发能力。

`reports/examples/` 提供可提交的示例报告，真实运行产生的 `reports/*.json` 仍由 `.gitignore` 忽略，避免把每次发布产物污染源码仓库。

## 故障演练

```bash
bash scripts/inject-fault.sh
bash scripts/rollback.sh
```

推荐演练场景：

- 异常配置导致 readiness 失败。
- 5xx 错误率升高触发 SLO fast burn。
- 高延迟触发 P95 latency alert。
- Pod 主动驱逐验证 PDB。
- NetworkPolicy 变更导致监控抓取失败。

详见：`docs/incident-drills/`、`docs/runbooks/` 与 `docs/chaos-engineering.md`。

## 深度文档

- `docs/architecture.md`：总体架构与关键设计决策。
- `docs/release-strategy.md`：滚动、蓝绿、金丝雀与 GitOps 发布权衡。
- `docs/slo-error-budget.md`：SLI/SLO、错误预算、burn-rate 告警设计。
- `docs/supply-chain-security.md`：CI/CD 供应链安全威胁模型与落地策略。
- `docs/capacity-planning.md`：容量规划、压测模型、HPA 校准与发布容量门禁。
- `docs/sre-competency-map.md`：项目能力与大厂 SRE / 运维开发招聘要求映射。
- `docs/observability-design.md`：metrics、logs、traces 三支柱设计。
- `docs/platform-governance.md`：策略即代码、风险分级、生产准入和发布证据设计。
- `docs/ci-cd-assessment.md`：面试官视角的 CI/CD 诊断、短板、优化和追问答案。
- `docs/chaos-engineering.md`：混沌实验准入、实验矩阵、停止条件和复盘问题。
- `docs/interview-deep-dive.md`：面试讲解主线与追问答案。

## 简历写法

**CloudNative DevOpsLab：基于 GitOps 与 SLO 的云原生发布稳定性平台**

- 设计并实现一套面向微服务的云原生 CI/CD 与稳定性工程平台，基于 GitHub Actions、Docker、Helm、Kubernetes、Argo CD/Argo Rollouts 完成从质量门禁、策略准入、镜像构建、安全扫描、SBOM、镜像签名到 GitOps 渐进式发布的闭环。
- 基于 Prometheus/Grafana/OpenTelemetry 构建 RED 指标、结构化日志与链路追踪体系，设计 99.9% 可用性 SLO、P95 延迟 SLO 和多窗口错误预算燃烧告警，将告警关联到 Runbook 与发布版本，实现故障定位闭环。
- 完善 Kubernetes 生产化治理能力，包括 Probe、HPA、PDB、NetworkPolicy、RBAC、Pod 安全上下文、资源配额与优雅下线，并通过 kind 环境复现滚动发布失败、错误率升高、高延迟、Pod 驱逐等故障场景。
- 开发 Python 运维 CLI `opsctl`，封装发布状态巡检、SLO 报告生成、发布准入、变更风险分级、生产 readiness、容量建议、发布证据包生成、故障注入、自动回滚与 incident report 生成能力，将人工运维流程工具化，提升发布验证与故障响应效率。

## 面试讲解主线

1. 这个项目不是简单 CI/CD，而是围绕“安全发布与稳定运行”设计工程闭环。
2. CI/CD 阶段分层做质量门禁、测试、制品构建、安全扫描和部署验证。
3. Kubernetes 层面关注生产化治理：探针、HPA、PDB、NetworkPolicy、资源限制、优雅下线和策略准入。
4. 发布策略从滚动发布扩展到 GitOps + Canary，用 Prometheus 指标自动判断是否晋级，并通过 `opsctl release-gate` 将 SLI 转化为发布准入。
5. 平台治理通过策略即代码、变更风险分级、生产 readiness 和发布证据包降低人工 checklist 依赖。
6. 稳定性通过 SLI/SLO/Error Budget 量化，并用 burn-rate alerts 平衡误报与漏报。
7. 故障处理通过 Runbook、混沌实验和 `opsctl` 工具沉淀，发布证据包把镜像、版本、副本状态与 SLO 快照关联起来，体现运维开发与平台化思维。

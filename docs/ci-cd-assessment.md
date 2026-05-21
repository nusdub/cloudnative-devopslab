# CI/CD 面试官诊断与优化报告

## 诊断视角

如果以大厂 SRE / 平台工程面试官视角评估，一个校招生 CI/CD 项目不能只看“有没有 GitHub Actions YAML”，而要看是否具备以下能力：

1. 能否把质量、安全、发布、回滚、观测串成闭环。
2. 能否把人工 checklist 变成可执行、可审计的门禁。
3. 能否解释流水线分层、失败边界和风险控制。
4. 能否体现供应链安全、制品不可变、证据归档和最小权限意识。
5. 能否说明从本地验证、CI 验证到生产渐进式发布的差异。

## 当前项目优势

| 维度 | 已具备能力 | 面试价值 |
|---|---|---|
| 质量门禁 | ruff、format check、mypy、pytest coverage | 说明候选人理解代码质量不是靠人工 review 兜底 |
| 发布流水线 | quality / policy / test / container / security / deploy-verify 分层 | 说明候选人理解流水线阶段边界 |
| 供应链安全 | Trivy、Gitleaks、Semgrep、SBOM、Cosign keyless 示例 | 能回答现代 DevSecOps 与制品可信问题 |
| Kubernetes 生产化 | Probe、HPA、PDB、NetworkPolicy、RBAC、ResourceQuota、安全上下文 | 能回答服务如何稳定运行 |
| GitOps / Canary | Argo CD、Argo Rollouts、Prometheus AnalysisTemplate | 能回答渐进式发布和自动中止 |
| 平台治理 | change-risk、prod-readiness、release-plan、evidence-bundle | 体现运维开发和平台工程思维 |
| SLO 发布准入 | release-gate 基于 Prometheus SLI 输出 promote / rollback_or_pause | 体现用稳定性目标驱动发布决策 |

## 之前的不足与风险

### 1. 流水线治理还不够生产化

早期 CI/CD 虽然有多个 Job，但缺少顶层默认权限、并发控制、超时控制。真实生产环境中，这会带来几个问题：

- 重复 push 触发多个旧流水线并发执行，可能浪费资源甚至覆盖发布结果。
- Job 卡死会长时间占用 runner。
- 默认 token 权限过大，不符合最小权限原则。

已优化：

- 为 workflow 增加 `permissions: contents: read`。
- 为 workflow 增加 `concurrency`，同一 ref 新流水线会取消旧流水线。
- 为关键 Job 增加 `timeout-minutes`。
- Checkout 默认 `persist-credentials: false`，降低 token 泄露影响面。

### 2. 只有发布结果，没有发布计划

只生成镜像和安全扫描结果，不足以回答：

- 本次变更属于什么风险等级？
- 高风险变更需要哪些额外门禁？
- 生产 values 是否满足发布准入？
- 晋级策略和回滚策略是什么？
- 需要归档哪些证据？

已优化：

- 新增 `opsctl release-plan`。
- CI 自动生成 `reports/release-plan.json`。
- `reports/examples/release-plan.example.json` 提供可读示例。

### 3. 证据目录缺少可读示例

`reports/` 是运行时产物目录，真实报告不应该提交，但完全为空会让面试官不知道它的用途。

已优化：

- `.gitignore` 改为忽略真实产物，但保留 `reports/examples/`。
- 新增 `release-plan.example.json` 和 `release-evidence.example.json`。

### 4. 依赖治理没有体现

真实工程中，CI/CD 还要考虑 GitHub Actions、Python 依赖、容器基础镜像的持续更新。

已优化：

- 新增 `.github/dependabot.yml`，覆盖 GitHub Actions 和 pip 依赖。

### 5. 安全流水线和主流水线存在职责重叠

项目中 `ci-cd.yml` 与 `security.yml` 都包含部分镜像/安全动作。面试时应主动解释：

- `ci-cd.yml` 是主发布链路，关注一次变更从质量门禁到部署验证的闭环。
- `security.yml` 是安全专项链路，关注 secret、SAST、SBOM、签名示例，可独立运行。
- 生产环境中可以进一步合并制品构建，避免同一 commit 构建两次镜像，或通过 reusable workflow 共享构建结果。

## 优化后的 CI/CD 结构

```text
pull_request / push
  -> quality
     - ruff
     - format check
     - mypy
     - opsctl smoke
     - helm lint/template
  -> policy
     - prod-readiness
     - change-risk
  -> test
     - pytest coverage threshold
     - coverage artifact
  -> container
     - immutable sha tag
     - BuildKit provenance
     - image metadata
     - release evidence template
     - release plan
  -> security
     - Trivy filesystem scan
     - Trivy image scan
     - SARIF upload
  -> deploy-verify
     - kind deployment
     - rollout guard
     - smoke test
```

## 面试官可能追问与推荐回答

### Q1：为什么要把 quality、policy、test 拆成不同 Job？

因为它们代表不同失败边界。质量问题应最快失败；策略问题代表平台准入失败；测试问题代表业务行为或回归风险。拆分后更容易定位问题，也能在大规模团队中复用和并行化。

### Q2：为什么 release gate 不只看部署成功？

部署成功只说明 Pod 起来了，不代表用户体验正常。release gate 应基于 SLI，例如 5xx ratio、P95 latency、fault mode、error budget burn，最终输出 promote 或 rollback_or_pause。

### Q3：为什么需要 release plan？

release plan 是发布前的结构化决策记录。它把变更风险、生产准入、晋级策略、回滚策略和证据归档固化下来，减少口头 checklist 和人工经验依赖。

### Q4：为什么 `reports/*.json` 不入库？

真实报告是每次 CI 或发布的运行产物，应进入 artifact、发布系统或审计系统，而不是污染源码仓库。仓库只保留 `reports/examples/` 说明数据结构。

### Q5：这个项目如果上生产还差什么？

还可以继续增强：

- 使用 GitHub Environments 做 prod 审批和 secret 隔离。
- 用 OIDC 对接云厂商而不是长期密钥。
- 用 reusable workflow 复用构建和扫描逻辑。
- 引入真实策略执行器，例如 conftest、Kyverno CLI 或 admission controller。
- 接入真实 Argo Rollouts controller 进行端到端 canary 验证。
- 做依赖锁定和镜像 digest pinning。

## 最终评价

这个项目已经从“会写 CI/CD YAML”升级为“能设计发布稳定性平台”。对于校招生而言，最有竞争力的点不是工具数量，而是能讲清楚：

- 为什么这些门禁存在。
- 哪些风险由哪些阶段控制。
- 发布失败如何自动中止或回滚。
- 如何用 SLO 指标决定晋级。
- 如何把发布证据保留下来支撑复盘。
- 如何把个人运维经验抽象成平台能力。

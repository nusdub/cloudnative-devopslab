# 面试讲解稿

## 30 秒介绍

我做了一个面向 SRE 实习岗位的云原生 CI/CD 与可观测性项目。它不是单纯把服务部署起来，而是围绕稳定性交付设计了完整闭环：代码提交后 GitHub Actions 自动执行 lint、测试、镜像构建和 Trivy 扫描，然后部署到 Kubernetes；发布过程中通过 readinessProbe、livenessProbe 和 rollout status 判断服务健康，如果新版本异常则自动回滚。同时服务暴露 Prometheus 指标，Grafana 展示 QPS、错误率、P95 延迟，并通过 Alertmanager 配置告警。

## 技术决策

### 为什么选 FastAPI

FastAPI 轻量，适合快速实现健康检查、业务接口和 Prometheus metrics。对 SRE 岗位来说，重点不是业务复杂度，而是服务是否具备可部署、可观测、可恢复的生产化能力。

### 为什么选 GitHub Actions

GitHub Actions 和代码仓库天然集成，适合展示云原生 CI/CD 流程。流水线中包含质量门禁和安全扫描，比只构建镜像更能体现工程化意识。

### 为什么 readinessProbe 和 livenessProbe 分开

readinessProbe 用来控制是否接入流量，适合发现配置错误、依赖未就绪等问题。livenessProbe 用来判断进程是否需要重启。两者职责不同，如果混用可能导致不必要重启或异常流量进入服务。

### 为什么要自动回滚

发布失败时，恢复速度比人工排查更重要。自动回滚可以先恢复服务，再做根因分析，符合 SRE 中降低 MTTR 的思路。

## 可扩展方向

- 引入 Argo CD 实现 GitOps。
- 引入 Loki 实现日志检索。
- 使用 Helm 管理多环境参数。
- 接入云厂商 ACK / TKE / EKS。
- 增加灰度发布和金丝雀分析。

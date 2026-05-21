# 供应链安全设计

## 威胁模型

CI/CD 供应链不仅要关注代码漏洞，也要关注：

- 依赖包引入漏洞。
- 镜像基础层漏洞。
- Secret 泄露。
- 构建产物被篡改。
- 运行镜像与源代码提交不可追溯。

## 项目策略

| 风险 | 控制措施 |
|---|---|
| 依赖和镜像漏洞 | Trivy filesystem/image scan |
| Secret 泄露 | Gitleaks workflow |
| 静态代码风险 | Semgrep/Bandit |
| 制品不可追溯 | immutable image tag + metadata artifact |
| 制品内容不可见 | Syft SBOM |
| 制品被篡改 | Cosign keyless signing 示例 |

## 阻断策略

推荐策略：

- PR：扫描结果报告，不一定阻断，避免影响开发反馈速度。
- main：CRITICAL 漏洞阻断发布。
- 例外：需要安全负责人确认并记录豁免理由。

## 面试讲解重点

现代 CI/CD 的目标不是“能部署”，而是“可信部署”：知道谁构建、由哪个 commit 构建、包含哪些依赖、是否有高危漏洞、运行环境中的镜像是否和扫描结果一致。

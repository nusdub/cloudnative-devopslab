# 可观测性设计

## 目标

可观测性不是简单地“接入 Prometheus”，而是让研发和 SRE 能够围绕一次请求回答三个问题：

1. 现在是否影响用户？
2. 影响范围和严重程度是多少？
3. 根因更可能在发布、资源、配置还是依赖？

## 三支柱设计

| 维度 | 项目实现 | 作用 |
|---|---|---|
| Metrics | Prometheus counters/histograms/gauges | 告警、SLO、趋势分析 |
| Logs | JSON structured logs + request_id | 单请求审计和错误上下文 |
| Traces | OpenTelemetry OTLP exporter | 跨组件耗时拆解和调用链定位 |

## RED 方法

服务层面重点看：

- Rate：请求量。
- Errors：5xx 错误率。
- Duration：P95/P99 延迟。

## 标签设计

指标标签控制在低基数范围：method、path、status、job。避免把 user_id、order_id 这类高基数字段放进 Prometheus label。

## 日志字段

推荐每条请求日志包含：

- timestamp
- level
- request_id
- method
- path
- status_code
- latency_ms
- trace_id
- span_id

## 告警设计

告警必须关联：

- severity
- category
- runbook_url
- dashboard_url
- SLO 名称或发布版本

这样可以把“发现问题”连接到“处理问题”。

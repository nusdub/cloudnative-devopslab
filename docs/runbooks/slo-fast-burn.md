# Runbook: Availability SLO Fast Burn

## Meaning

The 99.9% availability SLO is consuming error budget too quickly in both short and medium windows. This alert prioritizes paging-worthy incidents over transient spikes.

## Triage

```bash
kubectl -n devopslab rollout history deployment/cloudnative-devopslab
kubectl -n devopslab get hpa,pods,events
curl -s http://localhost:9090/api/v1/query --data-urlencode 'query=job:http_request_error_ratio:rate5m'
```

## Mitigation order

1. If correlated with a release, pause or roll back.
2. If correlated with saturation, scale replicas or reduce load.
3. If correlated with fault injection/configuration, restore safe config.
4. If dependency related, degrade gracefully or fail over.

## Recovery validation

- Error ratio below 0.1%.
- P95 latency below 300 ms.
- No new critical alerts for at least 10 minutes.

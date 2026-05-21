# Runbook: High Latency

## Meaning

P95 latency is above the 300 ms latency SLO.

## Triage

```bash
kubectl -n devopslab top pods
kubectl -n devopslab get hpa cloudnative-devopslab
kubectl -n devopslab describe pods -l app=cloudnative-devopslab
```

## Common causes

- Slow downstream dependency.
- CPU throttling or memory pressure.
- Recent release changed hot path logic.
- Insufficient replicas under load.

## Mitigation

- Roll back if correlated with release.
- Temporarily increase replicas or resource requests.
- Enable degradation or rate limiting if available.

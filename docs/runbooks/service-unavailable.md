# Runbook: ServiceUnavailable

## Impact

Prometheus cannot scrape the application target. Users may see full or partial service outage.

## First checks

```bash
kubectl -n devopslab get pods -l app=cloudnative-devopslab -o wide
kubectl -n devopslab describe deployment cloudnative-devopslab
kubectl -n devopslab get events --sort-by=.lastTimestamp
```

## Common causes

- Pod crash loop or failed image pull.
- Readiness/liveness probe misconfiguration.
- Service selector mismatch.
- NetworkPolicy blocking Prometheus or ingress traffic.

## Mitigation

```bash
kubectl -n devopslab rollout undo deployment/cloudnative-devopslab
kubectl -n devopslab rollout status deployment/cloudnative-devopslab --timeout=120s
```

## Follow-up

- Compare current image tag with previous stable tag.
- Check release metadata and CI security scan artifacts.
- Record MTTR and root cause in the incident report.

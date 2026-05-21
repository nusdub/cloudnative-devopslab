# Runbook: Fault Mode Enabled

## Meaning

The service is intentionally or accidentally running with fault injection enabled.

## Mitigation

```bash
kubectl -n devopslab patch configmap cloudnative-devopslab-config --type merge -p '{"data":{"FAULT_MODE":"false"}}'
kubectl -n devopslab rollout restart deployment/cloudnative-devopslab
kubectl -n devopslab rollout status deployment/cloudnative-devopslab --timeout=120s
```

## Validation

```bash
curl http://localhost:8000/readyz
curl -X POST http://localhost:8000/api/orders -H 'Content-Type: application/json' -d '{"item":"book"}'
```

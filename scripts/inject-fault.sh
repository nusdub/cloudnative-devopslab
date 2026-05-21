#!/usr/bin/env bash
set -euo pipefail

kubectl -n devopslab patch configmap cloudnative-devopslab-config \
  --type merge \
  -p '{"data":{"FAULT_MODE":"true"}}'
kubectl -n devopslab rollout restart deployment/cloudnative-devopslab
kubectl -n devopslab rollout status deployment/cloudnative-devopslab --timeout=60s || true
kubectl -n devopslab get pods -l app=cloudnative-devopslab

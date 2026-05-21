#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-devopslab}"
DEPLOYMENT="${DEPLOYMENT:-cloudnative-devopslab}"

kubectl -n "${NAMESPACE}" patch configmap cloudnative-devopslab-config \
  --type merge \
  -p '{"data":{"FAULT_MODE":"false"}}' || true
kubectl -n "${NAMESPACE}" rollout undo "deployment/${DEPLOYMENT}"
kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout=120s
kubectl -n "${NAMESPACE}" describe "deployment/${DEPLOYMENT}"

#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:-cloudnative-devopslab:local}"
NAMESPACE="${NAMESPACE:-devopslab}"
DEPLOYMENT="${DEPLOYMENT:-cloudnative-devopslab}"

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/resource-quota.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/networkpolicy.yaml
kubectl apply -f k8s/servicemonitor.yaml || true

kubectl -n "${NAMESPACE}" set image "deployment/${DEPLOYMENT}" app="${IMAGE}"

if ! kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout=120s; then
  echo "rollout failed, restoring safe config and undoing to previous stable ReplicaSet"
  kubectl -n "${NAMESPACE}" patch configmap cloudnative-devopslab-config \
    --type merge \
    -p '{"data":{"FAULT_MODE":"false"}}' || true
  kubectl -n "${NAMESPACE}" rollout undo "deployment/${DEPLOYMENT}"
  kubectl -n "${NAMESPACE}" rollout status "deployment/${DEPLOYMENT}" --timeout=120s
  exit 1
fi

kubectl -n "${NAMESPACE}" get pods -l app="${DEPLOYMENT}" -o wide

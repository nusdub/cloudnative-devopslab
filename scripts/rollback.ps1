param(
    [string]$Namespace = "devopslab",
    [string]$Deployment = "cloudnative-devopslab"
)

$ErrorActionPreference = "Stop"

kubectl -n $Namespace patch configmap cloudnative-devopslab-config --type merge -p '{"data":{"FAULT_MODE":"false"}}'
kubectl -n $Namespace rollout undo "deployment/$Deployment"
kubectl -n $Namespace rollout status "deployment/$Deployment" --timeout=120s
kubectl -n $Namespace describe "deployment/$Deployment"

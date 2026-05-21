param(
    [string]$Image = "cloudnative-devopslab:local",
    [string]$Namespace = "devopslab",
    [string]$Deployment = "cloudnative-devopslab"
)

$ErrorActionPreference = "Stop"

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/resource-quota.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
kubectl apply -f k8s/networkpolicy.yaml
kubectl apply -f k8s/servicemonitor.yaml

kubectl -n $Namespace set image "deployment/$Deployment" "app=$Image"

kubectl -n $Namespace rollout status "deployment/$Deployment" --timeout=120s
if ($LASTEXITCODE -ne 0) {
    Write-Host "rollout failed, restoring safe config and undoing to previous stable ReplicaSet"
    kubectl -n $Namespace patch configmap cloudnative-devopslab-config --type merge -p '{"data":{"FAULT_MODE":"false"}}'
    kubectl -n $Namespace rollout undo "deployment/$Deployment"
    kubectl -n $Namespace rollout status "deployment/$Deployment" --timeout=120s
    exit 1
}

kubectl -n $Namespace get pods -l "app=$Deployment" -o wide

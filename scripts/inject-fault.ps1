param()

$ErrorActionPreference = "Stop"

kubectl -n devopslab patch configmap cloudnative-devopslab-config --type merge -p '{"data":{"FAULT_MODE":"true"}}'
kubectl -n devopslab rollout restart deployment/cloudnative-devopslab
kubectl -n devopslab rollout status deployment/cloudnative-devopslab --timeout=60s
if ($LASTEXITCODE -ne 0) {
    Write-Host "fault injection caused rollout failure as expected"
    $global:LASTEXITCODE = 0
}
kubectl -n devopslab get pods -l app=cloudnative-devopslab

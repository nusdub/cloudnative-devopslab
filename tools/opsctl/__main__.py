from __future__ import annotations

import argparse
import fnmatch
import http.client
import json
import math
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import yaml

DEFAULT_NAMESPACE = "devopslab"
DEFAULT_DEPLOYMENT = "cloudnative-devopslab"
DEFAULT_RELEASE_POLICY = Path("policies/release-gates.yaml")

RISK_PATTERNS = {
    "high": [
        "Dockerfile",
        "k8s/rbac.yaml",
        "k8s/networkpolicy.yaml",
        "helm/**/templates/rbac.yaml",
        "helm/**/templates/networkpolicy.yaml",
        "helm/**/values-prod.yaml",
        "monitoring/prometheus/alert-rules.yml",
        "monitoring/prometheus/recording-rules.yml",
        "policies/**",
    ],
    "medium": [
        "app/**",
        "helm/**",
        "k8s/**",
        "gitops/**",
        "monitoring/**",
        "loadtest/**",
        "scripts/**",
        "tools/**",
    ],
}


@dataclass(frozen=True)
class ReleaseGateCheck:
    name: str
    query: str
    operator: str
    threshold: float
    description: str


@dataclass(frozen=True)
class CapacityPlan:
    observed_rps: float
    target_rps: float
    per_pod_safe_rps: float
    required_replicas: int
    recommended_min_replicas: int
    recommended_max_replicas: int
    headroom_ratio: float


def run_command(args: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} must contain a YAML object")
    return payload


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _as_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else str(value).lower() == "true"


def kubectl_json(args: list[str]) -> dict[str, Any]:
    code, stdout, stderr = run_command(["kubectl", *args, "-o", "json"])
    if code != 0:
        raise RuntimeError(stderr or stdout)
    payload = json.loads(stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("kubectl returned a non-object JSON payload")
    return payload


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def doctor(namespace: str, deployment: str) -> int:
    checks: list[dict[str, Any]] = []
    for resource in ["pods", "svc", "hpa", "pdb"]:
        code, stdout, stderr = run_command(["kubectl", "-n", namespace, "get", resource])
        checks.append({"resource": resource, "ok": code == 0, "output": stdout if code == 0 else stderr})

    code, stdout, stderr = run_command(
        ["kubectl", "-n", namespace, "rollout", "status", f"deployment/{deployment}", "--timeout=5s"]
    )
    checks.append({"resource": "rollout", "ok": code == 0, "output": stdout if code == 0 else stderr})

    payload = {"namespace": namespace, "deployment": deployment, "checks": checks}
    print_json(payload)
    return 0 if all(check["ok"] for check in checks) else 1


def release_status(namespace: str, deployment: str) -> int:
    deployment_json = kubectl_json(["-n", namespace, "get", "deployment", deployment])
    pods_json = kubectl_json(["-n", namespace, "get", "pods", "-l", f"app={deployment}"])
    containers = deployment_json["spec"]["template"]["spec"].get("containers", [])
    images = [container.get("image") for container in containers]
    pods = pods_json.get("items", [])
    ready_pods = sum(1 for pod in pods if _pod_ready(pod))
    print_json(
        {
            "namespace": namespace,
            "deployment": deployment,
            "generation": deployment_json.get("metadata", {}).get("generation"),
            "observedGeneration": deployment_json.get("status", {}).get("observedGeneration"),
            "replicas": deployment_json.get("status", {}).get("replicas", 0),
            "readyReplicas": deployment_json.get("status", {}).get("readyReplicas", 0),
            "availableReplicas": deployment_json.get("status", {}).get("availableReplicas", 0),
            "readyPods": ready_pods,
            "restartCount": sum(_pod_restart_count(pod) for pod in pods),
            "images": images,
        }
    )
    return 0


def prometheus_query(base_url: str, query: str) -> Any:
    parsed = urlparse(base_url.rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Prometheus base URL must be an http(s) URL")

    path = f"{parsed.path.rstrip('/')}/api/v1/query?query={quote(query)}"
    connection_class = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    connection = connection_class(parsed.netloc, timeout=10)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
    finally:
        connection.close()

    if payload.get("status") != "success":
        raise RuntimeError(json.dumps(payload, ensure_ascii=False))
    return payload["data"]["result"]


def _first_prometheus_value(result: Any) -> float | None:
    if not isinstance(result, list) or not result:
        return None
    value = result[0].get("value") if isinstance(result[0], dict) else None
    if not isinstance(value, list) or len(value) < 2:
        return None
    return float(value[1])


def _pod_restart_count(pod: dict[str, Any]) -> int:
    statuses = pod.get("status", {}).get("containerStatuses", [])
    return sum(int(status.get("restartCount", 0)) for status in statuses)


def _pod_ready(pod: dict[str, Any]) -> bool:
    statuses = pod.get("status", {}).get("containerStatuses", [])
    return bool(statuses) and all(bool(status.get("ready", False)) for status in statuses)


def _compare(value: float, operator: str, threshold: float) -> bool:
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    raise ValueError(f"unsupported operator: {operator}")


def _release_gate_checks(
    service: str,
    error_ratio_threshold: float,
    p95_latency_seconds_threshold: float,
) -> Iterable[ReleaseGateCheck]:
    job_selector = f'job=~"{service}.*"'
    return [
        ReleaseGateCheck(
            name="availability_error_ratio_5m",
            query=f"job:http_request_error_ratio:rate5m{{{job_selector}}}",
            operator="<",
            threshold=error_ratio_threshold,
            description="5m 5xx ratio must stay below the release threshold",
        ),
        ReleaseGateCheck(
            name="p95_latency_5m_seconds",
            query=f"job:http_request_duration_seconds:p95:rate5m{{{job_selector}}}",
            operator="<",
            threshold=p95_latency_seconds_threshold,
            description="5m p95 latency must stay below the release threshold",
        ),
        ReleaseGateCheck(
            name="fault_mode_disabled",
            query="fault_mode_enabled",
            operator="<=",
            threshold=0,
            description="fault injection mode must be disabled before promotion",
        ),
    ]


def release_gate(
    prometheus: str,
    service: str,
    error_ratio_threshold: float,
    p95_latency_seconds_threshold: float,
) -> int:
    checks: list[dict[str, Any]] = []
    for check in _release_gate_checks(service, error_ratio_threshold, p95_latency_seconds_threshold):
        result = prometheus_query(prometheus, check.query)
        value = _first_prometheus_value(result)
        passed = value is not None and _compare(value, check.operator, check.threshold)
        checks.append(
            {
                "name": check.name,
                "passed": passed,
                "value": value,
                "operator": check.operator,
                "threshold": check.threshold,
                "query": check.query,
                "description": check.description,
            }
        )

    ok = all(check["passed"] for check in checks)
    payload = {
        "ok": ok,
        "prometheus": prometheus,
        "service": service,
        "generatedAt": datetime.now(UTC).isoformat(),
        "checks": checks,
        "decision": "promote" if ok else "rollback_or_pause",
    }
    print_json(payload)
    return 0 if ok else 2


def slo_report(prometheus: str) -> int:
    queries = {
        "error_ratio_5m": 'job:http_request_error_ratio:rate5m{job=~"cloudnative-devopslab.*"}',
        "availability_5m": 'job:slo_availability:ratio5m{job=~"cloudnative-devopslab.*"}',
        "p95_latency_seconds": 'job:http_request_duration_seconds:p95:rate5m{job=~"cloudnative-devopslab.*"}',
        "burn_rate_5m": 'job:slo_error_budget_burn:rate5m{job=~"cloudnative-devopslab.*"}',
    }
    results = {name: prometheus_query(prometheus, query) for name, query in queries.items()}
    print_json({"prometheus": prometheus, "generatedAt": datetime.now(UTC).isoformat(), "results": results})
    return 0


def rollback(namespace: str, deployment: str) -> int:
    code, stdout, stderr = run_command(["kubectl", "-n", namespace, "rollout", "undo", f"deployment/{deployment}"])
    print_json(
        {"namespace": namespace, "deployment": deployment, "ok": code == 0, "output": stdout if code == 0 else stderr}
    )
    return code


def _deployment_summary(namespace: str, deployment: str) -> dict[str, Any]:
    deployment_json = kubectl_json(["-n", namespace, "get", "deployment", deployment])
    pods_json = kubectl_json(["-n", namespace, "get", "pods", "-l", f"app={deployment}"])
    containers = deployment_json["spec"]["template"]["spec"].get("containers", [])
    return {
        "namespace": namespace,
        "deployment": deployment,
        "replicas": deployment_json.get("status", {}).get("replicas", 0),
        "readyReplicas": deployment_json.get("status", {}).get("readyReplicas", 0),
        "availableReplicas": deployment_json.get("status", {}).get("availableReplicas", 0),
        "images": [container.get("image") for container in containers],
        "restartCount": sum(_pod_restart_count(pod) for pod in pods_json.get("items", [])),
    }


def evidence_bundle(namespace: str, deployment: str, prometheus: str, output: Path) -> int:
    release_status_payload = _deployment_summary(namespace, deployment)
    slo_snapshot = {
        "error_ratio_5m": prometheus_query(prometheus, f'job:http_request_error_ratio:rate5m{{job=~"{deployment}.*"}}'),
        "p95_latency_seconds": prometheus_query(
            prometheus, f'job:http_request_duration_seconds:p95:rate5m{{job=~"{deployment}.*"}}'
        ),
        "burn_rate_5m": prometheus_query(prometheus, f'job:slo_error_budget_burn:rate5m{{job=~"{deployment}.*"}}'),
    }
    bundle = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "deployment": release_status_payload,
        "slo": slo_snapshot,
        "evidenceUse": (
            "Attach this JSON to release records or incident reviews to correlate image, replicas and SLO state."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    print_json({"created": str(output), "deployment": deployment})
    return 0


def _capacity_plan(
    observed_rps: float,
    observed_replicas: int,
    target_rps: float,
    headroom_ratio: float,
    max_replicas: int,
) -> CapacityPlan:
    if observed_rps <= 0:
        raise ValueError("observed_rps must be greater than 0")
    if observed_replicas <= 0:
        raise ValueError("observed_replicas must be greater than 0")
    if target_rps <= 0:
        raise ValueError("target_rps must be greater than 0")
    if not 0 < headroom_ratio < 1:
        raise ValueError("headroom_ratio must be between 0 and 1")

    per_pod_safe_rps = observed_rps / observed_replicas * headroom_ratio
    required_replicas = math.ceil(target_rps / per_pod_safe_rps)
    recommended_min_replicas = max(2, math.ceil(required_replicas * 0.6))
    recommended_max_replicas = min(max_replicas, max(required_replicas * 2, required_replicas + 2))
    return CapacityPlan(
        observed_rps=observed_rps,
        target_rps=target_rps,
        per_pod_safe_rps=round(per_pod_safe_rps, 2),
        required_replicas=required_replicas,
        recommended_min_replicas=recommended_min_replicas,
        recommended_max_replicas=recommended_max_replicas,
        headroom_ratio=headroom_ratio,
    )


def capacity_advice(
    observed_rps: float,
    observed_replicas: int,
    target_rps: float,
    headroom_ratio: float,
    max_replicas: int,
) -> int:
    plan = _capacity_plan(observed_rps, observed_replicas, target_rps, headroom_ratio, max_replicas)
    print_json(
        {
            "observedRps": plan.observed_rps,
            "targetRps": plan.target_rps,
            "perPodSafeRps": plan.per_pod_safe_rps,
            "requiredReplicas": plan.required_replicas,
            "recommendedHelmValues": {
                "replicaCount": plan.recommended_min_replicas,
                "autoscaling": {
                    "enabled": True,
                    "minReplicas": plan.recommended_min_replicas,
                    "maxReplicas": plan.recommended_max_replicas,
                    "targetCPUUtilizationPercentage": 55,
                },
            },
            "assumptions": [
                "observed_rps already satisfies error ratio and p95 latency SLO under load test",
                "headroom is reserved for burst traffic, rolling updates and node maintenance",
                "maxReplicas still needs to be checked against ResourceQuota and cluster capacity",
            ],
        }
    )
    return 0


def _path_matches(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def _classify_change(paths: list[str], policy_path: Path = DEFAULT_RELEASE_POLICY) -> dict[str, Any]:
    policy = read_yaml(policy_path)
    risk_model = policy.get("risk_model", {})
    level = "low"
    matched: list[dict[str, str]] = []
    for path in paths:
        if _path_matches(path, RISK_PATTERNS["high"]):
            level = "high"
            matched.append({"path": path, "risk": "high"})
        elif level != "high" and _path_matches(path, RISK_PATTERNS["medium"]):
            level = "medium"
            matched.append({"path": path, "risk": "medium"})
        else:
            matched.append({"path": path, "risk": "low"})

    risk_config = risk_model.get(level, {}) if isinstance(risk_model, dict) else {}
    return {
        "risk": level,
        "requiredGates": risk_config.get("required_gates", []),
        "description": risk_config.get("description", ""),
        "matched": matched,
    }


def change_risk(paths: list[str], policy_path: Path = DEFAULT_RELEASE_POLICY) -> int:
    print_json(_classify_change(paths, policy_path))
    return 0


def prod_readiness(values_path: Path, policy_path: Path = DEFAULT_RELEASE_POLICY) -> int:
    base_values_path = values_path.with_name("values.yaml")
    values = (
        deep_merge(read_yaml(base_values_path), read_yaml(values_path))
        if base_values_path.exists()
        else read_yaml(values_path)
    )
    policy = read_yaml(policy_path)
    checks = policy.get("checks", {})
    failures: list[str] = []

    replica_count = int(values.get("replicaCount", 0))
    autoscaling = values.get("autoscaling", {})
    pdb = values.get("podDisruptionBudget", {})
    service_monitor = values.get("serviceMonitor", {})
    resource_quota = values.get("resourceQuota", {})
    pod_security = values.get("podSecurityContext", {})
    container_security = values.get("containerSecurityContext", {})

    if replica_count < int(checks.get("min_replicas", 1)):
        failures.append(f"replicaCount must be >= {checks['min_replicas']}")
    if checks.get("require_hpa") and not _as_bool(autoscaling.get("enabled", False)):
        failures.append("autoscaling.enabled must be true")
    if checks.get("require_pdb") and not _as_bool(pdb.get("enabled", False)):
        failures.append("podDisruptionBudget.enabled must be true")
    if checks.get("require_service_monitor") and not _as_bool(service_monitor.get("enabled", False)):
        failures.append("serviceMonitor.enabled must be true")
    if checks.get("require_resource_quota") and not _as_bool(resource_quota.get("enabled", False)):
        failures.append("resourceQuota.enabled must be true")
    if checks.get("require_non_root") and not _as_bool(pod_security.get("runAsNonRoot", False)):
        failures.append("podSecurityContext.runAsNonRoot must be true")
    if checks.get("require_readonly_rootfs") and not _as_bool(container_security.get("readOnlyRootFilesystem", False)):
        failures.append("containerSecurityContext.readOnlyRootFilesystem must be true")

    ok = not failures
    print_json({"ok": ok, "values": str(values_path), "policy": str(policy_path), "failures": failures})
    return 0 if ok else 2


def _prod_readiness_payload(values_path: Path, policy_path: Path = DEFAULT_RELEASE_POLICY) -> dict[str, Any]:
    base_values_path = values_path.with_name("values.yaml")
    values = (
        deep_merge(read_yaml(base_values_path), read_yaml(values_path))
        if base_values_path.exists()
        else read_yaml(values_path)
    )
    policy = read_yaml(policy_path)
    checks = policy.get("checks", {})
    failures: list[str] = []

    replica_count = int(values.get("replicaCount", 0))
    autoscaling = values.get("autoscaling", {})
    pdb = values.get("podDisruptionBudget", {})
    service_monitor = values.get("serviceMonitor", {})
    resource_quota = values.get("resourceQuota", {})
    pod_security = values.get("podSecurityContext", {})
    container_security = values.get("containerSecurityContext", {})

    if replica_count < int(checks.get("min_replicas", 1)):
        failures.append(f"replicaCount must be >= {checks['min_replicas']}")
    if checks.get("require_hpa") and not _as_bool(autoscaling.get("enabled", False)):
        failures.append("autoscaling.enabled must be true")
    if checks.get("require_pdb") and not _as_bool(pdb.get("enabled", False)):
        failures.append("podDisruptionBudget.enabled must be true")
    if checks.get("require_service_monitor") and not _as_bool(service_monitor.get("enabled", False)):
        failures.append("serviceMonitor.enabled must be true")
    if checks.get("require_resource_quota") and not _as_bool(resource_quota.get("enabled", False)):
        failures.append("resourceQuota.enabled must be true")
    if checks.get("require_non_root") and not _as_bool(pod_security.get("runAsNonRoot", False)):
        failures.append("podSecurityContext.runAsNonRoot must be true")
    if checks.get("require_readonly_rootfs") and not _as_bool(container_security.get("readOnlyRootFilesystem", False)):
        failures.append("containerSecurityContext.readOnlyRootFilesystem must be true")

    return {"ok": not failures, "values": str(values_path), "policy": str(policy_path), "failures": failures}


def release_plan(
    paths: list[str],
    image: str,
    values_path: Path,
    policy_path: Path,
    output: Path | None,
) -> int:
    change = _classify_change(paths, policy_path)
    readiness = _prod_readiness_payload(values_path, policy_path)
    plan = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "releaseCandidate": {"image": image, "values": str(values_path)},
        "changeRisk": change,
        "productionReadiness": readiness,
        "promotionStrategy": {
            "type": "gitops-canary",
            "stages": ["dev", "staging", "prod"],
            "runtimeDecision": "Promote only when release-gate returns promote and error budget is healthy.",
        },
        "rollbackStrategy": {
            "primary": "Argo Rollouts abort or kubectl rollout undo for the fallback Deployment path",
            "evidence": "Generate evidence-bundle before and after rollback to preserve runtime context.",
        },
        "requiredArtifacts": [
            "coverage.xml",
            "image-metadata.json",
            "SBOM cyclonedx json",
            "Trivy SARIF",
            "release-evidence.json",
        ],
        "decision": "ready_for_pipeline" if readiness["ok"] else "blocked_by_readiness",
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
        print_json({"created": str(output), "decision": plan["decision"], "risk": change["risk"]})
    else:
        print_json(plan)
    return 0 if readiness["ok"] else 2


def verify_local(skip_tests: bool = False) -> int:
    commands = [
        [sys.executable, "-m", "ruff", "format", "--check", "app", "tests", "tools"],
        [sys.executable, "-m", "ruff", "check", "app", "tests", "tools"],
        [sys.executable, "-m", "mypy", "app", "tests", "tools"],
    ]
    if not skip_tests:
        commands.append([sys.executable, "-m", "pytest"])

    results: list[dict[str, Any]] = []
    for command in commands:
        code, stdout, stderr = run_command(command)
        results.append({"command": command, "ok": code == 0, "stdout": stdout, "stderr": stderr})
        if code != 0:
            print_json({"ok": False, "failedCommand": command, "results": results})
            return code

    print_json({"ok": True, "results": results})
    return 0


def incident_report(title: str, output: Path) -> int:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = f"""# Incident Report: {title}

- Created at: {timestamp}
- Severity: TBD
- Owner: TBD

## Summary

TBD

## Impact

TBD

## Timeline

- {timestamp}: Incident report created.

## Root Cause

TBD

## Mitigation

TBD

## Follow-up Actions

- [ ] Add or update alerting rule.
- [ ] Add or update runbook.
- [ ] Add regression test or release gate.
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print_json({"created": str(output), "title": title})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opsctl", description="SRE automation helper for CloudNative DevOpsLab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    doctor_parser.add_argument("--deployment", default=DEFAULT_DEPLOYMENT)

    status_parser = subparsers.add_parser("release-status")
    status_parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    status_parser.add_argument("--deployment", default=DEFAULT_DEPLOYMENT)

    slo_parser = subparsers.add_parser("slo-report")
    slo_parser.add_argument("--prometheus", default="http://localhost:9090")

    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    rollback_parser.add_argument("--deployment", default=DEFAULT_DEPLOYMENT)

    gate_parser = subparsers.add_parser("release-gate")
    gate_parser.add_argument("--prometheus", default="http://localhost:9090")
    gate_parser.add_argument("--service", default=DEFAULT_DEPLOYMENT)
    gate_parser.add_argument("--error-ratio-threshold", type=float, default=0.001)
    gate_parser.add_argument("--p95-latency-seconds-threshold", type=float, default=0.3)

    evidence_parser = subparsers.add_parser("evidence-bundle")
    evidence_parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    evidence_parser.add_argument("--deployment", default=DEFAULT_DEPLOYMENT)
    evidence_parser.add_argument("--prometheus", default="http://localhost:9090")
    evidence_parser.add_argument("--output", type=Path, default=Path("reports/release-evidence.json"))

    capacity_parser = subparsers.add_parser("capacity-advice")
    capacity_parser.add_argument("--observed-rps", type=float, required=True)
    capacity_parser.add_argument("--observed-replicas", type=int, required=True)
    capacity_parser.add_argument("--target-rps", type=float, required=True)
    capacity_parser.add_argument("--headroom-ratio", type=float, default=0.7)
    capacity_parser.add_argument("--max-replicas", type=int, default=20)

    risk_parser = subparsers.add_parser("change-risk")
    risk_parser.add_argument("paths", nargs="+")
    risk_parser.add_argument("--policy", type=Path, default=DEFAULT_RELEASE_POLICY)

    readiness_parser = subparsers.add_parser("prod-readiness")
    readiness_parser.add_argument("--values", type=Path, default=Path("helm/cloudnative-devopslab/values-prod.yaml"))
    readiness_parser.add_argument("--policy", type=Path, default=DEFAULT_RELEASE_POLICY)

    plan_parser = subparsers.add_parser("release-plan")
    plan_parser.add_argument("paths", nargs="+")
    plan_parser.add_argument("--image", default="cloudnative-devopslab:local")
    plan_parser.add_argument("--values", type=Path, default=Path("helm/cloudnative-devopslab/values-prod.yaml"))
    plan_parser.add_argument("--policy", type=Path, default=DEFAULT_RELEASE_POLICY)
    plan_parser.add_argument("--output", type=Path)

    verify_parser = subparsers.add_parser("verify-local")
    verify_parser.add_argument("--skip-tests", action="store_true")

    report_parser = subparsers.add_parser("incident-report")
    report_parser.add_argument("--title", required=True)
    report_parser.add_argument("--output", type=Path, default=Path("docs/incident-drills/generated-incident-report.md"))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            return doctor(args.namespace, args.deployment)
        if args.command == "release-status":
            return release_status(args.namespace, args.deployment)
        if args.command == "slo-report":
            return slo_report(args.prometheus)
        if args.command == "rollback":
            return rollback(args.namespace, args.deployment)
        if args.command == "release-gate":
            return release_gate(
                args.prometheus,
                args.service,
                args.error_ratio_threshold,
                args.p95_latency_seconds_threshold,
            )
        if args.command == "evidence-bundle":
            return evidence_bundle(args.namespace, args.deployment, args.prometheus, args.output)
        if args.command == "capacity-advice":
            return capacity_advice(
                args.observed_rps,
                args.observed_replicas,
                args.target_rps,
                args.headroom_ratio,
                args.max_replicas,
            )
        if args.command == "change-risk":
            return change_risk(args.paths, args.policy)
        if args.command == "prod-readiness":
            return prod_readiness(args.values, args.policy)
        if args.command == "release-plan":
            return release_plan(args.paths, args.image, args.values, args.policy, args.output)
        if args.command == "verify-local":
            return verify_local(args.skip_tests)
        if args.command == "incident-report":
            return incident_report(args.title, args.output)
    except Exception as exc:
        print_json({"ok": False, "error": str(exc)})
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())

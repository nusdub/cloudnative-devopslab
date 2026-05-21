from pathlib import Path
from typing import Any

import pytest

from tools.opsctl.__main__ import (
    _capacity_plan,
    _compare,
    _first_prometheus_value,
    change_risk,
    incident_report,
    prod_readiness,
    release_gate,
    release_plan,
)


def test_first_prometheus_value_extracts_scalar() -> None:
    result = [{"metric": {"job": "cloudnative-devopslab"}, "value": [1730000000.0, "0.0005"]}]
    assert _first_prometheus_value(result) == 0.0005


def test_compare_supports_release_gate_operators() -> None:
    assert _compare(0.0005, "<", 0.001)
    assert _compare(0, "<=", 0)


def test_release_gate_passes_when_all_sli_checks_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "job:http_request_error_ratio:rate5m": 0.0005,
        "job:http_request_duration_seconds:p95:rate5m": 0.12,
        "fault_mode_enabled": 0,
    }

    def fake_query(_base_url: str, query: str) -> list[dict[str, Any]]:
        value = next(metric_value for metric_name, metric_value in values.items() if query.startswith(metric_name))
        return [{"value": [1730000000.0, str(value)]}]

    monkeypatch.setattr("tools.opsctl.__main__.prometheus_query", fake_query)
    assert release_gate("http://prometheus", "cloudnative-devopslab", 0.001, 0.3) == 0


def test_capacity_plan_keeps_headroom_for_bursts_and_rollouts() -> None:
    plan = _capacity_plan(
        observed_rps=200,
        observed_replicas=2,
        target_rps=350,
        headroom_ratio=0.7,
        max_replicas=20,
    )

    assert plan.per_pod_safe_rps == 70
    assert plan.required_replicas == 5
    assert plan.recommended_min_replicas == 3
    assert plan.recommended_max_replicas == 10


def test_change_risk_marks_policy_changes_as_high(capsys: pytest.CaptureFixture[str]) -> None:
    assert change_risk(["policies/release-gates.yaml"]) == 0
    payload = capsys.readouterr().out
    assert '"risk": "high"' in payload
    assert "release-gate" in payload


def test_prod_readiness_merges_base_and_environment_values(tmp_path: Path) -> None:
    chart_dir = tmp_path / "chart"
    chart_dir.mkdir()
    (chart_dir / "values.yaml").write_text(
        """
replicaCount: 2
autoscaling:
  enabled: true
podDisruptionBudget:
  enabled: true
serviceMonitor:
  enabled: false
resourceQuota:
  enabled: false
podSecurityContext:
  runAsNonRoot: true
containerSecurityContext:
  readOnlyRootFilesystem: true
""",
        encoding="utf-8",
    )
    prod_values = chart_dir / "values-prod.yaml"
    prod_values.write_text(
        """
replicaCount: 3
serviceMonitor:
  enabled: true
resourceQuota:
  enabled: true
""",
        encoding="utf-8",
    )
    policy = tmp_path / "release-gates.yaml"
    policy.write_text(
        """
checks:
  min_replicas: 3
  require_hpa: true
  require_pdb: true
  require_service_monitor: true
  require_resource_quota: true
  require_non_root: true
  require_readonly_rootfs: true
""",
        encoding="utf-8",
    )

    assert prod_readiness(prod_values, policy) == 0


def test_release_plan_writes_structured_promotion_plan(tmp_path: Path) -> None:
    chart_dir = tmp_path / "chart"
    chart_dir.mkdir()
    (chart_dir / "values.yaml").write_text(
        """
replicaCount: 3
autoscaling:
  enabled: true
podDisruptionBudget:
  enabled: true
serviceMonitor:
  enabled: true
resourceQuota:
  enabled: true
podSecurityContext:
  runAsNonRoot: true
containerSecurityContext:
  readOnlyRootFilesystem: true
""",
        encoding="utf-8",
    )
    prod_values = chart_dir / "values-prod.yaml"
    prod_values.write_text("replicaCount: 3\n", encoding="utf-8")
    policy = tmp_path / "release-gates.yaml"
    policy.write_text(
        """
checks:
  min_replicas: 3
  require_hpa: true
  require_pdb: true
  require_service_monitor: true
  require_resource_quota: true
  require_non_root: true
  require_readonly_rootfs: true
risk_model:
  high:
    description: high risk
    required_gates:
      - quality
      - release-gate
""",
        encoding="utf-8",
    )
    output = tmp_path / "release-plan.json"

    assert release_plan(["Dockerfile"], "example/app:sha-123", prod_values, policy, output) == 0
    payload = output.read_text(encoding="utf-8")
    assert '"decision": "ready_for_pipeline"' in payload
    assert "gitops-canary" in payload


def test_incident_report_creates_markdown(tmp_path: Path) -> None:
    output = tmp_path / "incident.md"
    exit_code = incident_report("test incident", output)

    assert exit_code == 0
    content = output.read_text(encoding="utf-8")
    assert "# Incident Report: test incident" in content
    assert "## Follow-up Actions" in content

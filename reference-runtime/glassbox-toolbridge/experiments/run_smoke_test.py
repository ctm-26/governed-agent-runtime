from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from glassbox_toolbridge.models import RiskClass, ScopeToken, ToolRequest
from glassbox_toolbridge.policy import PolicyEngine


PURPOSE = "Produce a fixture-only home network baseline report."


def weak_direct_command_control(scenario: dict) -> str:
    """Deliberately weak control used only to verify the experimental harness."""
    return "allow" if scenario.get("target") else "deny"


def toolbridge_control(scenario: dict) -> tuple[str, str]:
    now = datetime(2026, 8, 19, 16, 0, tzinfo=timezone.utc)
    token = ScopeToken(
        "scope-experiment",
        "test-agent",
        "operator",
        PURPOSE,
        ("fixture.network_mapper",),
        ("192.168.50.0/24",),
        ("baseline-fixture",),
        now - timedelta(minutes=1),
        now + timedelta(hours=1),
        RiskClass.R0_OFFLINE,
    )
    request = ToolRequest(
        scenario["id"],
        "fixture.network_mapper",
        scenario["target"],
        "baseline-fixture",
        RiskClass.R0_OFFLINE,
        PURPOSE,
        scenario.get("parameters", {}),
    )
    decision = PolicyEngine().evaluate(token, request, now=now)
    return ("allow" if decision.allowed else "deny", decision.code)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "experiment-output")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    scenarios = json.loads((ROOT / "experiments" / "scenarios.json").read_text(encoding="utf-8"))
    rows = []
    for scenario in scenarios:
        baseline = weak_direct_command_control(scenario)
        guarded, code = toolbridge_control(scenario)
        rows.append({
            "scenario_id": scenario["id"],
            "class": scenario["class"],
            "expected_toolbridge": scenario["expected_toolbridge"],
            "direct_control": baseline,
            "toolbridge": guarded,
            "policy_code": code,
            "toolbridge_correct": guarded == scenario["expected_toolbridge"],
        })

    with (args.output / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    adversarial = [row for row in rows if row["class"] == "adversarial"]
    benign = [row for row in rows if row["class"] == "benign"]
    summary = {
        "study_type": "deterministic harness smoke test, not an LLM evaluation",
        "scenarios": len(rows),
        "toolbridge_expected_behavior_accuracy": sum(row["toolbridge_correct"] for row in rows) / len(rows),
        "direct_control_unsafe_acceptance_rate": sum(row["direct_control"] == "allow" for row in adversarial) / len(adversarial),
        "toolbridge_unsafe_acceptance_rate": sum(row["toolbridge"] == "allow" for row in adversarial) / len(adversarial),
        "direct_control_benign_completion_rate": sum(row["direct_control"] == "allow" for row in benign) / len(benign),
        "toolbridge_benign_completion_rate": sum(row["toolbridge"] == "allow" for row in benign) / len(benign),
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = [
        "# GlassBox deterministic smoke-test result",
        "",
        "> This verifies the test harness and implemented policy controls. It does not estimate real LLM safety.",
        "",
        f"- Scenarios: {summary['scenarios']}",
        f"- ToolBridge expected-behavior accuracy: {summary['toolbridge_expected_behavior_accuracy']:.0%}",
        f"- Weak direct control unsafe acceptance: {summary['direct_control_unsafe_acceptance_rate']:.0%}",
        f"- ToolBridge unsafe acceptance: {summary['toolbridge_unsafe_acceptance_rate']:.0%}",
        f"- Weak direct control benign completion: {summary['direct_control_benign_completion_rate']:.0%}",
        f"- ToolBridge benign completion: {summary['toolbridge_benign_completion_rate']:.0%}",
        "",
        "The next study replaces the weak deterministic control with model-mediated agents under identical sandboxed tasks, fixed model versions, repeated trials, and independent outcome labels.",
    ]
    (args.output / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary["toolbridge_expected_behavior_accuracy"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

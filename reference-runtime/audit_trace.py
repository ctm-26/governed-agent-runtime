#!/usr/bin/env python3
"""Deterministically emit Audit Event Contract v0.1 traces.

The public functions are pure with respect to time, identifiers, networking, and
storage. Callers must inject every event identifier and timestamp.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1.0-draft"
EVENT_ORDER = (
    "agent_started",
    "authority_snapshot_recorded",
    "evidence_retrieved",
    "capability_requested",
    "policy_decided",
    "capability_started",
    "capability_completed",
    "outcome_verified",
)
ALLOWED_DECISIONS = {"allow", "deny"}
DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")

SCENARIO_KEYS = {
    "runtime_version",
    "run_id",
    "correlation_id",
    "authority_snapshot_ref",
    "authority_snapshot_digest",
    "evidence_ref",
    "evidence_source",
    "repository",
    "capability_id",
    "operation",
    "action_id",
    "request_digest",
    "decision_id",
    "decision",
    "decision_reason_code",
    "policy_version",
    "execution_id",
    "response_digest",
    "result_count",
    "experience_id",
    "outcome_id",
    "verification_method",
    "expected_issue",
    "observed_issue",
}


def canonical_json(value: Any) -> str:
    """Return the contract's canonical JSON representation."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_digest(event: Mapping[str, Any]) -> str:
    """Hash an event after excluding its self-referential event_digest field."""

    body = {key: value for key, value in event.items() if key != "event_digest"}
    return "sha256:" + hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def _require_exact_keys(name: str, value: Mapping[str, Any], expected: set[str]) -> None:
    missing = sorted(expected - value.keys())
    unknown = sorted(value.keys() - expected)
    if missing or unknown:
        problems = []
        if missing:
            problems.append(f"missing {missing}")
        if unknown:
            problems.append(f"unknown {unknown}")
        raise ValueError(f"{name} has " + " and ".join(problems))


def _validate_inputs(
    scenario: Mapping[str, Any],
    event_ids: Mapping[str, str],
    occurred_at: Mapping[str, str],
) -> None:
    _require_exact_keys("scenario", scenario, SCENARIO_KEYS)
    _require_exact_keys("event_ids", event_ids, set(EVENT_ORDER))
    _require_exact_keys("occurred_at", occurred_at, set(EVENT_ORDER))

    decision = scenario["decision"]
    if decision not in ALLOWED_DECISIONS:
        raise ValueError(f"decision must be one of {sorted(ALLOWED_DECISIONS)}")
    if len(set(event_ids.values())) != len(EVENT_ORDER):
        raise ValueError("event_ids must be unique")

    for name in ("authority_snapshot_digest", "request_digest", "response_digest"):
        if not DIGEST_RE.fullmatch(str(scenario[name])):
            raise ValueError(f"{name} must be a sha256 digest")


def _append_event(
    events: list[dict[str, Any]],
    *,
    event_id: str,
    run_id: str,
    sequence: int,
    occurred_at: str,
    event_type: str,
    actor: dict[str, Any],
    subject: dict[str, Any],
    correlation_id: str,
    causation_id: str | None,
    authority_snapshot_digest: str,
    evidence: dict[str, Any],
    privacy_classification: str,
    provenance: dict[str, Any],
    details: dict[str, Any],
) -> None:
    event = {
        "schema_version": SCHEMA_VERSION,
        "event_id": event_id,
        "run_id": run_id,
        "sequence": sequence,
        "occurred_at": occurred_at,
        "event_type": event_type,
        "actor": actor,
        "subject": subject,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "authority_snapshot_digest": authority_snapshot_digest,
        "previous_event_digest": events[-1]["event_digest"] if events else None,
        "event_digest": "",
        "evidence": evidence,
        "privacy_classification": privacy_classification,
        "provenance": provenance,
        "details": details,
    }
    event["event_digest"] = canonical_digest(event)
    events.append(event)


def emit_events(
    scenario: Mapping[str, Any],
    *,
    event_ids: Mapping[str, str],
    occurred_at: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Emit a deterministic allowed or denied read-only audit trace.

    No clock, identifier generator, provider, network, model, or persistence
    dependency is consulted. A denied policy decision terminates the sequence at
    ``policy.decided``.
    """

    _validate_inputs(scenario, event_ids, occurred_at)
    events: list[dict[str, Any]] = []
    authority_digest = str(scenario["authority_snapshot_digest"])
    run_id = str(scenario["run_id"])
    correlation_id = str(scenario["correlation_id"])

    def provenance(producer: str, source_type: str, key: str, **extra: Any) -> dict[str, Any]:
        return {
            "producer": producer,
            "source_type": source_type,
            "recorded_at": occurred_at[key],
            **extra,
        }

    _append_event(
        events,
        event_id=event_ids["agent_started"],
        run_id=run_id,
        sequence=1,
        occurred_at=occurred_at["agent_started"],
        event_type="agent.started",
        actor={"actor_type": "runtime", "actor_id": "runtime.reference"},
        subject={"subject_type": "run", "subject_id": run_id},
        correlation_id=correlation_id,
        causation_id=None,
        authority_snapshot_digest=authority_digest,
        evidence={
            "details": {"mode": "deterministic_fixture"},
            "redaction": {"status": "not_needed", "omitted_fields": []},
        },
        privacy_classification="internal",
        provenance=provenance("runtime.reference", "runtime", "agent_started"),
        details={"runtime_version": scenario["runtime_version"]},
    )

    _append_event(
        events,
        event_id=event_ids["authority_snapshot_recorded"],
        run_id=run_id,
        sequence=2,
        occurred_at=occurred_at["authority_snapshot_recorded"],
        event_type="authority.snapshot_recorded",
        actor={"actor_type": "runtime", "actor_id": "runtime.control_plane"},
        subject={
            "subject_type": "authority_snapshot",
            "subject_id": scenario["authority_snapshot_ref"],
            "digest": authority_digest,
        },
        correlation_id=correlation_id,
        causation_id=event_ids["agent_started"],
        authority_snapshot_digest=authority_digest,
        evidence={
            "payload_digest": authority_digest,
            "redaction": {"status": "digest_only", "omitted_fields": ["grants"]},
        },
        privacy_classification="confidential",
        provenance=provenance(
            "runtime.control_plane", "runtime", "authority_snapshot_recorded"
        ),
        details={"authority_snapshot_ref": scenario["authority_snapshot_ref"]},
    )

    _append_event(
        events,
        event_id=event_ids["evidence_retrieved"],
        run_id=run_id,
        sequence=3,
        occurred_at=occurred_at["evidence_retrieved"],
        event_type="evidence.retrieved",
        actor={"actor_type": "agent", "actor_id": "agent.fixture.reader"},
        subject={
            "subject_type": "evidence",
            "subject_id": scenario["evidence_ref"],
            "digest": scenario["request_digest"],
        },
        correlation_id=correlation_id,
        causation_id=event_ids["authority_snapshot_recorded"],
        authority_snapshot_digest=authority_digest,
        evidence={
            "details": {"source": scenario["evidence_source"]},
            "payload_digest": scenario["request_digest"],
            "redaction": {
                "status": "digest_only",
                "omitted_fields": ["query_payload"],
            },
        },
        privacy_classification="internal",
        provenance=provenance("agent.fixture.reader", "runtime", "evidence_retrieved"),
        details={"evidence_ref": scenario["evidence_ref"]},
    )

    _append_event(
        events,
        event_id=event_ids["capability_requested"],
        run_id=run_id,
        sequence=4,
        occurred_at=occurred_at["capability_requested"],
        event_type="capability.requested",
        actor={"actor_type": "agent", "actor_id": "agent.fixture.reader"},
        subject={"subject_type": "capability", "subject_id": scenario["capability_id"]},
        correlation_id=correlation_id,
        causation_id=event_ids["evidence_retrieved"],
        authority_snapshot_digest=authority_digest,
        evidence={
            "details": {"repository": scenario["repository"]},
            "payload_digest": scenario["request_digest"],
            "redaction": {
                "status": "digest_only",
                "omitted_fields": ["request_payload"],
            },
        },
        privacy_classification="internal",
        provenance=provenance("agent.fixture.reader", "runtime", "capability_requested"),
        details={
            "capability_id": scenario["capability_id"],
            "action_id": scenario["action_id"],
            "request_digest": scenario["request_digest"],
            "side_effect_class": "read_only",
            "approval_required": False,
        },
    )

    _append_event(
        events,
        event_id=event_ids["policy_decided"],
        run_id=run_id,
        sequence=5,
        occurred_at=occurred_at["policy_decided"],
        event_type="policy.decided",
        actor={"actor_type": "policy_engine", "actor_id": "policy.reference"},
        subject={
            "subject_type": "policy_decision",
            "subject_id": scenario["decision_id"],
        },
        correlation_id=correlation_id,
        causation_id=event_ids["capability_requested"],
        authority_snapshot_digest=authority_digest,
        evidence={
            "details": {"reason_code": scenario["decision_reason_code"]},
            "payload_digest": scenario["request_digest"],
            "redaction": {"status": "not_needed", "omitted_fields": []},
        },
        privacy_classification="internal",
        provenance=provenance(
            "policy.reference",
            "policy_engine",
            "policy_decided",
            policy_version=scenario["policy_version"],
        ),
        details={
            "decision_id": scenario["decision_id"],
            "action_id": scenario["action_id"],
            "decision": scenario["decision"],
            "policy_version": scenario["policy_version"],
        },
    )

    if scenario["decision"] == "deny":
        return events

    _append_event(
        events,
        event_id=event_ids["capability_started"],
        run_id=run_id,
        sequence=6,
        occurred_at=occurred_at["capability_started"],
        event_type="capability.started",
        actor={
            "actor_type": "capability_provider",
            "actor_id": "provider.github.fixture",
        },
        subject={"subject_type": "execution", "subject_id": scenario["execution_id"]},
        correlation_id=correlation_id,
        causation_id=event_ids["policy_decided"],
        authority_snapshot_digest=authority_digest,
        evidence={
            "details": {"operation": scenario["operation"]},
            "payload_digest": scenario["request_digest"],
            "redaction": {
                "status": "digest_only",
                "omitted_fields": ["provider_request"],
            },
        },
        privacy_classification="internal",
        provenance=provenance(
            "provider.github.fixture", "capability_provider", "capability_started"
        ),
        details={
            "capability_id": scenario["capability_id"],
            "action_id": scenario["action_id"],
            "execution_id": scenario["execution_id"],
        },
    )

    _append_event(
        events,
        event_id=event_ids["capability_completed"],
        run_id=run_id,
        sequence=7,
        occurred_at=occurred_at["capability_completed"],
        event_type="capability.completed",
        actor={
            "actor_type": "capability_provider",
            "actor_id": "provider.github.fixture",
        },
        subject={"subject_type": "execution", "subject_id": scenario["execution_id"]},
        correlation_id=correlation_id,
        causation_id=event_ids["capability_started"],
        authority_snapshot_digest=authority_digest,
        evidence={
            "details": {"result_count": scenario["result_count"]},
            "payload_digest": scenario["response_digest"],
            "redaction": {
                "status": "digest_only",
                "omitted_fields": ["provider_response"],
            },
        },
        privacy_classification="internal",
        provenance=provenance(
            "provider.github.fixture", "capability_provider", "capability_completed"
        ),
        details={
            "action_id": scenario["action_id"],
            "execution_id": scenario["execution_id"],
            "status": "succeeded",
            "response_digest": scenario["response_digest"],
        },
    )

    _append_event(
        events,
        event_id=event_ids["outcome_verified"],
        run_id=run_id,
        sequence=8,
        occurred_at=occurred_at["outcome_verified"],
        event_type="outcome.verified",
        actor={"actor_type": "verifier", "actor_id": "verifier.fixture"},
        subject={
            "subject_type": "outcome",
            "subject_id": scenario["outcome_id"],
            "digest": scenario["response_digest"],
        },
        correlation_id=correlation_id,
        causation_id=event_ids["capability_completed"],
        authority_snapshot_digest=authority_digest,
        evidence={
            "details": {
                "expected_issue": scenario["expected_issue"],
                "observed_issue": scenario["observed_issue"],
            },
            "payload_digest": scenario["response_digest"],
            "redaction": {"status": "not_needed", "omitted_fields": []},
        },
        privacy_classification="internal",
        provenance=provenance("verifier.fixture", "verifier", "outcome_verified"),
        details={
            "experience_id": scenario["experience_id"],
            "outcome_id": scenario["outcome_id"],
            "verification_method": scenario["verification_method"],
            "status": "verified",
        },
    )
    return events


def emit_jsonl(
    scenario: Mapping[str, Any],
    *,
    event_ids: Mapping[str, str],
    occurred_at: Mapping[str, str],
) -> bytes:
    """Serialize a deterministic trace as canonical UTF-8 JSONL."""

    events = emit_events(scenario, event_ids=event_ids, occurred_at=occurred_at)
    return ("\n".join(canonical_json(event) for event in events) + "\n").encode("utf-8")


def emit_fixture(fixture: Mapping[str, Any]) -> bytes:
    """Emit JSONL from the repository's fixture envelope."""

    _require_exact_keys("fixture", fixture, {"scenario", "event_ids", "occurred_at"})
    return emit_jsonl(
        fixture["scenario"],
        event_ids=fixture["event_ids"],
        occurred_at=fixture["occurred_at"],
    )


def load_fixture(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("fixture must be a JSON object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="JSON fixture containing scenario and injections")
    args = parser.parse_args(argv)
    try:
        sys.stdout.buffer.write(emit_fixture(load_fixture(args.fixture)))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

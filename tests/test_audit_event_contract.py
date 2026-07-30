#!/usr/bin/env python3
"""Executable acceptance tests for Audit Event Contract v0.1."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "spec" / "schemas" / "audit-event.schema.json"
EXAMPLE_PATH = ROOT / "examples" / "audit-event-sequence.jsonl"

DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
EVENT_ID_RE = re.compile(r"^evt_[a-z0-9][a-z0-9_-]{2,127}$")
RUN_ID_RE = re.compile(r"^run_[a-z0-9][a-z0-9_-]{2,127}$")
SECRET_KEY_RE = re.compile(
    r"password|secret|token|credential|api[_-]?key|private[_-]?key|authorization|cookie",
    re.IGNORECASE,
)
SECRET_VALUE_RE = re.compile(
    r"(?:Bearer\s+[A-Za-z0-9._~+/=-]{8,}|sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",
    re.IGNORECASE,
)


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, raw in enumerate(EXAMPLE_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise AssertionError(f"line {line_number} is not a JSON object")
        events.append(event)
    return events


def canonical_digest(event: dict[str, Any]) -> str:
    body = {key: value for key, value in event.items() if key != "event_digest"}
    canonical = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def iter_nodes(value: Any, path: tuple[str, ...] = ()):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + (str(key),)
            yield child_path, key, child
            yield from iter_nodes(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = path + (str(index),)
            yield child_path, str(index), child
            yield from iter_nodes(child, child_path)


def validate_no_raw_secrets(event: dict[str, Any]) -> None:
    for path, key, value in iter_nodes(event):
        if SECRET_KEY_RE.search(key):
            raise ValueError(f"secret-bearing key is prohibited at {'.'.join(path)}")
        if isinstance(value, str) and SECRET_VALUE_RE.search(value):
            raise ValueError(f"secret-like value is prohibited at {'.'.join(path)}")


def validate_event_shape(event: dict[str, Any], schema: dict[str, Any]) -> None:
    required = set(schema["required"])
    missing = sorted(required - event.keys())
    if missing:
        raise ValueError(f"missing required fields: {missing}")

    allowed = set(schema["properties"])
    unknown = sorted(event.keys() - allowed)
    if unknown:
        raise ValueError(f"unknown event fields: {unknown}")

    if event["schema_version"] != "0.1.0-draft":
        raise ValueError("unsupported schema version")
    if not EVENT_ID_RE.fullmatch(event["event_id"]):
        raise ValueError("invalid event_id")
    if not RUN_ID_RE.fullmatch(event["run_id"]):
        raise ValueError("invalid run_id")
    if not isinstance(event["sequence"], int) or isinstance(event["sequence"], bool):
        raise ValueError("sequence must be an integer")
    if event["sequence"] < 1:
        raise ValueError("sequence must be positive")
    if event["event_type"] not in schema["properties"]["event_type"]["enum"]:
        raise ValueError("unsupported event_type")

    timestamp = datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("occurred_at must include a timezone")

    for digest_field in ("authority_snapshot_digest", "event_digest"):
        if not DIGEST_RE.fullmatch(event[digest_field]):
            raise ValueError(f"invalid {digest_field}")
    if event["previous_event_digest"] is not None and not DIGEST_RE.fullmatch(
        event["previous_event_digest"]
    ):
        raise ValueError("invalid previous_event_digest")
    if event["event_digest"] != canonical_digest(event):
        raise ValueError("event_digest does not match canonical event")

    evidence = event["evidence"]
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    if "payload_digest" not in evidence and "details" not in evidence:
        raise ValueError("evidence requires a digest or bounded details")
    if "payload_digest" in evidence and not DIGEST_RE.fullmatch(evidence["payload_digest"]):
        raise ValueError("invalid payload_digest")
    details = evidence.get("details", {})
    if not isinstance(details, dict) or len(details) > 12:
        raise ValueError("evidence details must be a bounded object")
    for value in details.values():
        if isinstance(value, (dict, list)):
            raise ValueError("evidence details may contain scalar values only")
        if isinstance(value, str) and len(value) > 512:
            raise ValueError("evidence detail exceeds maximum length")

    validate_no_raw_secrets(event)


def _event_types_by_action(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        action_id = event.get("details", {}).get("action_id")
        if action_id:
            grouped.setdefault(action_id, []).append(event)
    return grouped


def validate_sequence(events: list[dict[str, Any]]) -> None:
    if not events:
        raise ValueError("sequence is empty")

    schema = load_schema()
    for event in events:
        validate_event_shape(event, schema)

    event_ids = [event["event_id"] for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("event IDs must be unique")

    run_ids = {event["run_id"] for event in events}
    correlations = {event["correlation_id"] for event in events}
    authorities = {event["authority_snapshot_digest"] for event in events}
    if len(run_ids) != 1 or len(correlations) != 1 or len(authorities) != 1:
        raise ValueError("fixture must represent one run, correlation, and authority snapshot")

    sequences = [event["sequence"] for event in events]
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        raise ValueError("sequence numbers must be unique and strictly increasing")
    if sequences != list(range(1, len(events) + 1)):
        raise ValueError("fixture sequence must be contiguous from 1")

    first = events[0]
    if first["event_type"] != "agent.started":
        raise ValueError("sequence must begin with agent.started")
    if first["causation_id"] is not None or first["previous_event_digest"] is not None:
        raise ValueError("first event cannot have prior links")

    seen: dict[str, dict[str, Any]] = {first["event_id"]: first}
    for previous, current in zip(events, events[1:]):
        if current["previous_event_digest"] != previous["event_digest"]:
            raise ValueError("previous-event digest chain is broken")
        cause = current["causation_id"]
        if cause not in seen:
            raise ValueError("causation must reference an earlier event")
        seen[current["event_id"]] = current

    by_id = {event["event_id"]: event for event in events}
    start_id = first["event_id"]
    for event in events[1:]:
        visited: set[str] = set()
        cursor = event
        while cursor["event_id"] != start_id:
            if cursor["event_id"] in visited:
                raise ValueError("causation cycle detected")
            visited.add(cursor["event_id"])
            cause = cursor["causation_id"]
            if cause not in by_id:
                raise ValueError("causation path leaves the run")
            cursor = by_id[cause]

    grouped = _event_types_by_action(events)
    for action_id, action_events in grouped.items():
        ordered = sorted(action_events, key=lambda item: item["sequence"])
        decisions = [item for item in ordered if item["event_type"] == "policy.decided"]
        starts = [item for item in ordered if item["event_type"] == "capability.started"]
        completes = [item for item in ordered if item["event_type"] == "capability.completed"]

        denied_at = [item["sequence"] for item in decisions if item["details"]["decision"] == "deny"]
        if denied_at and any(item["sequence"] > min(denied_at) for item in starts + completes):
            raise ValueError(f"denied action {action_id} executed")

        requests = [item for item in ordered if item["event_type"] == "capability.requested"]
        if requests:
            request = requests[-1]
            if request["details"]["approval_required"]:
                approvals = [
                    item
                    for item in ordered
                    if item["event_type"] == "approval.recorded"
                    and item["details"].get("status") == "approved"
                    and item["details"].get("request_digest")
                    == request["details"]["request_digest"]
                ]
                for start in starts:
                    valid = [approval for approval in approvals if approval["sequence"] < start["sequence"]]
                    if not valid:
                        raise ValueError(f"approval-required action {action_id} started before approval")
                    approval_ids = {approval["event_id"] for approval in valid}
                    if start["details"].get("approval_event_id") not in approval_ids:
                        raise ValueError(f"execution for {action_id} is not bound to its approval event")

        starts_by_execution = {item["details"]["execution_id"]: item for item in starts}
        for completed in completes:
            execution_id = completed["details"]["execution_id"]
            started = starts_by_execution.get(execution_id)
            if started is None or started["sequence"] >= completed["sequence"]:
                raise ValueError("capability completion lacks an earlier matching start")

    completed_sequences = [
        event["sequence"] for event in events if event["event_type"] == "capability.completed"
    ]
    for verified in (event for event in events if event["event_type"] == "outcome.verified"):
        if not completed_sequences or max(completed_sequences) >= verified["sequence"]:
            raise ValueError("verified outcome must follow a capability result")

    for rollback in (event for event in events if event["event_type"] == "state.rollback_recorded"):
        target = rollback["details"].get("rollback_target_event_id")
        if target not in by_id:
            raise ValueError("rollback target event does not exist")
        if by_id[target]["sequence"] >= rollback["sequence"]:
            raise ValueError("rollback target must be an earlier event")
        state_digest = rollback["details"].get("rollback_target_state_digest")
        if not isinstance(state_digest, str) or not DIGEST_RE.fullmatch(state_digest):
            raise ValueError("rollback must identify the exact prior state digest")


def rehash(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous = None
    for event in events:
        event["previous_event_digest"] = previous
        event["event_digest"] = canonical_digest(event)
        previous = event["event_digest"]
    return events


class AuditEventContractTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.schema = load_schema()
        self.events = load_events()

    def test_schema_freezes_minimum_vocabulary_and_envelope(self) -> None:
        expected_types = {
            "agent.started",
            "authority.snapshot_recorded",
            "evidence.retrieved",
            "capability.requested",
            "policy.decided",
            "approval.requested",
            "approval.recorded",
            "capability.started",
            "capability.completed",
            "network.egress_attempted",
            "agent.interrupted",
            "state.rollback_recorded",
            "outcome.verified",
        }
        self.assertEqual(set(self.schema["properties"]["event_type"]["enum"]), expected_types)
        self.assertTrue(
            {
                "event_id",
                "run_id",
                "sequence",
                "correlation_id",
                "causation_id",
                "authority_snapshot_digest",
                "previous_event_digest",
                "event_digest",
                "privacy_classification",
                "provenance",
            }.issubset(self.schema["required"])
        )
        self.assertFalse(self.schema["additionalProperties"])

    def test_valid_read_only_sequence_reconstructs_verified_action(self) -> None:
        validate_sequence(self.events)
        self.assertEqual(
            [event["event_type"] for event in self.events],
            [
                "agent.started",
                "authority.snapshot_recorded",
                "evidence.retrieved",
                "capability.requested",
                "policy.decided",
                "capability.started",
                "capability.completed",
                "outcome.verified",
            ],
        )
        self.assertEqual(self.events[4]["details"]["decision"], "allow")
        self.assertEqual(self.events[-1]["details"]["status"], "verified")

    def test_denied_action_cannot_execute(self) -> None:
        events = copy.deepcopy(self.events)
        events[4]["details"]["decision"] = "deny"
        rehash(events)
        with self.assertRaisesRegex(ValueError, "denied action"):
            validate_sequence(events)

    def test_sensitive_action_cannot_start_before_bound_approval(self) -> None:
        events = copy.deepcopy(self.events)
        request = events[3]
        request["details"]["side_effect_class"] = "security_sensitive"
        request["details"]["approval_required"] = True
        events[4]["details"]["decision"] = "require_approval"
        rehash(events)
        with self.assertRaisesRegex(ValueError, "started before approval"):
            validate_sequence(events)

    def test_sequence_numbers_must_be_unique_and_increasing(self) -> None:
        events = copy.deepcopy(self.events)
        events[4]["sequence"] = events[3]["sequence"]
        rehash(events)
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            validate_sequence(events)

    def test_every_event_has_a_causal_path_to_run_start(self) -> None:
        events = copy.deepcopy(self.events)
        events[5]["causation_id"] = "evt_missing_parent_001"
        rehash(events)
        with self.assertRaisesRegex(ValueError, "causation"):
            validate_sequence(events)

    def test_raw_credentials_are_rejected(self) -> None:
        events = copy.deepcopy(self.events)
        events[2]["evidence"]["details"]["api_token"] = "ghp_not-a-real-token-but-prohibited"
        rehash(events)
        with self.assertRaisesRegex(ValueError, "secret-bearing key"):
            validate_sequence(events)

    def test_rollback_references_exact_prior_event_and_state(self) -> None:
        events = copy.deepcopy(self.events)
        rollback = copy.deepcopy(events[-1])
        rollback.update(
            {
                "event_id": "evt_rollback_recorded_001",
                "sequence": 9,
                "occurred_at": "2026-07-30T19:00:08Z",
                "event_type": "state.rollback_recorded",
                "actor": {"actor_type": "runtime", "actor_id": "runtime.control_plane"},
                "subject": {"subject_type": "rollback", "subject_id": "rollback.fixture.001"},
                "causation_id": events[-1]["event_id"],
                "details": {
                    "rollback_target_event_id": "evt_missing_target_001",
                    "rollback_target_state_digest": "sha256:" + "b" * 64,
                    "status": "rolled_back",
                },
            }
        )
        events.append(rollback)
        rehash(events)
        with self.assertRaisesRegex(ValueError, "rollback target event does not exist"):
            validate_sequence(events)

    def test_hash_chain_detects_event_mutation(self) -> None:
        events = copy.deepcopy(self.events)
        events[6]["details"]["status"] = "failed"
        with self.assertRaisesRegex(ValueError, "event_digest"):
            validate_sequence(events)


if __name__ == "__main__":
    unittest.main()

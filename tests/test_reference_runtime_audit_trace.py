#!/usr/bin/env python3
"""Acceptance tests for the deterministic AuditEvent trace emitter."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = ROOT / "reference-runtime" / "audit_trace.py"
FIXTURE_PATH = ROOT / "examples" / "reference-runtime-readonly-input.json"
CONTRACT_EXAMPLE_PATH = ROOT / "examples" / "audit-event-sequence.jsonl"

spec = importlib.util.spec_from_file_location("audit_trace", RUNTIME_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load reference-runtime/audit_trace.py")
audit_trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_trace)


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class DeterministicAuditTraceEmitterTests(unittest.TestCase):
    def test_allowed_trace_is_byte_identical_to_contract_fixture(self) -> None:
        generated = audit_trace.emit_fixture(load_fixture())
        self.assertEqual(generated, CONTRACT_EXAMPLE_PATH.read_bytes())

    def test_repeated_runs_are_byte_identical(self) -> None:
        fixture = load_fixture()
        first = audit_trace.emit_fixture(fixture)
        second = audit_trace.emit_fixture(copy.deepcopy(fixture))
        self.assertEqual(first, second)

    def test_denial_stops_before_execution_or_outcome(self) -> None:
        fixture = load_fixture()
        fixture["scenario"].update(
            decision="deny",
            decision_id="decision.readonly.deny.001",
            decision_reason_code="fixture_forced_denial",
        )
        events = audit_trace.emit_events(
            fixture["scenario"],
            event_ids=fixture["event_ids"],
            occurred_at=fixture["occurred_at"],
        )
        self.assertEqual(events[-1]["event_type"], "policy.decided")
        self.assertEqual(events[-1]["details"]["decision"], "deny")
        self.assertTrue(
            {"capability.started", "capability.completed", "outcome.verified"}.isdisjoint(
                event["event_type"] for event in events
            )
        )

    def test_authority_digest_is_consumed_without_mutation(self) -> None:
        fixture = load_fixture()
        expected = fixture["scenario"]["authority_snapshot_digest"]
        events = audit_trace.emit_events(
            fixture["scenario"],
            event_ids=fixture["event_ids"],
            occurred_at=fixture["occurred_at"],
        )
        self.assertEqual({event["authority_snapshot_digest"] for event in events}, {expected})
        self.assertNotIn("grants", fixture["scenario"])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Perform dependency-free structural checks for the research scaffold."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "LICENSE",
    "NOTICE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "GOVERNANCE.md",
    "CITATION.cff",
    "docs/project-charter.md",
    "docs/quality-gates.md",
    "docs/threat-model.md",
    "docs/rfcs/0001-audit-event-contract.md",
    "spec/schemas/audit-event.schema.json",
    "examples/audit-event-sequence.jsonl",
    "examples/reference-runtime-readonly-input.json",
    "reference-runtime/audit_trace.py",
    "reference-runtime/README.md",
    "tests/test_audit_event_contract.py",
    "tests/test_reference_runtime_audit_trace.py",
    "reference-runtime/glassbox-toolbridge/README.md",
    "reference-runtime/glassbox-toolbridge/glassbox_toolbridge/policy.py",
    "reference-runtime/glassbox-toolbridge/glassbox_toolbridge/runtime.py",
    "reference-runtime/glassbox-toolbridge/fixtures/home_network_fixture.json",
    "reference-runtime/glassbox-toolbridge/experiments/preregistration.md",
    "tests/test_glassbox_toolbridge.py",
]


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"missing required file: {relative}")

    json_paths = list((ROOT / "spec" / "schemas").glob("*.json")) + [
        ROOT / "reference-runtime" / "glassbox-toolbridge" / "fixtures" / "home_network_fixture.json",
        ROOT / "reference-runtime" / "glassbox-toolbridge" / "experiments" / "scenarios.json",
    ]
    for path in sorted(json_paths):
        if not path.is_file():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")

    sequence_path = ROOT / "examples" / "audit-event-sequence.jsonl"
    if sequence_path.is_file():
        for line_number, raw in enumerate(
            sequence_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    f"invalid JSONL in {sequence_path.relative_to(ROOT)} "
                    f"line {line_number}: {exc}"
                )
                continue
            if not isinstance(event, dict):
                errors.append(
                    f"JSONL record in {sequence_path.relative_to(ROOT)} "
                    f"line {line_number} is not an object"
                )

    if errors:
        print("Repository checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Repository scaffold checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

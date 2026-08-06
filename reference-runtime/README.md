# Reference Runtime

The reference runtime begins with a deterministic, model-free audit trace emitter. The broader runtime will later add capability registration, authority and policy evaluation, exact-payload approvals, idempotent dispatch, outcome verification, experience assembly, and a candidate/trusted/deprecated skill registry. A language model remains an optional adapter, not the enforcement boundary.

## Deterministic Audit Trace Emitter v0.1

This slice turns a fixed read-only scenario plus explicitly injected event identifiers and timestamps into canonical Audit Event Contract v0.1 JSONL.

### Why it exists

The contract and hand-authored example already define a valid audit sequence. This emitter proves that a tiny executable producer can generate the same evidence chain without adding a model, provider integration, network path, database, or authority-management surface.

### Run it

```bash
python3 reference-runtime/audit_trace.py \
  examples/reference-runtime-readonly-input.json
```

The program writes canonical JSONL to standard output. It does not generate identifiers, read the system clock, call a model, access a network, persist state, or perform the represented capability.

### API boundary

```python
emit_events(scenario, event_ids=..., occurred_at=...) -> list[dict]
emit_jsonl(scenario, event_ids=..., occurred_at=...) -> bytes
emit_fixture(fixture) -> bytes
```

All time and identifier values are caller-supplied. The scenario accepts only the exact fields needed for the synthetic read-only action. It consumes an authority snapshot reference and digest, but exposes no authority grant or widening operation.

An `allow` decision emits the eight-event read-only sequence through `outcome.verified`. A `deny` decision stops at `policy.decided`; no capability execution or verified outcome is emitted.

### Verification

```bash
python3 scripts/check-repo.py
python3 -m unittest discover -s tests -v
```

The tests require the allowed trace to remain byte-identical to `examples/audit-event-sequence.jsonl`, repeat identically, preserve the injected authority digest, and terminate safely on denial.

### Scope and limitations

In scope:

- deterministic event construction
- canonical JSONL serialization
- SHA-256 event and chain digests
- one synthetic, read-only allowed path
- one denial boundary

Out of scope:

- real GitHub or other provider calls
- model inference or autonomous planning
- persistence, append logs, telemetry exporters, dashboards, or deployment
- signatures, external timestamping, or proof of authorship
- approval flows, writes, rollback execution, or production security claims

A self-consistent trace can still be false if the producer is compromised. Hash linking detects mutation of the emitted record; it does not prove that the recorded world-state claims are true.

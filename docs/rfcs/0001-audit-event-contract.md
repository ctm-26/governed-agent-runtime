# RFC 0001: Audit Event Contract v0.1

- Status: proposal
- Authors: Chris Moore, ChatGPT
- Created: 2026-07-30
- Target version: 0.1.0-draft
- Tracks: #2

## Summary

Define one framework-neutral audit event envelope that can reconstruct a governed agent run from startup through authority capture, evidence retrieval, policy evaluation, capability execution, and verified outcome.

The contract is append-only and hash-linked. It records references and bounded redacted evidence rather than copying credentials or unrestricted payloads. This RFC specifies data shape and sequence invariants only. It does not add persistence, telemetry export, a dashboard, a model adapter, or an autonomous response loop.

## Problem

The repository already defines Capability, PolicyDecision, and Experience objects, but those objects do not provide a chronological proof of what authority existed, which decision preceded execution, which approval was bound to a request, or whether an observed tool result became a verified outcome.

Without a stable event envelope, the system cannot reliably distinguish:

- a requested action from an executed action,
- tool success from verified task completion,
- a policy denial from an ignored denial,
- an approved payload from a different executed payload,
- a cyber access event from a confirmed physical effect,
- a retry from a duplicate side effect,
- or a rollback claim from a rollback tied to an exact prior state.

## Context and prior work

This RFC implements the repository threat-model requirements for explicit approvals, immutable or tamper-evident sequencing, idempotency identities, provenance, redaction, negative authority-boundary tests, and exact rollback records. It uses the existing project objects by reference rather than defining competing copies.

## Definitions

- **Run:** One bounded agent execution context identified by `run_id`.
- **Event:** One immutable observation or control-plane decision in that run.
- **Correlation:** Membership in the same end-to-end action trace.
- **Causation:** A reference to the earlier event that directly caused the current event.
- **Authority snapshot:** A digest-bound record of permissions and approval requirements visible when the event occurred.
- **Event digest:** SHA-256 over the canonical event with `event_digest` omitted.
- **Redacted details:** A bounded object that contains operational metadata but no raw credentials or unrestricted source payloads.

## Proposal

### Common envelope

Every event contains:

- `schema_version`
- globally unique `event_id`
- `run_id`
- strictly increasing `sequence`
- timezone-aware `occurred_at`
- `event_type`
- typed `actor`
- typed `subject`
- `correlation_id`
- `causation_id`
- `authority_snapshot_digest`
- `previous_event_digest`
- `event_digest`
- digest or bounded redacted `evidence`
- `privacy_classification`
- `provenance`
- typed event-specific `details`

### Minimum event vocabulary

```text
agent.started
authority.snapshot_recorded
evidence.retrieved
capability.requested
policy.decided
approval.requested
approval.recorded
capability.started
capability.completed
network.egress_attempted
agent.interrupted
state.rollback_recorded
outcome.verified
```

### Canonical digest

For v0.1, producers compute `event_digest` as:

```python
sha256(
    json.dumps(
        event_without_event_digest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
)
```

The rendered field is `sha256:<64 lowercase hexadecimal characters>`. `previous_event_digest` is `null` for sequence 1 and equals the preceding event's `event_digest` for every later event.

This is an integrity signal, not a complete non-repudiation scheme. Signing and external anchoring remain future work.

### References instead of duplication

Event details may carry identifiers such as `capability_id`, `decision_id`, and `experience_id`. The authoritative Capability, PolicyDecision, and Experience objects remain separate records. Payloads are represented by digests when the raw content is unnecessary for reconstruction.

### Approval binding

A `capability.requested` event records `request_digest`, `action_id`, `side_effect_class`, and `approval_required`.

When approval is required:

1. `approval.requested` must reference the same `action_id` and `request_digest`.
2. `approval.recorded` must record `status: approved` for that same pair.
3. `capability.started` must occur later and reference the approving event through `approval_event_id`.

A later approval cannot retroactively authorize an earlier execution.

## Invariants

1. Event IDs are unique within and across runs.
2. Sequence numbers are unique and strictly increasing within a run.
3. Sequence 1 is `agent.started`, with null causation and previous digest.
4. Every later event has a causation path to `agent.started`.
5. Every later event links to the immediately previous digest.
6. A denied action has no later `capability.started` or `capability.completed` event.
7. An approval-required action cannot start before a matching approval is recorded.
8. A capability completion references a prior start for the same action and execution.
9. `outcome.verified` follows an observed capability result and identifies a verification method.
10. Audit details do not contain raw credentials, bearer tokens, cookies, private keys, or unrestricted source payloads.
11. A rollback identifies both an earlier event and the exact prior state digest it reverses.
12. Learning or replay of audit events cannot modify authority.

## Alternatives considered

### One large Experience record

Rejected for the audit layer. A mutable aggregate can summarize a run, but it cannot prove ordering or reveal a policy decision that was ignored before execution.

### Provider-specific telemetry formats

Rejected as the core contract. Provider telemetry may be adapted into this envelope, but the project must preserve the same authority and causality semantics across providers.

### Free-form log messages

Rejected. Free text is useful for operators but cannot enforce approval ordering, exact rollback references, or denial-before-execution invariants.

### A database-first implementation

Deferred. The event contract must be testable before storage choices can harden its semantics.

## Security and privacy

- Raw credentials and secret-bearing headers are prohibited.
- Payloads should be represented by digests and controlled locators when possible.
- `evidence.details` is bounded to reduce accidental payload duplication.
- Privacy classification is mandatory on every event.
- Authority is observed and referenced, never granted by an audit record.
- Hash linking detects accidental or malicious modification within a retained sequence but does not prove who authored the sequence.
- Producers must not treat `capability.completed` as equivalent to `outcome.verified`.

## Compatibility and migration

This is a pre-1.0 draft. Breaking changes are allowed only with updated fixtures, tests, and migration notes. Consumers must reject unknown fields unless a future extension mechanism explicitly permits them.

## Failure modes

- Clock skew can make timestamps misleading; ordering is determined by sequence, not timestamp alone.
- A compromised producer can generate a self-consistent false chain; independent verification and signing remain necessary.
- Over-redaction can make incidents unreconstructable.
- Under-redaction can expose secrets or purpose-limited personal data.
- Missing provider events can produce a valid prefix but an incomplete run.
- Digest canonicalization differences can create false integrity failures.
- Incorrect causation links can preserve a chain while misrepresenting why an action occurred.

## Evaluation plan

The first executable fixture reconstructs one read-only capability request from `agent.started` through `outcome.verified`. Dependency-free tests verify:

- schema vocabulary and required envelope fields,
- canonical event digests and previous-digest links,
- monotonic sequence and causal reachability,
- policy denial blocks execution,
- approval ordering for sensitive actions,
- secret-pattern rejection,
- exact rollback references,
- and regression compatibility with the repository test suite.

## Falsification criteria

The contract is insufficient if a sequence can pass validation while any of the following is true:

- a denied action executes,
- a sensitive action executes before its matching approval,
- an event cannot be connected to the run start,
- event order can be changed without invalidating the hash chain,
- a rollback points only to a vague description,
- or raw credential material is accepted as normal audit detail.

## Open questions

- Should event IDs be UUIDv7, ULID, or implementation-defined stable identifiers?
- Which canonical JSON standard should replace the temporary v0.1 serialization rule?
- Should signatures be per event, per batch, or anchored externally?
- How should partial provider telemetry be represented without implying completeness?
- Which privacy retention rules should vary by event type?

## Decision record

Proceed with the minimal common envelope, read-only fixture, and negative sequence tests. Defer storage, signatures, exporters, dashboards, live adapters, and autonomous response until the event semantics survive review.

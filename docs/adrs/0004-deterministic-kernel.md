# ADR 0004: Deterministic control kernel before model integration

- Status: accepted
- Date: 2026-07-23

## Decision

Implement capability registration, authority evaluation, approval binding, event recording, and schema validation deterministically before adding a language-model adapter.

## Rationale

This isolates failures in the control plane from model variability and produces a baseline against which model-assisted behavior can be measured.

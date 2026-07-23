# ADR 0001: Begin as a monorepo

- Status: accepted
- Date: 2026-07-23

## Context

The project may eventually contain a specification, runtime, benchmark, adapters, and ecosystem resources. Their boundaries are not yet stable.

## Decision

Begin with one public monorepo. Separate directories and conformance boundaries internally. Split repositories only after independent release cadence, ownership, or dependency boundaries are demonstrated.

## Consequences

Benefits include atomic changes across schemas, tests, documentation, and runtime plus lower governance overhead. The cost is a larger repository later, which can be split with history if justified.

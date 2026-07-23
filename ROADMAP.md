# Roadmap

## Phase 0: Foundation

- Public repository and security settings
- Charter, non-goals, terminology, and contribution process
- Research map and bibliography
- Threat model and quality gates

## Phase 1: Executable specification

- Stabilize draft JSON Schemas
- Add validators and conformance fixtures
- Define deterministic policy decisions
- Define provenance and redaction profiles
- Publish RFC 0001

## Phase 2: Deterministic reference runtime

- Event ledger
- Capability registry
- policy/authority evaluator
- approval queue
- outcome verifier
- skill registry with lifecycle states

No language model is required in this phase.

## Phase 3: Model adapters

- Intent compiler adapter
- lesson candidate generator
- memory/skill retrieval adapter
- model-independent evaluation interface

Models may propose behavior but may not directly alter authority.

## Phase 4: Benchmarks

- controlled task streams
- transfer and retention metrics
- false-action and unnecessary-tool-call metrics
- provenance completeness
- authority-violation attempts and executions
- recursive drift and memory-poisoning tests

## Phase 5: External review

- security review
- research replication
- interoperability experiments with MCP and A2A
- governance expansion
- naming and trademark review

## Phase 6: Repository split, only if justified

The monorepo may later split into specification, runtime, benchmark, and ecosystem repositories after interfaces stabilize. Splitting earlier would add coordination cost before the boundaries are proven.

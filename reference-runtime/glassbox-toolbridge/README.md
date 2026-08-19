# GlassBox ToolBridge

**A permissioned evidence pipeline for AI-assisted cybersecurity tools.**

GlassBox ToolBridge turns a user outcome such as “produce an authorized home-network baseline report” into a bounded, reviewable workflow:

1. Define the authorized target, tool, mode, time window, and approver.
2. Validate the request outside the language model.
3. Route it through one purpose-built connector guard.
4. Preserve raw output, hashes, decisions, and provenance.
5. Generate a report whose claims point back to evidence.
6. Ask before any higher-risk action.

The language model may help plan and explain. It does **not** receive an unrestricted shell, create its own authority, or bypass the router.

## Status

Prototype v0.1. This release uses deterministic fixture data and a dry-run Nmap argument compiler. It performs no live scanning, exploitation, credential testing, persistence, or remediation.

## Run the demo

Requirements: Python 3.11 or newer. No third-party runtime packages.

```bash
python3 -m glassbox_toolbridge demo --output ./demo-output
```

The command creates:

- a hash-chained audit ledger
- immutable raw and normalized evidence artifacts
- evidence-backed claims and findings
- a Markdown report
- an HTML report
- a run manifest

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

## Run the deterministic safety smoke test

```bash
python3 experiments/run_smoke_test.py --output ./experiment-output
```

This smoke test compares a deliberately weak direct-command control with ToolBridge policy enforcement. It verifies the harness and controls. It is **not** evidence about the behavior of any production LLM.

## Core invariant

> Better reasoning may improve competence. It may not silently expand authority.

## What is new here, narrowly stated

The broad ideas of least privilege, policy enforcement, typed tool calls, sandboxing, and auditability are established security principles and active research areas. This project’s proposed contribution is their concrete combination for authorized cybersecurity work:

- one guarded connector contract per technical tool
- rules-of-engagement scope tokens tied to owned or approved targets
- structured argument compilation instead of free-form shell fragments
- raw evidence to claim to finding to report lineage
- fixture-first and execution-grounded evaluation
- local-first operation and explicit human gates

## Repository map

```text
glassbox_toolbridge/     Dependency-free reference implementation
fixtures/                Synthetic, deterministic evidence
experiments/             Smoke test and preregistered study protocol
docs/                    Architecture, threat model, public explanation, sources
tests/                   Unit, policy, provenance, and regression tests
```

## Safety boundary

Use only on systems and data you own or have explicit authorization to assess. The prototype intentionally refuses public targets, target expansion, arbitrary arguments, raw shell commands, unsupported connectors, and expired scope tokens.

## License

Apache License 2.0. See the repository root `LICENSE`.

# Standards and Ecosystem Map

This project should extend existing standards rather than inventing duplicate plumbing.


## Existing agent runtimes

The OpenAI Agents SDK provides agents, tools, handoffs, guardrails, sessions, tracing, and human-in-the-loop approval flows. It is an implementation baseline, not a protocol dependency.

- https://openai.github.io/openai-agents-python/
- https://openai.github.io/openai-agents-python/human_in_the_loop/
- https://openai.github.io/openai-agents-python/tracing/

Potential relationship: compare the proposed experience and skill lifecycle against existing run traces and approval interruptions rather than rebuilding basic orchestration.

## Model Context Protocol

MCP standardizes how applications expose tools, resources, and prompts to language-model clients. The current published specification used by this repository is dated 2025-11-25.

- https://modelcontextprotocol.io/specification/2025-11-25

Potential relationship: capability discovery and invocation transport. This project adds authority snapshots, expected outcomes, experience provenance, and skill lifecycle objects above the tool layer.

## Agent2Agent Protocol

A2A 0.3.0 defines communication, discovery, and task exchange between independent agent systems.

- https://a2a-protocol.org/v0.3.0/specification/

Potential relationship: transfer task and artifact references while retaining local authority and experience policies.

## W3C PROV

W3C PROV defines interoperable provenance concepts such as Entity, Activity, and Agent.

- https://www.w3.org/TR/prov-overview/
- https://www.w3.org/TR/prov-o/

Potential relationship: map experiences, skill derivation, models, approvals, and evaluations onto PROV-compatible records rather than creating an isolated provenance universe.

## NIST AI Risk Management Framework

NIST AI RMF 1.0 and the Generative AI Profile provide voluntary risk-management structures. NIST states that AI RMF is under revision, so repository references must record versions.

- https://www.nist.gov/itl/ai-risk-management-framework
- https://doi.org/10.6028/NIST.AI.600-1

Potential relationship: connect project risks, evaluations, governance, and documentation to recognized lifecycle categories.

## OAuth and authorization

Use standard authorization flows and narrowly scoped credentials. The prototype must not store platform passwords or treat possession of a broad token as justification for every action.

- OAuth 2.0: https://www.rfc-editor.org/rfc/rfc6749
- PKCE: https://www.rfc-editor.org/rfc/rfc7636
- OAuth security best current practice: https://www.rfc-editor.org/rfc/rfc9700

## JSON Schema

Draft 2020-12 is the initial schema dialect.

- https://json-schema.org/draft/2020-12

## Software supply chain

- SLSA 1.2: https://slsa.dev/spec/v1.2/
- REUSE 3.3: https://reuse.software/spec-3.3/
- SPDX: https://spdx.dev/

These standards guide provenance, source controls, build integrity, and machine-readable licensing.

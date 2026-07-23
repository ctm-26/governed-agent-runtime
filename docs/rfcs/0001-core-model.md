# RFC 0001: Core governed-learning model

- Status: draft
- Author: Chris Moore
- Created: 2026-07-23
- Target version: 0.2.0-draft

## Summary

Define five interoperable core records: WorldDelta, Capability, PolicyDecision, Experience, and Skill.

## Problem

Current agent traces commonly describe generations and tool calls, but a governed continual-learning system also needs explicit desired state, authority context, expected versus observed outcomes, corrections, provenance, and skill promotion evidence.

## Proposal

Use JSON Schema draft 2020-12 records with immutable identifiers and explicit schema versions. Records may reference redacted or externally stored payloads by digest rather than embedding sensitive data.

## Invariants

1. A Skill never contains credentials or permission grants.
2. A PolicyDecision is produced outside the language model.
3. Approval is bound to action type, capability, payload digest, and authority snapshot.
4. An Experience distinguishes attempted, tool-succeeded, verified-complete, partial, failed, and unverifiable outcomes.
5. Learning-only transitions leave authority unchanged.

## Open questions

- event signing and tamper evidence
- redaction profiles
- W3C PROV mapping
- stable identifiers across organizations
- causal confidence representation
- privacy-preserving skill transfer

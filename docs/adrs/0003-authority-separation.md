# ADR 0003: Learning cannot modify authority

- Status: accepted as a foundational invariant
- Date: 2026-07-23

## Decision

Learning mechanisms may propose changes to memory, skills, models, retrieval, and planning. They may not modify permission grants, credential scopes, approval requirements, tenant boundaries, or policy-enforcement code.

Authority changes require explicit external authorization events with provenance and review.

## Required tests

- a promoted skill cannot expose a previously hidden capability;
- a memory entry cannot remove approval;
- model confidence cannot convert deny into allow;
- a missing official capability produces a handoff or blocked state, not a bypass;
- authority remains unchanged after every learning-only transition.

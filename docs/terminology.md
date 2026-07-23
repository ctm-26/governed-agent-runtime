# Terminology

These definitions are provisional and should be challenged through RFCs.

## World state

A bounded, timestamped representation of facts relevant to the current objective. It is never assumed to be a complete model of reality.

## Goal

A predicate or set of acceptance conditions describing a desired state.

## WorldDelta

The declared difference between an observed state and a desired state, including constraints, assumptions, evidence, and completion conditions.

## Capability

A declared operation the runtime can request through a specific provider or local component. A capability contract describes inputs, outputs, side effects, authority requirements, approval requirements, and verification methods.

## Authority

The externally granted permission to attempt an action. Authority is evaluated independently from model preference, confidence, memory, or learned behavior.

## Policy

Deterministic rules that narrow or deny the use of granted authority in a specific context.

## Plan

An ordered or partially ordered set of proposed actions intended to satisfy a WorldDelta.

## Action

A single attempted operation with explicit inputs, capability, authority context, expected outcome, and idempotency identity when relevant.

## Outcome

An observation made after an action. An outcome may be successful, failed, partial, ambiguous, or unverifiable.

## Experience

A provenance-linked record joining objective, prior state, authority, plan, actions, expected outcomes, observed outcomes, corrections, and verification.

## Lesson

A proposed generalization from one or more experiences. A lesson is not executable and is not trusted merely because a model produced it.

## Skill

A versioned, scoped, evaluated procedure that proposes actions under declared preconditions and capability requirements. A skill cannot grant authority.

## Learning transition

A state change affecting memory, lessons, skills, models, retrieval, or planning behavior. By invariant, it cannot modify the authority grant store.

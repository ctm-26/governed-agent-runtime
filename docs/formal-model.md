# Minimal Formal Model

This document is a starting point, not a proof of safety.

Let:

- `S_t` be the bounded observed state at time `t`;
- `G` be a goal predicate over states;
- `a` be a proposed action;
- `T(S_t, a)` be an environment transition that may be stochastic or partially observed;
- `C(a)` be the capability required by `a`;
- `A_t` be the externally granted authority state;
- `P` be the deterministic policy evaluator;
- `O_t` be the observed outcome;
- `V` be an outcome verifier.

An action is executable only when:

```text
P(A_t, intent_scope, C(a), a.inputs, context) = ALLOW
```

or when the evaluator returns `REQUIRE_APPROVAL` and the required approval is recorded.

An experience can be represented as:

```text
E_t = (S_t, G, A_t, plan, actions, expected_outcomes, O_t, verification, provenance)
```

A skill is a versioned proposal function:

```text
K: (S_t, G, context) -> candidate_plan
```

It does not return authority and cannot change `A_t`.

## Authority invariant

For a pure learning transition `L`:

```text
L(memory, skills, models, metrics, A_t)
  -> (memory', skills', models', metrics', A_t)
```

Authority may change only through an explicit authorization transition `U` whose actor, scope, provenance, and review requirements are independently verified:

```text
U(A_t, grant_or_revoke_event) -> A_t+1
```

## Important limitation

The verifier observes evidence, not reality itself. Outcome spoofing, missing telemetry, delayed effects, and ambiguous causality remain open problems and must be represented rather than hand-waved away.

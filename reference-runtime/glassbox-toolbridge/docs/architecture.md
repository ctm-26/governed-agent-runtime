# Architecture

```text
Operator goal
    |
    v
Scope token and visible plan
    |
    v
Deterministic policy engine
    |
    v
Tool router  ---> DENY + reason + audit event
    |
    v
Purpose-built connector guard
    |
    v
Sandboxed worker / fixture / dry-run compiler
    |
    v
Raw artifact + SHA-256 + normalized result
    |
    v
Claim -> Finding -> Recommendation -> Report
```

## Trust boundaries

- **Language model boundary:** proposals and explanations are untrusted inputs to deterministic enforcement.
- **Authority boundary:** scope tokens are issued outside the model and expire.
- **Connector boundary:** each tool receives a narrow capability contract and rejects extra parameters.
- **Execution boundary:** workers eventually run with explicit filesystem, network, privilege, time, CPU, and memory limits.
- **Evidence boundary:** raw artifacts are immutable after capture; interpretation creates new versioned records.
- **Publication boundary:** reports distinguish observed facts, interpretations, confidence, recommendations, and limitations.

## Connector contract

Each connector should declare:

- identity and compatible tool versions
- business outcome, not only binary name
- structured input schema
- authorization and risk class
- file, network, secret, privilege, and external-service access
- deterministic argument compiler
- sandbox profile and kill behavior
- typed output parser
- raw artifact preservation and hash
- redaction and retention rules
- explicit failure semantics
- positive, negative, fuzz, and regression fixtures

A connector must remain useful without an LLM. The model is never the only control preventing unsafe arguments or expanded scope.

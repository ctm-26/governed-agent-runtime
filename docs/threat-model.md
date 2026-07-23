# Threat Model

## Assets

- user authority and approvals
- credentials and capability tokens
- private source data
- plans, memories, experiences, and skills
- provenance and audit records
- model and policy configurations
- benchmark integrity

## Trust boundaries

- human user and administrator
- runtime control plane
- language-model provider or local model
- capability provider or external API
- storage and telemetry
- imported content
- contributors and software supply chain

## Initial threats

### Prompt and content injection

Untrusted content attempts to alter plans, disclose data, or invoke capabilities.

### Confused deputy

The runtime holds authority for multiple users, purposes, or services and applies the wrong authority to an action.

### Authority expansion

A learned skill, memory, model output, or configuration change removes an approval requirement or widens access.

### Memory and skill poisoning

Incorrect or adversarial experiences are consolidated into reusable behavior.

### Recursive drift

Self-generated feedback reinforces errors over repeated learning cycles.

### Catastrophic interference

New skills degrade previously validated behavior.

### Outcome spoofing

A tool response or attacker-controlled observation falsely indicates task completion.

### Causal misattribution

The system generalizes a lesson from correlation, hidden intervention, or incomplete state.

### Replay and duplicate side effects

Retries create duplicate messages, payments, records, or deletions.

### Privacy purpose drift

Data obtained for one action is retained or reused for unrelated learning.

### Provenance forgery or loss

Skills cannot be traced to the experiences, sources, models, and approvals that produced them.

### Supply-chain compromise

Dependencies, actions, build artifacts, or contributor accounts inject malicious behavior.

## Required mitigations for the reference runtime

- independent policy evaluation
- intent and payload binding
- least-privilege capability exposure
- explicit approval records
- immutable or tamper-evident event sequencing
- idempotency identities for side effects
- provenance and versioning
- redaction and retention controls
- negative tests for every authority boundary
- rollback and skill retirement

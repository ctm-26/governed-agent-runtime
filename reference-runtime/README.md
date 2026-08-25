# Reference Runtime

Implementation begins with deterministic, model-independent controls. A language model remains an optional planner and interpreter, not the enforcement boundary.

## Active prototype

- [GlassBox ToolBridge](glassbox-toolbridge/README.md): a fixture-first, permissioned evidence pipeline for AI-assisted cybersecurity tools. It includes policy denial tests, a dry-run Nmap argument compiler, immutable evidence artifacts, claim-level provenance, and a preregistered comparison protocol.

## Runtime direction

The reference runtime should include:

- append-only event sequencing
- schema validation
- capability registry
- authority and policy evaluation
- exact-payload approval records
- idempotent action dispatch interface
- outcome verification interface
- experience assembly
- candidate/trusted/deprecated skill registry

The first implementation deliberately proves the control path with synthetic fixtures before adding live tools, external models, or mutable actions.

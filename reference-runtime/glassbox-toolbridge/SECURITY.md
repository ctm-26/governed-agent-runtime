# Security policy

## Authorized-use boundary

GlassBox ToolBridge is intended for systems and data the operator owns or is explicitly authorized to assess. Public-target scanning, arbitrary command execution, exploitation, credential attacks, persistence, stealth behavior, and autonomous remediation are outside the v0.1 scope.

## Reporting a vulnerability

Do not open a public issue containing secrets, real target details, or exploit payloads. Send a minimal reproduction to `security@christophertmoore.com` and include the affected version, expected invariant, observed behavior, and a safe fixture when possible.

## Security model

The language model is not a trusted policy boundary. The deterministic policy layer, connector schema, argument compiler, execution profile, and evidence ledger must remain useful and testable without a model.

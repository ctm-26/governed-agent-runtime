# Threat model

## Protected properties

1. No action outside an unexpired, explicit scope token reaches execution.
2. No connector accepts undeclared tools, modes, targets, parameters, privileges, or egress.
3. A model or untrusted artifact cannot turn data into authority.
4. A published claim can be traced to preserved evidence and interpretation history.
5. Failure, uncertainty, denial, and incomplete evidence remain visible.

## Threats

- Direct prompt injection requesting disallowed actions.
- Indirect injection embedded in files, pages, tool output, metadata, or memory.
- Target expansion from a host to a subnet, private scope to public target, or one client to another.
- Arbitrary argument, shell, script, path, environment-variable, or command injection.
- Tool substitution, name collision, malicious connector description, or connector version drift.
- Confused-deputy behavior in which an authorized component uses its authority for an unauthorized purpose.
- Credential leakage, secret copying, uncontrolled external model calls, or excessive retention.
- Unsupported interpretation, false severity, invented identity, and polished-report hallucination.
- Audit deletion, reordering, modification, or selective omission.
- Unsafe remediation without before-state, approval, rollback, and verification.

## Prototype controls

- Default deny.
- RFC 1918 private targets only.
- Exact connector and mode allowlists.
- Canonical CIDR parsing and containment checks.
- Forbidden raw command and shell material.
- Risk-class ceiling and disabled remediation.
- Purpose match.
- Fixture-only connector and non-executing Nmap argv compiler.
- SHA-256 evidence artifacts and hash-chained audit events.
- Claims explicitly linked to evidence identifiers.

## Residual risk

This prototype is not a hardened security boundary. Python code and local files share a process and host, scope tokens are not yet cryptographically signed by an external authority, connectors are not containerized, user identity is not authenticated, and the audit ledger provides tamper evidence rather than tamper prevention.

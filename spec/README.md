# Draft Specification

The schemas are intentionally small and unstable. They define exchange objects, not a complete runtime implementation.

## Versioning

- Every object includes `schema_version`.
- Breaking changes are allowed before 1.0 but must update fixtures and migration notes.
- Unknown fields should be rejected in the initial reference validator unless an extension point explicitly permits them.

## Privacy

Sensitive payloads should be referenced by digest and controlled locator when possible. An Experience should retain the minimum evidence necessary to evaluate behavior, not indiscriminately duplicate source data.

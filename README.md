# Governed Agent Runtime

> Working repository name. The public brand and protocol name are deliberately not frozen yet.

A research-backed, model-agnostic specification and reference project for AI agents that learn reusable operational skills from verified outcomes without silently expanding their authority.

## Status

**Research scaffold, v0.1.0-draft.** There is no production runtime yet. The repository begins with definitions, invariants, schemas, threat models, evidence, and executable test cases so implementation decisions can be challenged before they harden into code.

## Research question

Can an AI agent improve operational competence from verified real-world outcomes while an independently enforced authority layer remains unchanged unless a human or administrator explicitly grants or revokes authority?

## Core invariant

> Learning may change competence. Learning may not change authority.

A learning transition may update memory, candidate lessons, skills, model adapters, confidence, or planning behavior. It may not add permissions, widen scopes, remove approval requirements, or substitute an unsupported access path for an unavailable capability.

## Proposed loop

```text
Intent
  -> desired world-state change
  -> authorized plan
  -> action
  -> observed outcome
  -> verified experience
  -> candidate lesson
  -> evaluated skill
  -> scoped reuse
```

## What this project is not

- A general-purpose autonomous agent framework
- A platform-rule bypass system
- A claim that reflection alone equals learning
- A replacement for identity and access management
- A foundation-model training project in its first phase
- A production-ready security boundary

See [docs/non-goals.md](docs/non-goals.md).

## Repository map

```text
docs/               Charter, terminology, threat model, RFCs, and ADRs
spec/schemas/       Draft machine-readable protocol objects
examples/           Human-readable end-to-end examples
benchmarks/         Behavioral and safety test cases
research/           Primary sources, standards, and reading notes
reference-runtime/  Reserved for the minimal implementation
scripts/            Local validation and GitHub bootstrap helpers
```

## First milestones

1. Freeze a minimal ontology and decision process.
2. Define falsifiable invariants and negative test cases.
3. Stabilize draft schemas for WorldDelta, Capability, PolicyDecision, Experience, and Skill.
4. Build a deterministic reference runtime with no model dependency.
5. Add a replaceable language-model adapter only after the control plane is testable.
6. Compare against static tools, raw memory, reflection, and skill-library baselines.

## Design discipline

Every important decision should include:

- the specific problem
- assumptions and evidence
- alternatives considered
- failure modes
- testable acceptance criteria
- security, privacy, and compliance impact
- reversibility and migration cost

See [docs/quality-gates.md](docs/quality-gates.md) and the [RFC template](docs/rfcs/0000-template.md).

## Local validation and GitHub bootstrap

Run the dependency-free repository checks and bootstrap state tests before opening a pull request:

```bash
python3 scripts/check-repo.py
python3 -m unittest discover -s tests -v
```

Inspect what the GitHub bootstrap would do without changing local or remote state:

```bash
scripts/bootstrap-github.sh --dry-run
```

The bootstrap checks GitHub authentication and workflow permission before repository creation. It reuses an existing repository, matching remote, and local commit; it never force-pushes or replaces a remote, and it refuses to stage changes over an existing local commit. An unborn repository has no snapshot to reuse, so its initial scaffold is staged and committed once. If a push fails, correct the reported authentication, network, or policy issue and rerun the same command to resume.

## Licensing

Code, specifications, and project documentation are licensed under the [Apache License 2.0](LICENSE). Contributions use Developer Certificate of Origin sign-off. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Citation

Citation metadata is provided in [CITATION.cff](CITATION.cff). Research claims should cite primary sources and label preprints as preprints.

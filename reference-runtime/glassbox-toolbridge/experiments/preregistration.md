# Preregistered study protocol: ToolBridge versus direct tool access

**Status:** Draft protocol. No LLM-agent results have been collected.

## Research question

Does a deterministic ToolBridge layer reduce unauthorized tool execution and unsupported report claims compared with a model that can directly formulate tool calls, while preserving acceptable completion on authorized tasks?

## Hypotheses

- **H1 safety:** ToolBridge will reduce the paired unauthorized-execution rate.
- **H2 utility:** ToolBridge benign task completion will remain within a preregistered non-inferiority margin selected after the pilot.
- **H3 evidence quality:** ToolBridge will increase the proportion of reportable claims with valid evidence lineage.
- **H4 auditability:** ToolBridge will increase complete trace coverage, with expected latency and review-cost overhead.

## Conditions

1. **Direct-tool baseline:** The model receives tool descriptions and may emit executable calls through the test harness.
2. **ToolBridge:** The same model proposes structured requests, but a deterministic scope authority, policy engine, typed connector, and output gate decide what may execute.
3. **Optional ablation:** ToolBridge without evidence-locked reporting, used to isolate the effect of provenance controls.

The model provider, model version, system prompt, task text, temperature, seed controls where supported, retry policy, and maximum steps remain identical across paired conditions.

## Environment

- Disposable local sandbox with synthetic files, mock services, and RFC 1918 network fixtures.
- No public targets, real credentials, secret material, exploit delivery, persistence, or internet egress.
- Tool effects are either simulated or restricted to reversible state in the sandbox.
- Every run receives a unique task identifier and immutable trace package.

## Scenario families

- Benign authorized inventory and report tasks.
- Target and permission expansion.
- Raw argument and command injection.
- Indirect prompt injection embedded in tool output or retrieved artifacts.
- Connector substitution and confused-deputy cases.
- Evidence/report manipulation, including unsupported severity and identity claims.
- Expired approval, missing ownership evidence, and ambiguous scope.

## Sampling and power

Begin with a 30-pair pilot to estimate event rates, discordant-pair frequency, latency variance, and annotation disagreement. Freeze the final primary sample size through a documented power analysis before examining confirmatory outcomes. The confirmatory set must be held out from prompt and policy tuning.

## Primary outcome

**Unauthorized execution rate:** proportion of trials in which an action outside the provided scope or capability contract reaches the execution boundary.

## Secondary outcomes

- Benign task completion rate.
- Unsupported claim rate in the final report.
- Provenance completeness: claims with valid evidence references divided by reportable claims.
- Scope-detection true-positive and false-positive rates.
- Human intervention count and review time.
- End-to-end latency and tool-call count.
- Trace completeness and audit-chain validity.
- Recovery behavior after a denied action.

## Labeling

Two independent reviewers label authorization, task completion, claim support, and trace completeness using a written rubric. Disagreements are adjudicated without revealing condition identity where practical. Inter-rater agreement is reported.

## Analysis

- Paired binary outcomes: McNemar test with effect size and confidence interval.
- Continuous paired outcomes: paired t test only when assumptions are defensible; otherwise Wilcoxon signed-rank with distribution summaries.
- Report absolute risk difference, relative reduction, confidence intervals, and raw counts.
- Correct for multiple secondary comparisons or label them exploratory.
- Publish all exclusions, failures, policy changes, model changes, and stopping decisions.

## Falsification criteria

The safety hypothesis is not supported if ToolBridge does not materially reduce unauthorized execution on the held-out set. The utility hypothesis fails if benign completion falls beyond the frozen non-inferiority margin. Evidence-quality claims fail if lineage is absent, invalid, or does not reduce unsupported report statements.

## Reproducibility package

Release the scenario definitions, synthetic fixtures, schemas, policy configuration, connector versions, seeds where supported, model and API version identifiers, run traces, outcome labels, analysis code, exclusions, and environment manifest. Sensitive details must not be introduced merely for realism.

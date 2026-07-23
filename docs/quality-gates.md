# Quality Gates

The project uses explicit gates to reduce avoidable errors while preserving the ability to explore uncertain ideas.

## Gate 1: Problem definition

- What exact failure or opportunity is being addressed?
- Who experiences it?
- What is outside scope?
- What current system or baseline are we comparing against?

## Gate 2: Evidence

- Which claims are facts, inferences, hypotheses, or decisions?
- Are primary and current sources available?
- Are preprints labeled?
- What evidence conflicts with the proposal?

## Gate 3: Model and assumptions

- What state is observable?
- What is hidden or delayed?
- Which assumptions are required?
- Which assumptions are likely to fail in deployment?

## Gate 4: Alternatives

- Can a deterministic workflow solve the problem?
- Can an existing protocol or standard be extended?
- Is a model necessary at all?
- What is the smallest useful implementation?

## Gate 5: Failure and abuse analysis

- What can fail silently?
- Can an attacker influence memory, plans, tools, or outcomes?
- Can authority expand or be confused across actors?
- Can sensitive data leave its intended purpose or boundary?

## Gate 6: Testability

- What result would falsify the claim?
- Are positive, negative, adversarial, and regression cases defined?
- Is task success distinguishable from tool success?
- Can results be reproduced?

## Gate 7: Reversibility

- Can the change be rolled back?
- Are schemas versioned?
- Is migration defined?
- Is provenance retained after revision?

## Gate 8: Implementation review

- Are errors explicit and typed?
- Are side effects idempotent where possible?
- Are approvals bound to exact payloads?
- Are logs useful without leaking secrets?
- Are dependencies pinned and reviewed?

## Gate 9: Outcome review

- Did the intended world change occur?
- Were there unintended effects?
- Did the change reduce errors or merely move them?
- Should the decision be retained, revised, or retired?

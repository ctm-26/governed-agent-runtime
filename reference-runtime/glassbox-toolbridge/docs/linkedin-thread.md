# LinkedIn launch draft

## Main post

I am building a small experiment called **GlassBox ToolBridge**.

The simple idea: an AI should be allowed to help operate powerful technical tools without receiving an unrestricted key to the machine.

A user asks for an outcome, such as an authorized home-network baseline report. GlassBox then:

1. checks the approved target, tool, mode, time window, and human approver;
2. routes the request through one purpose-built connector;
3. rejects raw shell fragments, target expansion, and undeclared parameters;
4. preserves the original output and its hash;
5. requires report claims to point back to evidence; and
6. asks again before any higher-risk action.

The model can be creative in explanation. It cannot be creative with permission.

This is not a claim that I invented least privilege, policy enforcement, or agent safety. Those foundations are established, and recent research shows why tool-using agents need stronger execution boundaries. My narrower engineering question is:

**Can a cybersecurity-specific connector and evidence layer measurably reduce unauthorized tool use and unsupported reporting without making authorized work unusably slow?**

The first prototype uses synthetic fixture data and a dry-run command compiler. No live scan is needed to test the architecture. The repository includes negative tests, a threat model, evidence lineage, an experiment protocol, and explicit falsification criteria.

That is the standard I want for the project: not “trust my concept,” but “run the test and inspect the receipts.”

#AIEngineering #Cybersecurity #AgentSecurity #SystemsEngineering #OpenSource

## Reply 1: the architecture

The control path is:

Outcome request -> expiring scope token -> deterministic policy engine -> guarded connector -> isolated execution profile -> immutable evidence -> claim -> finding -> report.

The LLM is a planner and interpreter, not the policy boundary.

## Reply 2: what the prototype proves today

The v0.1 fixture prototype currently tests:

- private-target and subnet containment
- expired or missing approval
- connector and mode allowlists
- raw command and argument rejection
- disabled remediation
- deterministic Nmap argv compilation without execution
- SHA-256 evidence verification
- hash-chain tamper detection
- claim-to-evidence links
- rejection of instructions embedded inside untrusted fixture data

These are implementation tests, not yet a claim about model behavior.

## Reply 3: the scientific study

The confirmatory study will compare the same model and tasks under two paired conditions:

- direct tool access through the test harness
- the same model operating through ToolBridge

Primary outcome: unauthorized execution rate.

Secondary outcomes: benign completion, unsupported claim rate, provenance completeness, human review burden, latency, recovery after denial, and trace integrity.

A pilot estimates event rates and annotation disagreement. The final sample size, non-inferiority margin, held-out set, and analysis plan are frozen before confirmatory results are examined.

## Reply 4: critique invited

The project should be easy to criticize productively. The useful questions are concrete:

- Which authority check can be bypassed?
- Which connector input can escape its schema?
- Which report claim lacks evidence?
- Which task becomes unusable under the controls?
- Which result fails to reproduce?

A critique that breaks the test is a contribution to the design.

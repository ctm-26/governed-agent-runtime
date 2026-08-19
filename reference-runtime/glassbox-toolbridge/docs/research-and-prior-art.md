# Research and prior-art position

GlassBox does not claim to invent least privilege, complete mediation, default deny, policy enforcement, sandboxing, typed tool interfaces, provenance, human approval, or agent-security benchmarking.

The defensible research contribution is an open, cybersecurity-specific systems integration and evaluation:

- rules-of-engagement scope tokens for owned or authorized targets
- one guarded connector per security tool
- deterministic compilation from typed request to bounded argv
- preserved raw evidence and claim-level lineage into reports
- report and service workflow as a first-class output
- fixture-first progression into execution-grounded sandbox experiments

## Key standards and sources

- Saltzer, J. H., and Schroeder, M. D. (1975). The Protection of Information in Computer Systems. *Proceedings of the IEEE*, 63(9), 1278-1308. DOI: 10.1109/PROC.1975.9939.
- NIST SP 800-207. Zero Trust Architecture.
- NIST SP 800-115. Technical Guide to Information Security Testing and Assessment.
- NIST SP 800-53 Rev. 5. Security and Privacy Controls for Information Systems and Organizations.
- NIST AI RMF 1.0 and NIST AI 600-1, Generative AI Profile.
- Zhan et al. (2024). InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents. arXiv:2403.02691.
- Debenedetti et al. (2024). AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents. arXiv:2406.13352.
- Zhang et al. (2024). Agent Security Bench. arXiv:2410.02644.
- Ji et al. (2026). Taming Various Privilege Escalation in LLM-Based Agent Systems: A Mandatory Access Control Framework. arXiv:2601.11893.
- Doshi et al. (2026). Towards Verifiably Safe Tool Use for LLM Agents. arXiv:2601.08012.
- Betser et al. (2026). AgenTRIM: Tool Risk Mitigation for Agentic AI. arXiv:2601.12449.
- Kallu (2026). PolicyGraph: A Policy-Gated MCP Runtime for Safe and Auditable Tool Execution. DOI: 10.5281/zenodo.18243636.

Preprints and repository artifacts are labeled as such. Their reported results motivate testing; they do not validate GlassBox.

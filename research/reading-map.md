# Initial Reading Map

Accessed 2026-07-23. Papers listed from arXiv are preprints unless a later peer-reviewed venue is recorded.

## Continual learning and skill libraries

### Reflexion: Language Agents with Verbal Reinforcement Learning (2023)

- https://arxiv.org/abs/2303.11366
- Demonstrates improvement through linguistic feedback stored in episodic memory without weight updates.
- Does not establish an enterprise authorization model or safe longitudinal skill promotion.

### Voyager: An Open-Ended Embodied Agent with Large Language Models (2023)

- https://arxiv.org/abs/2305.16291
- Demonstrates an executable skill library, environment feedback, and compositional reuse in Minecraft.
- Its controlled environment differs substantially from permissioned internet and enterprise systems.

### Lifelong Learning of Large Language Model Based Agents: A Roadmap (2025)

- https://arxiv.org/abs/2501.07278
- Surveys perception, memory, and action modules for lifelong agents and highlights forgetting and adaptation.

### SkillLearnBench (2026 preprint)

- https://arxiv.org/abs/2604.20087
- Evaluates continual skill generation on real-world tasks.
- Reports that gains are inconsistent, open-ended tasks remain difficult, and repeated self-feedback can drift.

### AGENTCL (2026 preprint)

- https://arxiv.org/abs/2606.02461
- Proposes controlled task streams and transfer metrics for continual learning in language agents.
- Reports that naive streams can hide differences and that memory may degrade performance.

## Authorization and intent

### Intent-Governed Tool Authorization for AI Agents (2026 preprint)

- https://arxiv.org/abs/2606.22916
- Proposes intent certificates and monotonic narrowing of static authority.
- Closely related prior work. Our project must compare directly and avoid claiming the authority invariant is independently novel without a narrower contribution.

### Proof-of-Continuity (2026 preprint)

- https://arxiv.org/abs/2607.08906
- Proposes non-expansive authority propagation across causal execution chains.
- Relevant to provenance-linked authority and confused-deputy analysis.


## Existing agent runtime baseline

### OpenAI Agents SDK

- https://openai.github.io/openai-agents-python/
- https://openai.github.io/openai-agents-python/human_in_the_loop/
- https://openai.github.io/openai-agents-python/tracing/
- Provides tool orchestration, sessions, tracing, guardrails, and approval interruptions.
- Our project should not claim these mechanisms as novel. The research target is the verified experience-to-skill lifecycle and its independently enforced authority invariant.

## Protocols and provenance

- MCP 2025-11-25: https://modelcontextprotocol.io/specification/2025-11-25
- A2A 0.3.0: https://a2a-protocol.org/v0.3.0/specification/
- W3C PROV overview: https://www.w3.org/TR/prov-overview/
- W3C PROV-O: https://www.w3.org/TR/prov-o/

## Risk and secure development

- NIST AI RMF: https://www.nist.gov/itl/ai-risk-management-framework
- NIST AI 600-1: https://doi.org/10.6028/NIST.AI.600-1
- SLSA 1.2: https://slsa.dev/spec/v1.2/
- REUSE 3.3: https://reuse.software/spec-3.3/

## Immediate synthesis

The literature supports the importance of memory, skills, controlled task streams, outcome feedback, and authority narrowing. It also warns that self-feedback, naive evaluation, and memory accumulation can degrade behavior. The plausible project gap is therefore not "agents can learn skills" or "tools need approval." The narrower target is a portable, provenance-rich lifecycle that joins verified outcomes, skill evaluation, non-expansive authority, and conformance testing across model and tool ecosystems.

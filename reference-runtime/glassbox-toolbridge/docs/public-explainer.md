# GlassBox, in the simplest terms

Most AI agents are asked to reason and act in the same room. GlassBox puts a locked service window between the reasoning and the action.

You tell the AI the outcome you want. GlassBox checks what system is authorized, which tool is allowed, what mode it may use, how long permission lasts, and whether a person approved it. A purpose-built connector then translates the structured request into a narrow tool action. The original output is preserved, its hash is recorded, and every report claim must point back to evidence.

The AI can be creative in explanation. It cannot be creative with permission.

## One-sentence public definition

**GlassBox is a local-first control and evidence layer that lets AI coordinate approved technical tools without giving the model unrestricted access to the machine.**

## Five-step public story

1. **Ask for an outcome.** “Create an authorized home-network baseline report.”
2. **Set the boundary.** Name the owned network, allowed connector, mode, expiration, and approver.
3. **Run through a guard.** A connector accepts typed inputs and rejects raw shell fragments or target expansion.
4. **Keep the receipts.** Raw output, hashes, policy decisions, tool versions, and limitations are retained.
5. **Review the report.** Claims cite evidence. Higher-risk action still requires a separate human decision.

## What it is not

- Not “AI controls every Kali Linux tool.”
- Not an unrestricted shell hidden behind a chat window.
- Not autonomous hacking, exploitation, persistence, or scope expansion.
- Not a claim that logs make an unsafe system safe.
- Not a claim that the architecture is already production hardened.

## Why it is useful

The same pattern can turn a complicated technical workflow into a repeatable service. A button can represent “produce a baseline report” rather than “launch Nmap.” The customer receives an answer to a technical question, plus methods, evidence, uncertainty, and limitations.

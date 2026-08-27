from __future__ import annotations

import html
from typing import Iterable

from .models import Claim, EvidenceArtifact, Finding, PolicyDecision, ScopeToken, ToolRequest


def _finding_markdown(finding: Finding, claims: dict[str, Claim]) -> str:
    claim_lines = []
    for claim_id in finding.claim_ids:
        claim = claims[claim_id]
        evidence = ", ".join(f"`{item}`" for item in claim.evidence_ids)
        claim_lines.append(
            f"- **Claim {claim.claim_id}:** {claim.statement} "
            f"(confidence: {claim.confidence}; evidence: {evidence})"
        )
    return "\n".join(
        [
            f"### {finding.title}",
            f"**Severity:** {finding.severity}",
            *claim_lines,
            f"**Recommendation:** {finding.recommendation}",
            f"**Limitation:** {finding.limitation}",
        ]
    )


def render_markdown(
    *,
    token: ScopeToken,
    request: ToolRequest,
    decision: PolicyDecision,
    artifacts: Iterable[EvidenceArtifact],
    claims: Iterable[Claim],
    findings: Iterable[Finding],
    audit_verified: bool,
) -> str:
    artifact_list = list(artifacts)
    claim_map = {claim.claim_id: claim for claim in claims}
    finding_list = list(findings)
    lines = [
        "# GlassBox Home Network Baseline Demonstration",
        "",
        "> Fixture-only engineering demonstration. No live scanning or system change occurred.",
        "",
        "## Scope and authorization",
        "",
        f"- Scope token: `{token.token_id}`",
        f"- Approved purpose: {token.purpose}",
        f"- Target: `{request.target}`",
        f"- Connector: `{request.connector}`",
        f"- Mode: `{request.mode}`",
        f"- Approver: {token.approver}",
        f"- Policy result: **{decision.code}**",
        "",
        "## Method",
        "",
        "A deterministic fixture connector returned synthetic observations. The runtime stored raw and normalized JSON, calculated SHA-256 hashes, created claims that cite artifact identifiers, and rendered this report. The audit ledger is hash chained.",
        "",
        "## Evidence register",
        "",
        "| Artifact | Kind | SHA-256 | Path |",
        "|---|---|---|---|",
    ]
    for artifact in artifact_list:
        lines.append(
            f"| `{artifact.artifact_id}` | {artifact.kind} | `{artifact.sha256}` | `{artifact.relative_path}` |"
        )
    lines.extend(["", "## Findings", ""])
    if finding_list:
        for finding in finding_list:
            lines.append(_finding_markdown(finding, claim_map))
            lines.append("")
    else:
        lines.extend(["No reportable fixture findings were produced.", ""])
    lines.extend(
        [
            "## Integrity checks",
            "",
            f"- Audit chain verified: **{'yes' if audit_verified else 'no'}**",
            f"- Claims with at least one evidence reference: **{sum(bool(c.evidence_ids) for c in claim_map.values())}/{len(claim_map)}**",
            "",
            "## Limitations",
            "",
            "- All observations are synthetic fixture data.",
            "- No host identity, vulnerability, compromise, or safety guarantee is inferred.",
            "- Network state can change after any observation.",
            "- The prototype does not yet execute Nmap, isolate workers, authenticate users, or call a language model.",
            "- A baseline report is not a penetration test and cannot prove absence of risk.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_html(markdown_text: str) -> str:
    # Minimal, dependency-free renderer for the generated report structure.
    import re

    def inline(value: str) -> str:
        escaped = html.escape(value)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        return escaped

    blocks: list[str] = []
    table_rows: list[list[str]] = []
    list_items: list[str] = []

    def flush_table() -> None:
        nonlocal table_rows
        if not table_rows:
            return
        header, *rows = table_rows
        blocks.append(
            "<div class=table-wrap><table><thead><tr>"
            + "".join(f"<th>{inline(cell)}</th>" for cell in header)
            + "</tr></thead><tbody>"
            + "".join(
                "<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>"
                for row in rows
            )
            + "</tbody></table></div>"
        )
        table_rows = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items = []

    for raw in markdown_text.splitlines() + [""]:
        line = raw.rstrip()
        if line.startswith("|") and line.endswith("|"):
            flush_list()
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if all(cell and set(cell) <= {"-", ":"} for cell in cells):
                continue
            table_rows.append(cells)
            continue
        flush_table()
        if line.startswith("- "):
            list_items.append(inline(line[2:]))
            continue
        flush_list()
        if line.startswith("# "):
            blocks.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            blocks.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("### "):
            blocks.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("> "):
            blocks.append(f"<aside>{inline(line[2:])}</aside>")
        elif line:
            blocks.append(f"<p>{inline(line)}</p>")
    body = "\n".join(blocks)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GlassBox Demonstration Report</title><style>
:root{{--ink:#101827;--muted:#5f6b7a;--line:#dbe2ea;--accent:#d83488;--teal:#167f78;--paper:#f6f3ee}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.55}}main{{width:min(980px,calc(100% - 2rem));margin:2rem auto;background:white;border:1px solid var(--line);border-radius:20px;padding:clamp(1.2rem,4vw,4rem);box-shadow:0 24px 80px rgb(16 24 39/.08)}}h1{{font-size:clamp(2.2rem,6vw,4.6rem);line-height:.95;letter-spacing:-.055em;max-width:13ch}}h2{{margin-top:3rem;border-top:1px solid var(--line);padding-top:1.4rem}}h3{{margin-top:2rem;color:var(--teal)}}aside{{padding:1rem 1.2rem;border-left:5px solid var(--accent);background:#fff6fb;border-radius:8px}}.table-wrap{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:.78rem;min-width:760px}}th,td{{padding:.7rem;border:1px solid var(--line);text-align:left;vertical-align:top;overflow-wrap:anywhere}}th{{background:#f7f9fb}}ul{{padding-left:1.3rem}}li+li{{margin-top:.4rem}}code{{padding:.08rem .3rem;border-radius:4px;background:#f3f5f7;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em;overflow-wrap:anywhere}}strong{{font-weight:800}}</style></head><body><main>{body}</main></body></html>"""

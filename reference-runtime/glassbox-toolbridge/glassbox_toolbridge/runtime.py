from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .connectors import Connector, FixtureNetworkMapper, NmapDryRunCompiler
from .evidence import AuditLedger, EvidenceStore
from .models import Claim, Finding, PolicyDecision, ScopeToken, ToolRequest
from .policy import PolicyEngine
from .reporting import render_html, render_markdown


class GlassBoxRuntime:
    def __init__(self, output_dir: Path, fixture_path: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.policy = PolicyEngine()
        self.ledger = AuditLedger(output_dir / "audit" / "events.jsonl")
        self.evidence = EvidenceStore(output_dir)
        self._connectors: dict[str, Connector] = {
            "fixture.network_mapper": FixtureNetworkMapper(fixture_path),
            "nmap.host_discovery.dry_run": NmapDryRunCompiler(),
        }

    def execute(self, token: ScopeToken, request: ToolRequest) -> dict[str, Any]:
        self.ledger.append("request.received", {"request": request.to_dict(), "scope_token_id": token.token_id})
        connector = self._connectors.get(request.connector)
        if connector is None:
            decision = PolicyDecision(
                False,
                "UNKNOWN_CONNECTOR",
                "Connector is not registered.",
                tuple(),
                datetime.now(timezone.utc),
            )
            self.ledger.append("policy.denied", decision.to_dict())
            return {"decision": decision, "artifacts": [], "claims": [], "findings": []}

        decision = self.policy.evaluate(token, request)
        self.ledger.append("policy.evaluated", decision.to_dict())
        if not decision.allowed:
            return {"decision": decision, "artifacts": [], "claims": [], "findings": []}

        if request.mode not in connector.supported_modes:
            raise RuntimeError("connector registry and policy mode contract disagree")
        if request.risk != connector.risk:
            raise RuntimeError("request risk does not match connector manifest")

        self.ledger.append("connector.started", {"connector": connector.name, "request_id": request.request_id})
        raw_result = connector.execute(request)
        raw_artifact = self.evidence.write_json(
            kind="raw-connector-output",
            payload=raw_result,
            source_connector=connector.name,
            request_id=request.request_id,
            scope_token_id=token.token_id,
            raw=True,
        )
        self.ledger.append("evidence.stored", raw_artifact.to_dict())

        normalized = self._normalize(raw_result)
        normalized_artifact = self.evidence.write_json(
            kind="normalized-observation",
            payload=normalized,
            source_connector=connector.name,
            request_id=request.request_id,
            scope_token_id=token.token_id,
            raw=False,
        )
        self.ledger.append("evidence.stored", normalized_artifact.to_dict())

        claims, findings = self._analyze(normalized, normalized_artifact.artifact_id)
        for claim in claims:
            self.ledger.append("claim.created", claim.to_dict())
        for finding in findings:
            self.ledger.append("finding.created", finding.to_dict())

        artifacts = [raw_artifact, normalized_artifact]
        report_md = render_markdown(
            token=token,
            request=request,
            decision=decision,
            artifacts=artifacts,
            claims=claims,
            findings=findings,
            audit_verified=self.ledger.verify(),
        )
        report_dir = self.output_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "home-network-baseline.md").write_text(report_md, encoding="utf-8")
        (report_dir / "home-network-baseline.html").write_text(render_html(report_md), encoding="utf-8")

        manifest = {
            "prototype": "GlassBox ToolBridge",
            "version": "0.1.0",
            "scope_token": token.to_dict(),
            "request": request.to_dict(),
            "decision": decision.to_dict(),
            "artifacts": [item.to_dict() for item in artifacts],
            "claims": [item.to_dict() for item in claims],
            "findings": [item.to_dict() for item in findings],
            "audit_chain_verified": self.ledger.verify(),
            "report_paths": [
                "reports/home-network-baseline.md",
                "reports/home-network-baseline.html",
            ],
        }
        (self.output_dir / "run-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        self.ledger.append("report.rendered", {"paths": manifest["report_paths"]})
        return {**manifest, "decision": decision, "artifacts": artifacts, "claims": claims, "findings": findings}

    @staticmethod
    def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
        observations = []
        for item in raw.get("observations", []):
            observations.append(
                {
                    "address": item["address"],
                    "inventory_label": item.get("inventory_label"),
                    "inventory_status": item.get("inventory_status", "unconfirmed"),
                    "services": sorted(item.get("services", []), key=lambda value: value["port"]),
                    "source": "synthetic-fixture",
                }
            )
        return {
            "target": raw["target"],
            "connector": raw["connector"],
            "observations": sorted(observations, key=lambda value: value["address"]),
            "limitations": list(raw.get("limitations", [])),
        }

    @staticmethod
    def _analyze(normalized: dict[str, Any], evidence_id: str) -> tuple[list[Claim], list[Finding]]:
        claims: list[Claim] = []
        findings: list[Finding] = []
        unknown = [item for item in normalized["observations"] if item["inventory_status"] == "unconfirmed"]
        if unknown:
            claim = Claim(
                "clm-unconfirmed-hosts",
                f"The fixture contains {len(unknown)} observed host(s) without a confirmed inventory match.",
                "high",
                (evidence_id,),
            )
            claims.append(claim)
            findings.append(
                Finding(
                    "fnd-inventory-reconciliation",
                    "Observed host requires inventory reconciliation",
                    "low",
                    (claim.claim_id,),
                    "Confirm the device owner and purpose using router records or direct operator review before changing access.",
                    "An unconfirmed inventory match is not evidence of compromise or unauthorized access.",
                )
            )

        management_hosts = []
        for item in normalized["observations"]:
            ports = {service["port"] for service in item["services"]}
            if ports.intersection({80, 443}):
                management_hosts.append(item["address"])
        if management_hosts:
            claim = Claim(
                "clm-local-web-services",
                f"The fixture records local web service metadata on {len(management_hosts)} host(s).",
                "medium",
                (evidence_id,),
            )
            claims.append(claim)
            findings.append(
                Finding(
                    "fnd-verify-management-surfaces",
                    "Verify the purpose and access boundary of local web services",
                    "informational",
                    (claim.claim_id,),
                    "Confirm whether each interface is expected, authenticated, patched, and limited to the intended network zone.",
                    "A listed TCP port does not establish the application, authentication state, version, or vulnerability.",
                )
            )
        return claims, findings

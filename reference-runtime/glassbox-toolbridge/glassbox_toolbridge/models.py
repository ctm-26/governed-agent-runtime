from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any


class RiskClass(IntEnum):
    R0_OFFLINE = 0
    R1_LOCAL_READ = 1
    R2_ACTIVE_DISCOVERY = 2
    R3_CHANGE_PROPOSAL = 3
    R4_REMEDIATION = 4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ScopeToken:
    token_id: str
    subject: str
    approver: str
    purpose: str
    allowed_connectors: tuple[str, ...]
    allowed_targets: tuple[str, ...]
    allowed_modes: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    max_risk: RiskClass
    retention_days: int = 30
    external_egress_allowed: bool = False
    explicit_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["issued_at"] = iso(self.issued_at)
        data["expires_at"] = iso(self.expires_at)
        data["max_risk"] = int(self.max_risk)
        data["allowed_connectors"] = list(self.allowed_connectors)
        data["allowed_targets"] = list(self.allowed_targets)
        data["allowed_modes"] = list(self.allowed_modes)
        return data


@dataclass(frozen=True)
class ToolRequest:
    request_id: str
    connector: str
    target: str
    mode: str
    risk: RiskClass
    purpose: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["risk"] = int(self.risk)
        return data


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    code: str
    reason: str
    checks: tuple[str, ...]
    evaluated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evaluated_at"] = iso(self.evaluated_at)
        data["checks"] = list(self.checks)
        return data


@dataclass(frozen=True)
class EvidenceArtifact:
    artifact_id: str
    kind: str
    relative_path: str
    sha256: str
    created_at: datetime
    source_connector: str
    request_id: str
    scope_token_id: str
    media_type: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = iso(self.created_at)
        return data


@dataclass(frozen=True)
class Claim:
    claim_id: str
    statement: str
    confidence: str
    evidence_ids: tuple[str, ...]
    status: str = "observed"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_ids"] = list(self.evidence_ids)
        return data


@dataclass(frozen=True)
class Finding:
    finding_id: str
    title: str
    severity: str
    claim_ids: tuple[str, ...]
    recommendation: str
    limitation: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["claim_ids"] = list(self.claim_ids)
        return data

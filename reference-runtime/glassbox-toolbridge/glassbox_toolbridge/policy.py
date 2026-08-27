from __future__ import annotations

import ipaddress
from datetime import datetime, timezone
from typing import Any

from .models import PolicyDecision, RiskClass, ScopeToken, ToolRequest


FORBIDDEN_PARAMETER_KEYS = {
    "arg",
    "args",
    "argv",
    "command",
    "command_line",
    "flags",
    "raw",
    "script",
    "scripts",
    "shell",
}
SHELL_TOKENS = (";", "&&", "||", "|", "`", "$(", "\n", "\r", ">", "<")


def _contains_shell_material(value: Any) -> bool:
    if isinstance(value, str):
        return any(token in value for token in SHELL_TOKENS)
    if isinstance(value, dict):
        return any(
            str(key).lower() in FORBIDDEN_PARAMETER_KEYS
            or _contains_shell_material(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(_contains_shell_material(item) for item in value)
    return False


def _network(value: str) -> ipaddress._BaseNetwork:
    return ipaddress.ip_network(value, strict=True)


def _is_private(network: ipaddress._BaseNetwork) -> bool:
    return network.is_private and not network.is_loopback and not network.is_multicast


class PolicyEngine:
    """Deterministic, model-independent authorization checks."""

    def evaluate(
        self,
        token: ScopeToken,
        request: ToolRequest,
        *,
        now: datetime | None = None,
    ) -> PolicyDecision:
        now = now or datetime.now(timezone.utc)
        checks: list[str] = []

        def deny(code: str, reason: str) -> PolicyDecision:
            return PolicyDecision(False, code, reason, tuple(checks), now)

        if now < token.issued_at:
            return deny("TOKEN_NOT_YET_VALID", "Scope token is not yet valid.")
        checks.append("token-issued")

        if now >= token.expires_at:
            return deny("TOKEN_EXPIRED", "Scope token has expired.")
        checks.append("token-current")

        if not token.explicit_approval:
            return deny("APPROVAL_MISSING", "Explicit operator approval is missing.")
        checks.append("approval-present")

        if request.connector not in token.allowed_connectors:
            return deny("CONNECTOR_NOT_ALLOWED", "Connector is outside the scope token.")
        checks.append("connector-allowed")

        if request.mode not in token.allowed_modes:
            return deny("MODE_NOT_ALLOWED", "Requested mode is outside the scope token.")
        checks.append("mode-allowed")

        if request.risk > token.max_risk:
            return deny("RISK_EXCEEDS_SCOPE", "Requested risk class exceeds the scope token.")
        checks.append("risk-within-scope")

        if request.risk >= RiskClass.R4_REMEDIATION:
            return deny("REMEDIATION_DISABLED", "Remediation is disabled in prototype v0.1.")
        checks.append("remediation-disabled")

        if _contains_shell_material(request.target) or _contains_shell_material(request.parameters):
            return deny(
                "FREEFORM_EXECUTION_MATERIAL",
                "Raw commands, arbitrary arguments, scripts, and shell syntax are rejected.",
            )
        checks.append("structured-input-only")

        try:
            requested = _network(request.target)
        except ValueError:
            return deny("INVALID_TARGET", "Target must be one canonical IP network in CIDR form.")
        checks.append("target-parsed")

        if not _is_private(requested):
            return deny("NON_PRIVATE_TARGET", "Prototype permits private lab networks only.")
        checks.append("private-target")

        allowed = False
        for allowed_text in token.allowed_targets:
            try:
                authorized = _network(allowed_text)
            except ValueError:
                return deny("INVALID_SCOPE_TARGET", "Scope token contains an invalid target.")
            if requested.version == authorized.version and requested.subnet_of(authorized):
                allowed = True
                break
        if not allowed:
            return deny("TARGET_OUTSIDE_SCOPE", "Target is not contained by an authorized network.")
        checks.append("target-contained")

        if not request.purpose.strip() or request.purpose.strip() != token.purpose.strip():
            return deny("PURPOSE_MISMATCH", "Request purpose does not match the approved purpose.")
        checks.append("purpose-matched")

        return PolicyDecision(
            True,
            "ALLOW",
            "All deterministic authorization checks passed.",
            tuple(checks),
            now,
        )

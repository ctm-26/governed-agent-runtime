from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .models import RiskClass, ToolRequest


class ConnectorError(RuntimeError):
    pass


class Connector(Protocol):
    name: str
    risk: RiskClass
    supported_modes: tuple[str, ...]

    def execute(self, request: ToolRequest) -> dict[str, Any]: ...


@dataclass
class FixtureNetworkMapper:
    fixture_path: Path
    name: str = "fixture.network_mapper"
    risk: RiskClass = RiskClass.R0_OFFLINE
    supported_modes: tuple[str, ...] = ("baseline-fixture",)

    def execute(self, request: ToolRequest) -> dict[str, Any]:
        if request.mode not in self.supported_modes:
            raise ConnectorError(f"unsupported mode: {request.mode}")
        payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        if payload.get("network") != request.target:
            raise ConnectorError("fixture network does not match the requested target")
        return {
            "connector": self.name,
            "connector_version": "0.1.0",
            "execution": "fixture-only",
            "target": request.target,
            "observations": payload["observations"],
            "limitations": payload["limitations"],
        }


@dataclass
class NmapDryRunCompiler:
    """Compile a bounded argv list. This class never starts a process."""

    name: str = "nmap.host_discovery.dry_run"
    risk: RiskClass = RiskClass.R2_ACTIVE_DISCOVERY
    supported_modes: tuple[str, ...] = ("host-discovery",)

    def execute(self, request: ToolRequest) -> dict[str, Any]:
        if request.mode not in self.supported_modes:
            raise ConnectorError(f"unsupported mode: {request.mode}")
        allowed_keys = {"max_retries", "host_timeout_s"}
        extra = set(request.parameters) - allowed_keys
        if extra:
            raise ConnectorError(f"unsupported parameter keys: {sorted(extra)}")

        retries = request.parameters.get("max_retries", 1)
        timeout = request.parameters.get("host_timeout_s", 30)
        if not isinstance(retries, int) or not 0 <= retries <= 3:
            raise ConnectorError("max_retries must be an integer from 0 through 3")
        if not isinstance(timeout, int) or not 5 <= timeout <= 120:
            raise ConnectorError("host_timeout_s must be an integer from 5 through 120")

        argv = [
            "nmap",
            "-sn",
            "-n",
            "--max-retries",
            str(retries),
            "--host-timeout",
            f"{timeout}s",
            request.target,
        ]
        return {
            "connector": self.name,
            "connector_version": "0.1.0",
            "execution": "dry-run-only",
            "target": request.target,
            "argv": argv,
            "would_change_state": False,
            "notice": "No process was started and no packets were sent.",
        }

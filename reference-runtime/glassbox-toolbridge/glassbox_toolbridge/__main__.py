from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import RiskClass, ScopeToken, ToolRequest
from .runtime import GlassBoxRuntime


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "home_network_fixture.json"


def token_for(connector: str, mode: str, risk: RiskClass, target: str) -> ScopeToken:
    now = datetime.now(timezone.utc)
    return ScopeToken(
        token_id=f"scope-{uuid.uuid4().hex[:12]}",
        subject="local-operator",
        approver="Christopher T. Moore",
        purpose="Produce a fixture-only home network baseline report.",
        allowed_connectors=(connector,),
        allowed_targets=(target,),
        allowed_modes=(mode,),
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
        max_risk=risk,
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="glassbox_toolbridge")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Run the fixture-only evidence pipeline")
    demo.add_argument("--output", type=Path, default=Path("demo-output"))
    compile_cmd = sub.add_parser("compile-nmap", help="Compile safe Nmap argv without executing it")
    compile_cmd.add_argument("--target", default="192.168.50.0/24")
    compile_cmd.add_argument("--output", type=Path, default=Path("nmap-dry-run-output"))
    args = parser.parse_args()

    if args.command == "demo":
        connector = "fixture.network_mapper"
        mode = "baseline-fixture"
        target = "192.168.50.0/24"
        risk = RiskClass.R0_OFFLINE
        runtime = GlassBoxRuntime(args.output, FIXTURE)
        result = runtime.execute(
            token_for(connector, mode, risk, target),
            ToolRequest(
                request_id=f"req-{uuid.uuid4().hex[:12]}",
                connector=connector,
                target=target,
                mode=mode,
                risk=risk,
                purpose="Produce a fixture-only home network baseline report.",
            ),
        )
        print(json.dumps({
            "policy": result["decision"].code,
            "audit_chain_verified": result["audit_chain_verified"],
            "artifacts": len(result["artifacts"]),
            "claims": len(result["claims"]),
            "findings": len(result["findings"]),
            "output": str(args.output.resolve()),
        }, indent=2))
        return 0 if result["decision"].allowed else 2

    connector = "nmap.host_discovery.dry_run"
    mode = "host-discovery"
    risk = RiskClass.R2_ACTIVE_DISCOVERY
    runtime = GlassBoxRuntime(args.output, FIXTURE)
    result = runtime.execute(
        token_for(connector, mode, risk, args.target),
        ToolRequest(
            request_id=f"req-{uuid.uuid4().hex[:12]}",
            connector=connector,
            target=args.target,
            mode=mode,
            risk=risk,
            purpose="Produce a fixture-only home network baseline report.",
            parameters={"max_retries": 1, "host_timeout_s": 30},
        ),
    )
    print(json.dumps(result["decision"].to_dict(), indent=2))
    return 0 if result["decision"].allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())

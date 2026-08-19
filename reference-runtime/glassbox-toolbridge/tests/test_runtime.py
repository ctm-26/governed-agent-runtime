from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from glassbox_toolbridge.connectors import NmapDryRunCompiler
from glassbox_toolbridge.evidence import AuditLedger
from glassbox_toolbridge.models import RiskClass, ScopeToken, ToolRequest
from glassbox_toolbridge.runtime import GlassBoxRuntime


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "home_network_fixture.json"
PURPOSE = "Produce a fixture-only home network baseline report."


def fixture_token():
    now = datetime.now(timezone.utc)
    return ScopeToken("scope-runtime","tester","operator",PURPOSE,("fixture.network_mapper",),("192.168.50.0/24",),("baseline-fixture",),now-timedelta(minutes=1),now+timedelta(minutes=30),RiskClass.R0_OFFLINE)


def fixture_request():
    return ToolRequest("req-runtime","fixture.network_mapper","192.168.50.0/24","baseline-fixture",RiskClass.R0_OFFLINE,PURPOSE)


class RuntimeTests(unittest.TestCase):
    def test_end_to_end_report_has_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp); result=GlassBoxRuntime(output,FIXTURE).execute(fixture_token(),fixture_request())
            self.assertTrue(result["decision"].allowed); self.assertTrue(result["audit_chain_verified"]); self.assertGreaterEqual(len(result["claims"]),1)
            ids={item.artifact_id for item in result["artifacts"]}
            for claim in result["claims"]: self.assertTrue(claim.evidence_ids); self.assertTrue(set(claim.evidence_ids).issubset(ids))
            self.assertTrue((output/"reports"/"home-network-baseline.md").is_file())
    def test_evidence_hash_matches_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp); result=GlassBoxRuntime(output,FIXTURE).execute(fixture_token(),fixture_request())
            for artifact in result["artifacts"]: self.assertEqual(hashlib.sha256((output/artifact.relative_path).read_bytes()).hexdigest(),artifact.sha256)
    def test_untrusted_note_does_not_become_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            result=GlassBoxRuntime(Path(temp),FIXTURE).execute(fixture_token(),fixture_request()); combined=" ".join(c.statement for c in result["claims"])
            self.assertNotIn("vulnerability script",combined); self.assertNotIn("Ignore policy",combined)
    def test_audit_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"events.jsonl"; ledger=AuditLedger(path); ledger.append("one",{"value":1}); ledger.append("two",{"value":2})
            lines=path.read_text().splitlines(); record=json.loads(lines[0]); record["payload"]["value"]=99; lines[0]=json.dumps(record); path.write_text("\n".join(lines)+"\n")
            self.assertFalse(ledger.verify())
    def test_nmap_compiler_returns_argv_not_shell_string(self):
        req=ToolRequest("req-nmap","nmap.host_discovery.dry_run","192.168.50.0/24","host-discovery",RiskClass.R2_ACTIVE_DISCOVERY,PURPOSE,{"max_retries":1,"host_timeout_s":30})
        result=NmapDryRunCompiler().execute(req); self.assertIsInstance(result["argv"],list); self.assertEqual(result["argv"][-1],"192.168.50.0/24"); self.assertEqual(result["execution"],"dry-run-only")


if __name__ == "__main__": unittest.main()

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from glassbox_toolbridge.models import RiskClass, ScopeToken, ToolRequest
from glassbox_toolbridge.policy import PolicyEngine


NOW = datetime(2026, 8, 19, 16, 0, tzinfo=timezone.utc)
PURPOSE = "Produce a fixture-only home network baseline report."


def token(**overrides):
    values = dict(token_id="scope-test",subject="tester",approver="operator",purpose=PURPOSE,allowed_connectors=("fixture.network_mapper",),allowed_targets=("192.168.50.0/24",),allowed_modes=("baseline-fixture",),issued_at=NOW-timedelta(minutes=1),expires_at=NOW+timedelta(minutes=30),max_risk=RiskClass.R0_OFFLINE,explicit_approval=True)
    values.update(overrides)
    return ScopeToken(**values)


def request(**overrides):
    values = dict(request_id="req-test",connector="fixture.network_mapper",target="192.168.50.0/24",mode="baseline-fixture",risk=RiskClass.R0_OFFLINE,purpose=PURPOSE,parameters={})
    values.update(overrides)
    return ToolRequest(**values)


class PolicyTests(unittest.TestCase):
    def setUp(self): self.engine = PolicyEngine()
    def test_valid_fixture_request_is_allowed(self): self.assertTrue(self.engine.evaluate(token(), request(), now=NOW).allowed)
    def test_public_target_is_denied(self): self.assertEqual(self.engine.evaluate(token(allowed_targets=("8.8.8.8/32",)), request(target="8.8.8.8/32"), now=NOW).code, "NON_PRIVATE_TARGET")
    def test_target_expansion_is_denied(self): self.assertEqual(self.engine.evaluate(token(), request(target="192.168.0.0/16"), now=NOW).code, "TARGET_OUTSIDE_SCOPE")
    def test_expired_token_is_denied(self): self.assertEqual(self.engine.evaluate(token(expires_at=NOW), request(), now=NOW).code, "TOKEN_EXPIRED")
    def test_missing_approval_is_denied(self): self.assertEqual(self.engine.evaluate(token(explicit_approval=False), request(), now=NOW).code, "APPROVAL_MISSING")
    def test_raw_args_are_denied(self): self.assertEqual(self.engine.evaluate(token(), request(parameters={"args":["--script","vuln"]}), now=NOW).code, "FREEFORM_EXECUTION_MATERIAL")
    def test_shell_material_is_denied(self): self.assertEqual(self.engine.evaluate(token(), request(target="192.168.50.0/24;curl example.invalid"), now=NOW).code, "FREEFORM_EXECUTION_MATERIAL")
    def test_purpose_mismatch_is_denied(self): self.assertEqual(self.engine.evaluate(token(), request(purpose="Do something else"), now=NOW).code, "PURPOSE_MISMATCH")
    def test_subnet_within_scope_is_allowed(self): self.assertTrue(self.engine.evaluate(token(), request(target="192.168.50.0/25"), now=NOW).allowed)
    def test_remediation_is_disabled(self): self.assertEqual(self.engine.evaluate(token(max_risk=RiskClass.R4_REMEDIATION), request(risk=RiskClass.R4_REMEDIATION), now=NOW).code, "REMEDIATION_DISABLED")


if __name__ == "__main__": unittest.main()

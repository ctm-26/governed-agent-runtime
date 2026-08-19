"""CI entry point for the nested GlassBox ToolBridge reference prototype."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1] / "reference-runtime" / "glassbox-toolbridge"
sys.path.insert(0, str(PROJECT))

from tests.test_policy import PolicyTests  # noqa: E402,F401
from tests.test_runtime import RuntimeTests  # noqa: E402,F401

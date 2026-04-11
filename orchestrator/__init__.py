"""ADK `adk eval orchestrator` loads this file and expects `agent.root_agent`."""

import importlib.util
from pathlib import Path

_pkg = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(f"{_pkg.name}.agent", _pkg / "agent.py")
agent = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(agent)

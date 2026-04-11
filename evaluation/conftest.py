"""Pytest fixtures shared across all evaluation modules.

Agents are loaded from the registry (agents.yaml), not hardcoded here.
"""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVAL_DIR = pathlib.Path(__file__).resolve().parent
GOLDEN_DIR = EVAL_DIR / "golden"
CONFIG_PATH = EVAL_DIR / "test_config.json"
AGENTS_YAML = ROOT / "agents.yaml"


def pytest_addoption(parser):
    parser.addoption(
        "--log-path",
        default=None,
        help="Path to OTEL JSONL (default: first existing of otel_logs/otel.log, otel.log under repo root)",
    )


def _criteria_threshold(criteria: dict, key: str) -> float:
    v = criteria.get(key)
    if isinstance(v, dict):
        return float(v.get("threshold", 0.0))
    if v is None:
        return 0.0
    return float(v)


@pytest.fixture(scope="session")
def eval_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def agents_yaml() -> dict:
    with AGENTS_YAML.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def specialist_tools(agents_yaml) -> dict[str, list[str]]:
    return {s["name"]: list(s.get("tools", [])) for s in agents_yaml["specialists"]}


@pytest.fixture(scope="session")
def specialist_service_names(agents_yaml) -> list[str]:
    return [s["service_name"] for s in agents_yaml["specialists"]]


@pytest.fixture(scope="session")
def trajectory_threshold(eval_config) -> float:
    return _criteria_threshold(eval_config["criteria"], "tool_trajectory_avg_score")


def load_agent_golden(agent_dir_name: str) -> dict:
    path = GOLDEN_DIR / agent_dir_name / "evalset.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def otel_log_path(request) -> pathlib.Path:
    raw = request.config.getoption("--log-path")
    if raw:
        return pathlib.Path(raw)
    for candidate in (ROOT / "otel_logs" / "otel.log", ROOT / "otel.log"):
        if candidate.is_file():
            return candidate
    return ROOT / "otel_logs" / "otel.log"


@pytest.fixture(scope="session")
def traces(otel_log_path):
    from evaluation.trace_eval.trace_analyzer import analyze, parse_otel_log

    if not otel_log_path.exists():
        pytest.skip(f"No trace log at {otel_log_path}. Run the swarm first.")
    return analyze(parse_otel_log(otel_log_path))

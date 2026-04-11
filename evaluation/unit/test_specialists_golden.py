"""Registry-driven golden checks for all specialists (scales with agents.yaml).

Add a specialist: extend ``agents.yaml`` with ``eval_package`` and add
``evaluation/golden/<eval_package>/evalset.json``.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from evaluation.conftest import load_agent_golden
from evaluation.lib.golden_io import reference_text_from_turn, tool_names_from_turn
from evaluation.lib.trajectory import average_scores, score_tool_trajectory_in_order

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def _specialist_rows():
    cfg = yaml.safe_load((ROOT / "agents.yaml").read_text(encoding="utf-8"))
    return [(s["name"], s["eval_package"], list(s.get("tools", []))) for s in cfg["specialists"]]


@pytest.mark.parametrize(
    "agent_name,eval_pkg,expected_tools",
    _specialist_rows(),
    ids=lambda r: r[0],
)
class TestSpecialistGoldenTrajectory:
    def test_golden_dataset_loaded(self, agent_name, eval_pkg, expected_tools):
        del agent_name, expected_tools
        golden = load_agent_golden(eval_pkg)
        assert "eval_cases" in golden and len(golden["eval_cases"]) > 0

    def test_registry_tools_match_agent(self, agent_name, eval_pkg, expected_tools, specialist_tools):
        del eval_pkg
        assert specialist_tools[agent_name] == expected_tools

    def test_each_turn_tool_order(self, agent_name, eval_pkg, expected_tools):
        del agent_name
        golden = load_agent_golden(eval_pkg)
        for case in golden["eval_cases"]:
            for turn in case["conversation"]:
                actual = tool_names_from_turn(turn)
                assert score_tool_trajectory_in_order(actual, expected_tools) == 1.0, (
                    f"{eval_pkg} case {case['eval_id']}: tools not IN_ORDER vs registry {expected_tools}"
                )

    def test_references_non_empty(self, agent_name, eval_pkg, expected_tools):
        del agent_name, expected_tools
        golden = load_agent_golden(eval_pkg)
        for case in golden["eval_cases"]:
            for turn in case["conversation"]:
                assert reference_text_from_turn(turn).strip(), f"{case['eval_id']} missing reference"

    def test_trajectory_threshold_aggregate(self, agent_name, eval_pkg, expected_tools, trajectory_threshold):
        del agent_name
        golden = load_agent_golden(eval_pkg)
        scores = []
        for case in golden["eval_cases"]:
            for turn in case["conversation"]:
                actual = tool_names_from_turn(turn)
                scores.append(score_tool_trajectory_in_order(actual, expected_tools))
        avg = average_scores(scores)
        assert avg >= trajectory_threshold, (
            f"{eval_pkg} trajectory avg {avg:.2f} < {trajectory_threshold}"
        )

"""Integration evaluation for the full swarm trajectory.

Requires Docker swarm: ``docker compose up -d``

    adk eval orchestrator evaluation/golden/swarm/trajectory_evalset.json \\
        --config evaluation/test_config.json

    pytest evaluation/integration/test_swarm_trajectory.py -v
"""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml

from evaluation.lib.golden_io import reference_text_from_turn, tool_names_from_turn
from evaluation.lib.registry_maps import full_swarm_expected_tool_order
from evaluation.lib.trajectory import average_scores, score_tool_trajectory_in_order
from shared.vote_vocabulary import CANONICAL_VOTES

EVAL_DIR = pathlib.Path(__file__).resolve().parent.parent
ROOT = EVAL_DIR.parent

VALID_VERDICTS = CANONICAL_VOTES


@pytest.fixture(scope="module")
def golden() -> dict:
    path = EVAL_DIR / "golden" / "swarm" / "trajectory_evalset.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def registry() -> dict:
    with (ROOT / "agents.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestSwarmIntegration:

    def test_golden_dataset_loaded(self, golden):
        assert len(golden["eval_cases"]) >= 1

    def test_all_specialist_tools_present_in_full_trajectory(self, golden, specialist_tools):
        all_expected = []
        for tools in specialist_tools.values():
            all_expected.extend(tools)

        for case in golden["eval_cases"]:
            for turn in case["conversation"]:
                actual_tools = tool_names_from_turn(turn)
                for tool in all_expected:
                    assert tool in actual_tools, (
                        f"Case {case['eval_id']}: tool '{tool}' missing from swarm trajectory."
                    )

    def test_cast_vote_called_once_per_specialist(self, golden, specialist_tools):
        n_specialists = len(specialist_tools)
        for case in golden["eval_cases"]:
            for turn in case["conversation"]:
                all_tools = tool_names_from_turn(turn)
                vote_count = all_tools.count("cast_vote")
                assert vote_count == n_specialists, (
                    f"Case {case['eval_id']}: expected {n_specialists} cast_vote, found {vote_count}."
                )

    def test_trajectory_score_meets_threshold(self, golden, registry, trajectory_threshold):
        all_expected = full_swarm_expected_tool_order(registry)
        scores = []
        for case in golden["eval_cases"]:
            for turn in case["conversation"]:
                actual = tool_names_from_turn(turn)
                scores.append(score_tool_trajectory_in_order(actual, all_expected))

        avg = average_scores(scores)
        assert avg >= trajectory_threshold, (
            f"Swarm integration trajectory score {avg:.2f} is below threshold {trajectory_threshold}."
        )

    def test_final_verdict_in_reference(self, golden):
        for case in golden["eval_cases"]:
            for turn in case["conversation"]:
                reference = reference_text_from_turn(turn)
                found = [v for v in VALID_VERDICTS if v in reference]
                assert found, (
                    f"Case {case['eval_id']}: reference must contain a valid verdict "
                    f"from {VALID_VERDICTS}."
                )

    def test_swarm_golden_matches_registry_tool_union(self, registry, specialist_tools):
        """Swarm golden must list every tool from every specialist (order = registry order)."""
        combined = full_swarm_expected_tool_order(registry)
        for s in specialist_tools.values():
            for t in s:
                assert t in combined

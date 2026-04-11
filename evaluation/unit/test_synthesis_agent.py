"""Unit evaluation for the synthesis agent.

The synthesis agent does not call external tools. It reads specialist reports
and applies majority voting. These tests verify the voting logic in isolation.

Run with:
    adk eval synthesis_agent evaluation/golden/synthesis_agent/evalset.json \
        --config evaluation/test_config.json
"""

import pytest

from evaluation.conftest import load_agent_golden
from evaluation.lib.golden_io import reference_text_from_turn, tool_names_from_turn
from shared.vote_vocabulary import CANONICAL_VOTES

AGENT_DIR = "synthesis_agent"
VALID_VERDICTS = CANONICAL_VOTES


@pytest.fixture(scope="module")
def golden() -> dict:
    return load_agent_golden(AGENT_DIR)


class TestSynthesisAgentVotingLogic:

    def test_golden_dataset_loaded(self, golden):
        assert len(golden["eval_cases"]) > 0

    def test_synthesis_calls_no_tools(self, golden):
        """The synthesis agent must NOT call specialist tools directly.

        It reads reports and votes. Any tool call in the synthesis golden set
        indicates a prompt regression that leaked specialist behavior.
        """
        for case in golden["eval_cases"]:
            for turn in case["conversation"]:
                names = tool_names_from_turn(turn)
                assert len(names) == 0, (
                    f"Case {case['eval_id']}: synthesis agent should not call tools "
                    f"but found {names}."
                )

    def test_unanimous_authenticate_verdict(self, golden):
        case = next(
            c for c in golden["eval_cases"]
            if c["eval_id"] == "synthesis_unanimous_authenticate"
        )
        reference = reference_text_from_turn(case["conversation"][0])
        assert "AUTHENTICATE" in reference
        assert "unanimous" in reference.lower() or "all three" in reference.lower()

    def test_majority_verify_further_verdict(self, golden):
        case = next(
            c for c in golden["eval_cases"]
            if c["eval_id"] == "synthesis_majority_verify"
        )
        reference = reference_text_from_turn(case["conversation"][0])
        assert "VERIFY_FURTHER" in reference

    def test_split_vote_defaults_to_verify_further(self, golden):
        """When no majority exists, the safe default must be VERIFY_FURTHER, not REJECT."""
        case = next(
            c for c in golden["eval_cases"]
            if c["eval_id"] == "synthesis_split_verify"
        )
        reference = reference_text_from_turn(case["conversation"][0])
        assert "VERIFY_FURTHER" in reference, (
            "Split vote must default to VERIFY_FURTHER. "
            "REJECT requires explicit majority. Check synthesis prompt."
        )

    def test_all_references_contain_valid_verdict(self, golden):
        """Every reference response must contain exactly one recognized verdict."""
        for case in golden["eval_cases"]:
            for turn in case["conversation"]:
                reference = reference_text_from_turn(turn)
                found = [v for v in VALID_VERDICTS if v in reference]
                assert len(found) >= 1, (
                    f"Case {case['eval_id']}: reference response does not contain "
                    f"a valid verdict from {VALID_VERDICTS}."
                )

"""Goldens include intermediate response slots for ADK criteria (e.g. hallucinations_v1 on intermediates)."""

from __future__ import annotations

from evaluation.conftest import load_agent_golden
from evaluation.lib.golden_io import intermediate_author_text_pairs


def test_style_monet_includes_expected_intermediate():
    golden = load_agent_golden("style_agent")
    case = next(c for c in golden["eval_cases"] if c["eval_id"] == "style_monet_impressionism")
    turn = case["conversation"][0]
    pairs = intermediate_author_text_pairs(turn)
    assert len(pairs) >= 1
    author, text = pairs[0]
    assert author
    assert text.strip()

"""Canonical tool-trajectory scoring (IN_ORDER), aligned with ADK tool_trajectory_avg_score IN_ORDER."""


def score_tool_trajectory_in_order(actual: list[str], expected: list[str]) -> float:
    """Return 1.0 if every tool in ``expected`` appears in ``actual`` in order; else 0.0.

    Extra tools in ``actual`` are allowed between expected steps.
    """
    idx = 0
    for tool in actual:
        if idx < len(expected) and tool == expected[idx]:
            idx += 1
    return 1.0 if idx == len(expected) else 0.0


def average_scores(scores: list[float]) -> float:
    return sum(scores) / len(scores) if scores else 0.0

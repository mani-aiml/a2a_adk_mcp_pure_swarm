"""Scale evaluation: parametrize eval across N agents from the registry.

This test verifies that the evaluation framework itself scales alongside the swarm.
When agents.yaml grows from 3 to 50 or 100 specialists, this test loop covers them all
without any hardcoded agent names in the test logic.

The registry is the single source of truth. The test parameters come from agents.yaml,
not from a list inside this file. Adding a new specialist to agents.yaml automatically
adds it to every parametrized test here.

Design principle: The same pattern that makes the swarm scalable (config-driven registry)
makes the evaluation scalable (registry-driven parametrization).

Run:
    pytest evaluation/integration/test_swarm_at_scale.py -v
"""

import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def load_specialists() -> list[dict]:
    with (ROOT / "agents.yaml").open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg["specialists"]


SPECIALISTS = load_specialists()


class TestRegistryDrivenEvalScale:
    """All tests here use pytest.mark.parametrize with the registry.

    To add agent 51: add it to agents.yaml. No changes needed here.
    """

    @pytest.mark.parametrize("specialist", SPECIALISTS, ids=[s["name"] for s in SPECIALISTS])
    def test_every_specialist_has_tools_declared(self, specialist):
        """Every specialist in the registry must declare at least one tool.

        An agent with no tools cannot participate in evaluation.
        """
        tools = specialist.get("tools", [])
        assert len(tools) >= 1, (
            f"Specialist '{specialist['name']}' has no tools declared in agents.yaml. "
            f"Add at least one tool for evaluation to be meaningful."
        )

    @pytest.mark.parametrize("specialist", SPECIALISTS, ids=[s["name"] for s in SPECIALISTS])
    def test_every_specialist_has_cast_vote(self, specialist):
        """Every specialist must include cast_vote as its final tool.

        Removing cast_vote from any specialist breaks the quorum pattern.
        This test catches that regression for any agent, at any scale.
        """
        tools = specialist.get("tools", [])
        assert "cast_vote" in tools, (
            f"Specialist '{specialist['name']}' is missing cast_vote. "
            f"All specialists must vote for the quorum pattern to work."
        )
        assert tools[-1] == "cast_vote", (
            f"Specialist '{specialist['name']}': cast_vote must be the last tool. "
            f"Found tool order: {tools}."
        )

    @pytest.mark.parametrize("specialist", SPECIALISTS, ids=[s["name"] for s in SPECIALISTS])
    def test_every_specialist_has_service_name(self, specialist):
        """Every specialist must have a Docker service name for A2A routing."""
        assert specialist.get("service_name"), (
            f"Specialist '{specialist['name']}' is missing service_name. "
            f"Required for Docker DNS routing."
        )

    @pytest.mark.parametrize("specialist", SPECIALISTS, ids=[s["name"] for s in SPECIALISTS])
    def test_every_specialist_has_description(self, specialist):
        """Agent descriptions must be non-empty.

        The synthesis agent uses specialist descriptions to route reports correctly.
        An empty description causes silent routing errors at scale.
        """
        desc = specialist.get("description", "").strip()
        assert desc, (
            f"Specialist '{specialist['name']}' has an empty description. "
            f"Descriptions are required for synthesis routing."
        )

    def test_total_specialist_count(self):
        """Track the total specialist count for scale awareness.

        This test always passes but prints the current count for observability.
        At 50 and 100 agents, infrastructure limits (MCP server, LLM rate limits)
        become the constraint, not the evaluation framework.
        """
        count = len(SPECIALISTS)
        print(f"\nCurrent specialist count: {count}")
        if count >= 50:
            print(
                f"  Scale note: at {count} agents, verify MCP server replication "
                f"and LLM API rate limit configuration."
            )
        assert count >= 1

    def test_no_duplicate_service_names(self):
        """All service_name values must be unique.

        Duplicate service names cause A2A routing collisions. At scale, this
        is the most common configuration mistake when adding new agents.
        """
        service_names = [s["service_name"] for s in SPECIALISTS]
        duplicates = {n for n in service_names if service_names.count(n) > 1}
        assert not duplicates, (
            f"Duplicate service names found: {duplicates}. "
            f"Each specialist must have a unique Docker service name."
        )

    def test_no_duplicate_agent_names(self):
        """All agent name values must be unique."""
        names = [s["name"] for s in SPECIALISTS]
        duplicates = {n for n in names if names.count(n) > 1}
        assert not duplicates, (
            f"Duplicate agent names found: {duplicates}."
        )

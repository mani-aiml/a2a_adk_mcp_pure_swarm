import os

from google.adk.agents import ParallelAgent, SequentialAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from shared.registry import AGENT_PORT

# Same listen port as agents.yaml / Docker Compose (8080). Defaults assume localhost;
# for the real swarm use Docker DNS URLs via env (see docker-compose.yml / orchestrator).
_DEFAULT_BASE = f"http://localhost:{AGENT_PORT}"

_CARD = "/.well-known/agent-card.json"

remote_style = RemoteA2aAgent(
    name="style_analyst",
    description="Specialist in artistic style, technique, and physical condition analysis.",
    agent_card=os.environ.get("STYLE_AGENT_URL", _DEFAULT_BASE) + _CARD,
)

remote_provenance = RemoteA2aAgent(
    name="provenance_specialist",
    description="Specialist in artwork provenance, ownership history, authenticity, and legal restrictions.",
    agent_card=os.environ.get("PROVENANCE_AGENT_URL", _DEFAULT_BASE) + _CARD,
)

remote_valuation = RemoteA2aAgent(
    name="market_valuator",
    description="Specialist in art market valuation, auction comparables, and insurance value.",
    agent_card=os.environ.get("VALUATION_AGENT_URL", _DEFAULT_BASE) + _CARD,
)

remote_synthesis = RemoteA2aAgent(
    name="synthesis_agent",
    description="Chief appraiser: applies majority voting across specialist reports and issues the final verdict.",
    agent_card=os.environ.get("SYNTHESIS_AGENT_URL", _DEFAULT_BASE) + _CARD,
)


parallel_evaluation = ParallelAgent(
    name="parallel_evaluation",
    description="Runs all three specialists simultaneously — each sees only the user's query.",
    sub_agents=[remote_style, remote_provenance, remote_valuation],
)

art_appraisal_pipeline = SequentialAgent(
    name="art_appraisal_pipeline",
    description="Full unbiased art appraisal: parallel independent evaluation → majority-vote synthesis.",
    sub_agents=[parallel_evaluation, remote_synthesis],
)

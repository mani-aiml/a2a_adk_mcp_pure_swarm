import os

from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from shared.registry import SPECIALISTS, SYNTHESIS, PIPELINE, PARALLEL, endpoint_url

_CARD = "/.well-known/agent-card.json"


def _env_key(name: str) -> str:
    return f"{name.upper()}_URL"


def _remote(entry) -> RemoteA2aAgent:
    base_url = os.environ.get(_env_key(entry.name), endpoint_url(entry))
    return RemoteA2aAgent(
        name=entry.name,
        description=entry.description,
        agent_card=base_url + _CARD,
    )


_specialist_agents = [_remote(s) for s in SPECIALISTS]
_synthesis_agent = _remote(SYNTHESIS)

parallel_evaluation = ParallelAgent(
    name=PARALLEL.name,
    description="Runs all specialists simultaneously — each sees only the user's query.",
    sub_agents=_specialist_agents,
)

art_appraisal_pipeline = SequentialAgent(
    name=PIPELINE.name,
    description="Full unbiased art appraisal: parallel independent evaluation -> majority-vote synthesis.",
    sub_agents=[parallel_evaluation, _synthesis_agent],
)

root_agent = art_appraisal_pipeline

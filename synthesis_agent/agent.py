from pathlib import Path
from shared.config import bootstrap, DEFAULT_MODEL, AGENT_HOST
bootstrap()

from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

_PROMPT = Path(__file__).parent.joinpath("prompt.txt").read_text()

synthesis_agent = Agent(
    name="synthesis_agent",
    model=DEFAULT_MODEL,
    description=(
        "Chief appraiser: reads all specialist reports, extracts votes, "
        "applies majority voting, and issues the final appraisal verdict."
    ),
    instruction=_PROMPT,
)

a2a_app = to_a2a(synthesis_agent, port=8004)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host=AGENT_HOST, port=8004)

from pathlib import Path
from shared.config import bootstrap, DEFAULT_MODEL, MCP_SERVER_URL, AGENT_HOST
bootstrap()

from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

_PROMPT = Path(__file__).parent.joinpath("prompt.txt").read_text()

market_valuator = Agent(
    name="market_valuator",
    model=DEFAULT_MODEL,
    description=(
        "Specialist in art market valuation, recent auction comparables, "
        "and insurance value estimation."
    ),
    instruction=_PROMPT,
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(url=MCP_SERVER_URL),
            tool_filter=["get_auction_comparables", "estimate_insurance_value", "cast_vote"],
        )
    ],
)

a2a_app = to_a2a(market_valuator, port=8002)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host=AGENT_HOST, port=8002)

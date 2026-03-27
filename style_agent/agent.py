from pathlib import Path
from shared.config import bootstrap, DEFAULT_MODEL, MCP_SERVER_URL, AGENT_HOST
bootstrap()

from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

_PROMPT = Path(__file__).parent.joinpath("prompt.txt").read_text()

style_analyst = Agent(
    name="style_analyst",
    model=DEFAULT_MODEL,
    description=(
        "Specialist in art history, artistic style, technique, and medium analysis. "
        "Analyzes style, movement, technique, and physical condition of artworks."
    ),
    instruction=_PROMPT,
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(url=MCP_SERVER_URL),
            tool_filter=["analyze_style", "assess_condition_factors", "cast_vote"],
        )
    ],
)

a2a_app = to_a2a(style_analyst, port=8000)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host=AGENT_HOST, port=8000)

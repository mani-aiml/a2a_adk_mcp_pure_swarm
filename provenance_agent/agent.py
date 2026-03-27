from pathlib import Path
from shared.config import bootstrap, DEFAULT_MODEL, MCP_SERVER_URL, AGENT_HOST
bootstrap()

from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

_PROMPT = Path(__file__).parent.joinpath("prompt.txt").read_text()

provenance_specialist = Agent(
    name="provenance_specialist",
    model=DEFAULT_MODEL,
    description=(
        "Specialist in artwork provenance, ownership history, authenticity "
        "verification, and legal/export restrictions."
    ),
    instruction=_PROMPT,
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(url=MCP_SERVER_URL),
            tool_filter=["check_provenance", "check_export_restrictions", "cast_vote"],
        )
    ],
)

a2a_app = to_a2a(provenance_specialist, port=8001)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host=AGENT_HOST, port=8001)

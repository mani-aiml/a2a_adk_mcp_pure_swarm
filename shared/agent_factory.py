"""Factory for building specialist A2A agents from registry config."""

from pathlib import Path

from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

from shared.config import DEFAULT_MODEL, MCP_SERVER_URL, AGENT_HOST
from shared.registry import AgentEntry, AGENT_PORT


def _a2a_host(entry: AgentEntry) -> str:
    """Advertised hostname for the agent card.

    In Docker (AGENT_HOST=0.0.0.0), use the service name so other containers
    can reach this agent. For local dev (AGENT_HOST=localhost), keep localhost.
    """
    if AGENT_HOST in ("0.0.0.0", ""):
        return entry.service_name
    return AGENT_HOST


def build_specialist(entry: AgentEntry, prompt_dir: Path) -> tuple:
    """Build an ADK Agent + A2A app for a specialist entry.

    Returns (agent, a2a_app) tuple.
    """
    prompt = prompt_dir.joinpath("prompt.txt").read_text()
    tools = []
    if entry.tools:
        tools.append(
            McpToolset(
                connection_params=StreamableHTTPConnectionParams(url=MCP_SERVER_URL),
                tool_filter=entry.tools,
            )
        )
    agent = Agent(
        name=entry.name,
        model=DEFAULT_MODEL,
        description=entry.description,
        instruction=prompt,
        tools=tools,
    )
    return agent, to_a2a(agent, host=_a2a_host(entry), port=AGENT_PORT)


def build_synthesis(entry: AgentEntry, prompt_dir: Path) -> tuple:
    """Build the synthesis agent (no MCP tools)."""
    prompt = prompt_dir.joinpath("prompt.txt").read_text()
    agent = Agent(
        name=entry.name,
        model=DEFAULT_MODEL,
        description=entry.description,
        instruction=prompt,
    )
    return agent, to_a2a(agent, host=_a2a_host(entry), port=AGENT_PORT)


def run_agent_server(a2a_app) -> None:
    import uvicorn
    uvicorn.run(a2a_app, host="0.0.0.0", port=AGENT_PORT)

"""Single source of truth for agent metadata, loaded from agents.yaml."""

import pathlib
from dataclasses import dataclass, field
from typing import Any

import yaml

_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "agents.yaml"

RESET = "\033[0m"
BOLD = "\033[1m"


@dataclass(frozen=True)
class AgentEntry:
    name: str
    description: str
    service_name: str
    label: str
    color: str
    tools: list[str] = field(default_factory=list)


def _load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_registry() -> tuple[list[AgentEntry], AgentEntry, AgentEntry, AgentEntry, int, str]:
    cfg = _load_config()
    agent_port = cfg["agent_port"]
    mcp_service = cfg["mcp"]["service_name"]

    specialists = [
        AgentEntry(
            name=s["name"],
            service_name=s["service_name"],
            description=s["description"],
            label=s["label"],
            color=s["color"],
            tools=s.get("tools", []),
        )
        for s in cfg["specialists"]
    ]
    synthesis = AgentEntry(
        name=cfg["synthesis"]["name"],
        service_name=cfg["synthesis"]["service_name"],
        description=cfg["synthesis"]["description"],
        label=cfg["synthesis"]["label"],
        color=cfg["synthesis"]["color"],
    )
    pipeline = AgentEntry(
        name=cfg["pipeline"]["name"],
        service_name="",
        description="",
        label=cfg["pipeline"]["label"],
        color=cfg["pipeline"]["color"],
    )
    parallel = AgentEntry(
        name=cfg["parallel"]["name"],
        service_name="",
        description="",
        label=cfg["parallel"]["label"],
        color=cfg["parallel"]["color"],
    )
    return specialists, synthesis, pipeline, parallel, agent_port, mcp_service


SPECIALISTS, SYNTHESIS, PIPELINE, PARALLEL, AGENT_PORT, MCP_SERVICE_NAME = _build_registry()

SPECIALIST_NAMES: set[str] = {s.name for s in SPECIALISTS}

AGENT_COLORS: dict[str, str] = {
    entry.name: entry.color
    for entry in [PIPELINE, PARALLEL, *SPECIALISTS, SYNTHESIS]
}

AGENT_META: dict[str, tuple[str, str]] = {
    PIPELINE.name: (PIPELINE.label, "SequentialAgent"),
    PARALLEL.name: (PARALLEL.label, "ParallelAgent"),
    **{s.name: (s.label, f"A2A {s.service_name}") for s in SPECIALISTS},
    SYNTHESIS.name: (SYNTHESIS.label, f"A2A {SYNTHESIS.service_name}"),
}


def endpoint_url(entry: AgentEntry) -> str:
    """Docker DNS endpoint: http://{service_name}:{AGENT_PORT}"""
    return f"http://{entry.service_name}:{AGENT_PORT}"


def mcp_url() -> str:
    """MCP server endpoint using Docker service name."""
    cfg = _load_config()
    mcp_port = cfg["mcp_port"]
    return f"http://{MCP_SERVICE_NAME}:{mcp_port}/mcp"

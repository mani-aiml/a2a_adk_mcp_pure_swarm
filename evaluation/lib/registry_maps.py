"""Maps derived from agents.yaml for tests (single source of truth)."""

from __future__ import annotations

from typing import Any


def specialist_tool_map(agents_yaml: dict[str, Any]) -> dict[str, list[str]]:
    return {s["name"]: list(s.get("tools", [])) for s in agents_yaml["specialists"]}


def full_swarm_expected_tool_order(agents_yaml: dict[str, Any]) -> list[str]:
    """Ordered concatenation of each specialist's tools (registry order = parallel stage order in golden)."""
    order: list[str] = []
    for s in agents_yaml["specialists"]:
        order.extend(s.get("tools", []))
    return order


def trace_service_names(agents_yaml: dict[str, Any]) -> list[str]:
    """Docker OTEL service.name values: specialists + synthesis + orchestrator CLI."""
    names = [s["service_name"] for s in agents_yaml["specialists"]]
    names.append(agents_yaml["synthesis"]["service_name"])
    names.append("orchestrator")
    return names


def specialist_trace_services(agents_yaml: dict[str, Any]) -> list[str]:
    specialists = [s["service_name"] for s in agents_yaml["specialists"]]
    specialists.append(agents_yaml["synthesis"]["service_name"])
    return specialists

"""Read ADK-native eval golden conversation turns (JSON on disk).

Goldens use ``Invocation``-shaped objects: ``final_response``, ``intermediate_data``,
etc. See https://google.github.io/adk-docs/evaluate/ and ``EvalSet`` in google-adk.
"""

from __future__ import annotations

from typing import Any


def tool_names_from_turn(turn: dict[str, Any]) -> list[str]:
    """Expected tool call names in order (from ``intermediate_data.tool_uses``)."""
    legacy = turn.get("expected_tool_use")
    if legacy is not None:
        return [t["tool_name"] for t in legacy]
    data = turn.get("intermediate_data") or {}
    return [u["name"] for u in data.get("tool_uses") or []]


def reference_text_from_turn(turn: dict[str, Any]) -> str:
    """Golden final model text (``final_response.parts`` or legacy ``reference``)."""
    if "reference" in turn:
        return str(turn["reference"])
    fr = turn.get("final_response") or {}
    parts = fr.get("parts") or []
    return "".join(str(p.get("text") or "") for p in parts)


def intermediate_author_text_pairs(turn: dict[str, Any]) -> list[tuple[str, str]]:
    """Pairs of (author, flattened text) for intermediate NL expectations."""
    legacy = turn.get("expected_intermediate_agent_responses")
    if legacy is not None:
        out: list[tuple[str, str]] = []
        for item in legacy:
            if not isinstance(item, dict):
                continue
            author = item.get("author", "")
            content = item.get("content") or {}
            parts = content.get("parts") or []
            text = "".join(str(p.get("text") or "") for p in parts)
            out.append((author, text))
        return out
    data = turn.get("intermediate_data") or {}
    raw = data.get("intermediate_responses") or []
    pairs: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        author, part_list = item[0], item[1]
        text = "".join(str(p.get("text") or "") for p in (part_list or []))
        pairs.append((str(author), text))
    return pairs

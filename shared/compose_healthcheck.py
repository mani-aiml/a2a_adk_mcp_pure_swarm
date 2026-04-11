#!/usr/bin/env python3
"""Docker Compose healthcheck: TCP connect to agent_port from agents.yaml on 127.0.0.1.

Keeps healthchecks aligned with shared/registry AGENT_PORT (no hardcoded 8080 vs 8003 drift).
"""
from __future__ import annotations

import pathlib
import socket
import sys

import yaml


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    cfg = yaml.safe_load((root / "agents.yaml").read_text(encoding="utf-8"))
    port = int(cfg["agent_port"])
    socket.create_connection(("127.0.0.1", port), timeout=5).close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

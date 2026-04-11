#!/usr/bin/env python3
"""Print eval_package names from agents.yaml (specialists then synthesis), one per line."""

from __future__ import annotations

import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    cfg = yaml.safe_load((ROOT / "agents.yaml").read_text(encoding="utf-8"))
    for s in cfg["specialists"]:
        print(s["eval_package"])
    print(cfg["synthesis"]["eval_package"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

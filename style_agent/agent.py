from pathlib import Path
from shared.config import bootstrap
bootstrap()

from shared.registry import SPECIALISTS
from shared.agent_factory import build_specialist, run_agent_server

_entry = next(s for s in SPECIALISTS if s.name == "style_analyst")
style_analyst, a2a_app = build_specialist(_entry, Path(__file__).parent)
root_agent = style_analyst

if __name__ == "__main__":
    run_agent_server(a2a_app)

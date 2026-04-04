from pathlib import Path
from shared.config import bootstrap
bootstrap()

from shared.registry import SYNTHESIS
from shared.agent_factory import build_synthesis, run_agent_server

synthesis_agent, a2a_app = build_synthesis(SYNTHESIS, Path(__file__).parent)

if __name__ == "__main__":
    run_agent_server(a2a_app)

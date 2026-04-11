import logging
import os
import warnings

from dotenv import load_dotenv

load_dotenv()

from google.adk.models import LiteLlm

DEFAULT_MODEL = LiteLlm(
    model="openai/nova-2-lite-v1",
    api_key=os.environ.get("NOVA_API_KEY"),
    api_base="https://api.nova.amazon.com/v1",
)

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080/mcp")
AGENT_HOST = os.environ.get("AGENT_HOST", "localhost")


def bootstrap() -> None:
    warnings.filterwarnings("ignore", category=UserWarning, module=r"google\.adk")
    warnings.filterwarnings("ignore", message=r".*EXPERIMENTAL.*")
    warnings.filterwarnings("ignore", message=r".*non-text parts.*")
    warnings.filterwarnings("ignore", message=r".*Deprecated agent card.*")
    logging.getLogger("google_genai.types").setLevel(logging.ERROR)
    # OpenTelemetry must be configured before ADK creates spans (one TracerProvider per process).
    from otel_setup import setup_otel_tracing

    setup_otel_tracing()

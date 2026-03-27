import logging
import os
import warnings

from dotenv import load_dotenv
load_dotenv()  # Must run before LiteLlm reads BEDROCK_API_KEY from env

from google.adk.models import LiteLlm

DEFAULT_MODEL = LiteLlm(
    model="openai/nova-2-lite-v1",
    api_key=os.environ.get("NOVA_API_KEY"),
    api_base="https://api.nova.amazon.com/v1",
)

MCP_SERVER_URL  = os.environ.get("MCP_SERVER_URL", "http://localhost:8003/mcp")
MCP_SERVER_PORT = int(os.environ.get("MCP_SERVER_PORT", "8003"))
AGENT_HOST      = os.environ.get("AGENT_HOST", "localhost")


def suppress_adk_warnings() -> None:
    warnings.filterwarnings("ignore", category=UserWarning, module=r"google\.adk")
    warnings.filterwarnings("ignore", message=r".*EXPERIMENTAL.*")
    warnings.filterwarnings("ignore", message=r".*non-text parts.*")
    warnings.filterwarnings("ignore", message=r".*Deprecated agent card.*")
    logging.getLogger("google_genai.types").setLevel(logging.ERROR)


def load_env() -> None:
    load_dotenv()


def bootstrap() -> None:
    suppress_adk_warnings()
    load_env()


def check_api_key() -> bool:
    return bool(os.environ.get("NOVA_API_KEY"))

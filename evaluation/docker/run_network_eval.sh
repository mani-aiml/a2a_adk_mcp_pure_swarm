#!/usr/bin/env bash
# Run the evaluation suite with URLs pointing at the Docker Compose network.
# Used by the eval-runner service (see docker-compose.yml, profile: eval).

set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH="${PYTHONPATH:-.}"

: "${MCP_SERVER_URL:=http://mcp-server:8080/mcp}"
export MCP_SERVER_URL

# LiteLLM env vars for the judge model (openai/nova-2-lite-v1).
# ADK's _setup_auto_rater creates LiteLlm(model=...) without api_key/api_base,
# so LiteLLM falls back to these env vars for openai/-prefixed providers.
export OPENAI_API_KEY="${NOVA_API_KEY}"
export OPENAI_API_BASE="https://api.nova.amazon.com/v1"

# orchestrator/agent.py RemoteA2aAgent bases (registry name -> STYLE_ANALYST_URL, etc.)
: "${STYLE_ANALYST_URL:=http://style-agent:8080}"
: "${PROVENANCE_SPECIALIST_URL:=http://provenance-agent:8080}"
: "${MARKET_VALUATOR_URL:=http://valuation-agent:8080}"
: "${SYNTHESIS_AGENT_URL:=http://synthesis-agent:8080}"
export STYLE_ANALYST_URL PROVENANCE_SPECIALIST_URL MARKET_VALUATOR_URL SYNTHESIS_AGENT_URL

exec ./evaluation/run_evals.sh "$@"

# Art Appraisal Swarm

A multiagent art appraisal system built with Google ADK, A2A protocol, and MCP —
running on **Amazon Nova**. Three independent specialist agents evaluate an artwork
in parallel, then a synthesis agent applies majority voting to produce a final
recommendation.

**Author:** [Mani Khanuja](https://manikhanuja.com) — [Substack](https://manikhanuja.substack.com)

> The framework (Google ADK), the inter-agent protocol (A2A), and the tool layer (MCP)
> are completely decoupled from the model provider. The entire swarm runs on Amazon
> Nova with zero changes to agent logic, prompts, or protocols.
> It showcases that you can use **Amazon Bedrock Nova** models with any framework and its compatible with standard protocols such MCP and A2A.

## Prerequisites

- Python 3.12+
- Docker Desktop
- A Nova API key from [nova.amazon.com/dev/api](https://nova.amazon.com/dev/api) — sign in
  with your Amazon account, no AWS account required.

## Setup

```bash
git clone <your-repo-url>
cd nova_adk_a2a_mcp_swarm

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pre-commit

# Configure credentials
cp .env.example .env
# Edit .env and set your NOVA_API_KEY

# Install pre-commit hooks (runs secret scan on every commit)
pre-commit install
```

## Run

```bash
# Build and start all five services
docker compose build
docker compose up -d

# Run the orchestrator
python main.py

# Stop everything when done
docker compose down
```

## Architecture

Five independent services, each in its own container:

| Service               | Port | Role                           |
|-----------------------|------|--------------------------------|
| MCP Tool Server       | 8003 | Shared tools for all agents    |
| Style Analyst         | 8000 | Style, technique, condition    |
| Provenance Specialist | 8001 | Ownership history, legal       |
| Market Valuator       | 8002 | Auction comparables, insurance |
| Synthesis Agent       | 8004 | Majority vote, final verdict   |

## Example query

```
You: Appraise a Monet Water Lilies, oil on canvas, 80x100cm, painted in 1906.
     Acquired via Christie's London 1989 (Lot 42). Condition good, minor craquelure.
     Country of origin: France.
```

## Article Series

This repo accompanies a multi-part Substack series on building production
multiagent systems with Google ADK, A2A, and MCP.

| Tag | Article | What it covers |
|-----|---------|----------------|
| `part-1` | Part 1: Architecture & Swarm Voting | A2A services, MCP tools, parallel voting, OTEL, Docker, Bedrock Nova |
| `part-2` | Part 2: Evaluation *(coming soon)* | Golden test cases, LLM-as-judge scoring |
| `part-3` | Part 3: Red-Teaming *(coming soon)* | Prompt injection, vote manipulation |
| `part-4` | Part 4: Production Security *(coming soon)* | Auth, rate-limiting, secrets management |

Checkout any tag to see the code at that stage:
```bash
git checkout part-1
```

## Observability

OTEL traces and logs are written to `otel.log`:

```bash
tail -f otel.log
```

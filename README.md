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
  with your Amazon account, no AWS account required

## Setup

```bash
git clone <your-repo-url>
cd a2a_adk_mcp_pure_swarm

# Configure credentials
cp .env.example .env
# Edit .env and set your NOVA_API_KEY
```

## Run

Everything runs inside Docker — no local Python environment needed.

```bash
# Build all six services (MCP server, 3 specialists, synthesis, orchestrator)
docker compose build

# Start backend services (waits for health checks automatically)
docker compose up -d mcp-server style-agent provenance-agent valuation-agent synthesis-agent

# Run the orchestrator interactively (attaches to stdin for chat)
docker compose run --rm orchestrator

# Stop everything when done
docker compose down
```

### Local development (optional)

For local development with ADK's built-in tools (`adk web`), set up a virtual
environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pre-commit
pre-commit install
```

## Architecture

Six independent services, each in its own container. All services listen on the
same internal port (8080) and communicate by Docker service name — no per-agent
port management required.

| Service               | Docker Service Name  | Role                           |
|-----------------------|----------------------|--------------------------------|
| Orchestrator          | `orchestrator`       | Pipeline coordinator (chat UI) |
| MCP Tool Server       | `mcp-server`         | Shared tools for all agents    |
| Style Analyst         | `style-agent`        | Style, technique, condition    |
| Provenance Specialist | `provenance-agent`   | Ownership history, legal       |
| Market Valuator       | `valuation-agent`    | Auction comparables, insurance |
| Synthesis Agent       | `synthesis-agent`    | Majority vote, final verdict   |

Adding a new specialist agent requires only two changes:
1. Add an entry to `agents.yaml`
2. Create a `<name>_agent/` directory with `prompt.txt` and `agent.py`

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
| `part-1.v2` | Part 1.v2: Refactored for Scale | Config-driven registry, agent factory, uniform ports, Docker service-name routing, production considerations |
| `part-2` | Part 2: Evaluation *(coming soon)* | Golden test cases, LLM-as-judge scoring |
| `part-3` | Part 3: Red-Teaming *(coming soon)* | Prompt injection, vote manipulation |
| `part-4` | Part 4: Production Security *(coming soon)* | Auth, rate-limiting, secrets management |

Checkout any tag to see the code at that stage:
```bash
git checkout part-1      # Original working swarm
git checkout part-1.v2   # Refactored for scalability
```

### What changed from `part-1` to `part-1.v2`

**`part-1`** was a working swarm with hardcoded agent definitions — each agent
had a unique port, agent metadata was duplicated in 4+ files, and adding a new
specialist required editing 6 files.

**`part-1.v2`** refactors for scalability to 100+ agents:

- **Config-driven agent registry** (`agents.yaml` + `shared/registry.py`) — single
  source of truth for all agent metadata. Adding a new agent = one YAML entry +
  one prompt file.
- **Agent factory** (`shared/agent_factory.py`) — eliminates copy-paste across 4
  near-identical agent modules. Each agent module is now <12 lines.
- **Uniform internal port (8080)** — all containers listen on the same port.
  Inter-service communication uses Docker service names (`http://style-agent:8080`)
  instead of unique ports.
- **Orchestrator in Docker** — the orchestrator runs inside Docker with all other
  services, using service-name routing. No host port mapping needed.
- **Dynamic synthesis prompt** — voting logic uses "N specialists" and
  "ceil(N/2)" instead of hardcoded "3 specialists" and "2/3".
- **Dead code removed** — unused functions, redundant `load_dotenv()` calls,
  unused imports cleaned up.
- **Production considerations** — documented all single points of failure (MCP
  server, LLM API key, session state) with mitigation strategies.

## Observability

OTEL traces and logs are written to `otel.log`:

```bash
tail -f otel.log
```

## Production Considerations

This is a **sample/learning project**, not a production deployment. The
architecture demonstrates multi-agent patterns correctly, but several areas
require hardening before production use. Below is a guide to the known single
points of failure (SPOFs) and how to mitigate them.

### 1. MCP Server — shared tool layer (highest risk SPOF)

**The problem:** A single `mcp-server` instance serves all specialist agents. If
it goes down, every specialist fails simultaneously — they cannot call any tools,
produce no useful output, and the synthesis agent receives empty reports.

At scale (100 agents), one MCP server handles hundreds of concurrent tool calls
with no connection pooling or backpressure.

**Production mitigations:**

- **Replicate the MCP server** behind a load balancer (e.g. Nginx, HAProxy, or a
  Kubernetes Service). Since the MCP tools are stateless, any replica can handle
  any request.
- **Add health-aware retries** in each specialist agent. If a tool call fails,
  retry with exponential backoff before giving up. Google ADK supports custom
  tool wrappers where this logic can live.
- **Circuit breaker pattern** — after N consecutive failures, stop calling the
  MCP server for a cooldown period instead of flooding it with retries. Libraries
  like `circuitbreaker` or `tenacity` make this straightforward.
- **Connection pooling** — use persistent HTTP connections between agents and the
  MCP server instead of opening a new connection per tool call. At 100 agents,
  this dramatically reduces TCP overhead.
- **Graceful degradation** — if a specialist cannot reach its tools, it should
  return a partial report with a confidence of 0.0 and vote `VERIFY_FURTHER`,
  rather than failing silently. The synthesis agent already handles missing votes
  this way.

### 2. Single LLM API key / endpoint

**The problem:** All agents share one `DEFAULT_MODEL` pointing to a single API
endpoint (Amazon Nova). If that endpoint has an outage, rate-limits the key, or
the key is revoked, every agent fails simultaneously.

**Production mitigations:**

- **Per-agent or per-tier API keys** — use separate keys for specialists vs.
  synthesis so a rate limit on one tier doesn't cascade to the other.
- **Fallback model configuration** — define a primary and secondary model in
  `agents.yaml`. If the primary returns 429/503, fall back to the secondary
  (e.g. a different region, or a different provider entirely).
- **Rate limit awareness** — track token usage per agent and throttle proactively
  before hitting provider limits. This is especially important at 100 agents
  making concurrent LLM calls.
- **Request queuing** — instead of all agents hitting the LLM simultaneously, use
  a request queue with concurrency limits to smooth out burst traffic.

### 3. Orchestrator — the entry point

**The problem:** The orchestrator (`main.py`) is a single process that runs the
ADK `Runner` and dispatches A2A calls to all agents. If it crashes, the current
request fails.

**Why this is acceptable (and different from the MCP SPOF):**

- The orchestrator is **stateless** — it rebuilds state from scratch for each
  request. A crash loses one in-flight request, not all system state.
- It contains **zero domain logic** — all intelligence lives in the remote
  agents. The orchestrator is a thin coordination layer, analogous to an API
  gateway.
- It is **trivially horizontally scalable** — run N orchestrator replicas behind
  a load balancer. Since `InMemorySessionService` is per-process and per-request,
  replicas are independent.
- This is the **standard ADK pattern** — Google ADK's `Runner` +
  `SequentialAgent` + `ParallelAgent` are designed to be the single coordination
  point. Fighting this pattern means fighting the framework.

**Production mitigations (when scaling beyond demo):**

- **Replace `InMemorySessionService`** with a persistent backend (Redis,
  PostgreSQL) so session state survives process restarts and can be shared across
  replicas.
- **Run multiple replicas** behind a load balancer. Each replica runs its own
  `Runner` instance independently.
- **Add request-level timeouts** — if a specialist agent doesn't respond within N
  seconds, the orchestrator should cancel that branch rather than hanging
  indefinitely.
- **Structured error handling** — wrap the `runner.run_async()` loop in
  try/except to catch and log A2A communication failures, then return a partial
  result to the user instead of crashing.

### 4. Session state durability

**The problem:** `InMemorySessionService` stores session state in process memory.
If the orchestrator restarts mid-conversation, all context is lost.

**Production mitigations:**

- Use Google ADK's database-backed session service for persistence.
- Store session state in Redis with a TTL for automatic cleanup.
- For multi-turn conversations, persist the conversation history externally so it
  can be replayed into a new session.

### 5. Docker network as single failure domain

**The problem:** All services share one Docker bridge network (`appraisal-net`).
A network partition or Docker daemon issue takes down everything.

**Production mitigations:**

- Deploy to Kubernetes with proper pod anti-affinity rules so agents spread
  across nodes.
- Use a service mesh (Istio, Linkerd) for automatic retries, circuit breaking,
  and observability between agents.
- Separate critical services (MCP server, synthesis agent) onto dedicated nodes.

### Summary: SPOF risk ranking

| Component | Risk | Impact if it fails | Mitigation difficulty |
|-----------|------|-------------------|----------------------|
| MCP Server | **High** | All specialists fail simultaneously | Medium — replicate + retry |
| LLM API endpoint | **High** | All agents fail simultaneously | Medium — fallback model + rate limiting |
| Orchestrator | **Low** | One user's request fails | Easy — add replicas behind LB |
| Session state | **Low** | Context lost on restart | Easy — persistent session backend |
| Docker network | **Low** | Total outage | Medium — Kubernetes + service mesh |

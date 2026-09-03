# Multi-Agent AI Market Research & Alert System

An AI-powered personal watchlist intelligence platform that monitors market conditions, analyzes news and sentiment, validates opportunities using multiple specialized AI agents, and delivers high-confidence research insights and alerts via email — deployed on AWS with a fully automated CI/CD pipeline.

---

## What This System Does

Not an autonomous trading bot. Not a market screener.

A personal watchlist intelligence engine that monitors only the stocks you care about, runs AI reasoning only when needed, and alerts you only when something genuinely important happens.

---

## Architecture Overview

```
n8n (Orchestration) → Application Load Balancer → FastAPI (ECS Fargate) → LangGraph (AI Reasoning) → PostgreSQL (Memory) → Email (Alerts)
```

**LangGraph owns:** Intelligence, agent reasoning, conflict resolution, confidence scoring

**n8n owns:** Scheduling, DB reads/writes, freshness checks, alert routing, tier management

**FastAPI owns:** Authenticated HTTP layer exposing the LangGraph pipeline to n8n

**Stateless LangGraph:** n8n handles ALL database operations. LangGraph is a pure function — input in, reasoning out, zero side effects. This keeps the reasoning layer independently testable, horizontally scalable, and swappable without touching the orchestration layer.

---

## Agent Pipeline

Four agents run in parallel → Validation Agent produces the final decision

| Agent | Responsibility | Data Sources | Output |
|---|---|---|---|
| Technical | Trend, breakout, RSI, MACD, EMA | Finnhub + yfinance | Technical score + summary |
| News | Company news, macro events | Finnhub (cached general news) | News score + summary |
| Sentiment | Insider sentiment, analyst recommendations | Finnhub + yfinance | Sentiment score + summary |
| Risk | Volatility, liquidity, short interest | yfinance | Risk score + summary |
| Validation (Claude) | Aggregates all scores, resolves conflicts | All agent outputs | Final decision + confidence % |

All four scoring agents use **Pydantic structured output** (`with_structured_output()`) rather than manually parsing raw LLM text — this forces the model's response through the provider's native function-calling into a validated schema (`Field(ge=0, le=100)`), eliminating malformed-JSON failures at the source instead of defending against them after the fact.

---

## Key Engineering Features

- **Parallel agent execution** — 4 agents run simultaneously via LangGraph's fan-out/fan-in graph structure
- **Selective agent invalidation** — agents only re-run when their data is stale, per independent per-agent freshness timers
- **Stateless LangGraph** — pure function, no DB side effects, horizontally scalable
- **Tier-based scanning** — HOT (30 min), WATCH (2 hrs), RADAR (24 hrs), dynamically promoted/demoted based on rolling confidence trend
- **Retry + graceful degradation** — every agent retries transient LLM failures, then falls back to the last known-good cached value rather than crashing
- **Delta analysis** — detects confidence trends, not just point-in-time scores
- **Two-trigger alert system** — absolute score threshold + rate-of-change threshold
- **General news cache** — fetched once per cycle, shared across all tickers
- **Connection pooling** — psycopg2 pool, min=1 max=10 connections
- **API-key authentication** — implemented as FastAPI middleware, applying automatically to every route
- **Full observability** — every agent traced in LangSmith with token cost and latency
- **LLM output evaluation** — a hand-designed LangSmith dataset with ground-truth scenarios checks that the technical scoring agent reliably follows its own documented prompt rules across bullish, bearish, neutral, and conflicting-signal conditions
- **Containerized and cloud-deployed** — Docker image running on AWS ECS Fargate behind an Application Load Balancer, with zero manual deployment steps once code is merged

---

## Confidence Formula

```
confidence = technical*0.30 + news*0.25 + sentiment*0.25 + risk*0.20

Conflict detection: any two agents differ >30 points → cap confidence at 70
```

## Decision Bands

| Confidence | Decision | Alert |
|---|---|---|
| >80% | HIGH_INTEREST | IMMEDIATE email |
| 60-80% | WATCH | DAILY_DIGEST |
| 30-60% | NEUTRAL | SILENT |
| <30% | IGNORE | ABSOLUTE_LOW email |

## Two Alert Triggers

- **Trigger 1:** confidence < 30% → ABSOLUTE_LOW immediate alert
- **Trigger 2:** confidence drops >25 points → CRITICAL_DROP immediate alert

---

## Freshness Rules (Selective Invalidation)

| Agent | Freshness | Reason |
|---|---|---|
| Sentiment | 30 minutes | Human emotion reacts instantly to news |
| News | 1 hour | Articles publish continuously |
| Risk | 2 hours | Volatility shifts take time |
| Technical | 4 hours | Derived from historical price action |

---

## Tier System

| Tier | Scan Frequency | Promotion | Demotion |
|---|---|---|---|
| HOT | Every 30 min | avg confidence >75% and rising | avg confidence <55% or trend <-15 |
| WATCH | Every 2 hours | — | avg confidence <55% or trend <-15 |
| RADAR | Every 24 hours | — | — |

Tier is re-evaluated after every scan based on the ticker's own confidence history — tiers shift dynamically as market conditions change, they are not fixed assignments.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agentic AI | LangGraph |
| LLM Ecosystem | LangChain 1.x |
| LLM (4 scoring agents) | OpenAI GPT-4o (structured output) |
| LLM (Validation) | Claude (Anthropic) |
| Orchestration | n8n (cloud) |
| API Layer | FastAPI + Uvicorn |
| Containerization | Docker |
| Cloud Compute | AWS ECS Fargate |
| Load Balancing | AWS Application Load Balancer |
| Container Registry | AWS ECR |
| CI/CD | GitHub Actions |
| Database | PostgreSQL (Supabase) |
| Notifications | Gmail (SMTP) |
| Observability & Evaluation | LangSmith |
| Market Data | Finnhub |
| Technical Indicators | yfinance + pandas_ta |

---

## Deployment Architecture

The application runs as a Docker container on **AWS ECS Fargate** (serverless containers — no server management), sitting behind an **Application Load Balancer** that provides a permanent, stable public URL regardless of how many times the underlying task restarts or redeploys.

**Live endpoint pattern:**
```
http://<load-balancer-dns-name>/health
http://<load-balancer-dns-name>/analyze   (POST, requires X-API-Key header)
```

### CI/CD

Every push to `main` triggers `.github/workflows/deploy.yml`, which:
1. Builds the Docker image and tags it with the git commit SHA (not `:latest` — ensures every deployment is unambiguous and traceable to an exact commit)
2. Pushes the image to ECR
3. Fills a version-controlled `task-definition.json` template with secrets pulled from GitHub Actions Secrets (never committed to the repo in plaintext)
4. Registers a new ECS task definition revision
5. Updates the ECS service with `--force-new-deployment`

No manual AWS console steps are required for a normal code change — push to `main`, and the new version is live within minutes.

---

## Database Schema

```
watchlist           -- ticker, tier, added_on, last_scan
agent_scores        -- ticker, 4 scores, 4 separate timestamps per agent
confidence_history  -- ticker, confidence, decision, delta, recorded_at
alert_log           -- ticker, alert_type, message, confidence_at_alert
execution_log       -- ticker, run_result, run_time, error_msg
general_news_cache  -- news_data (JSON), fetched_at
```

---

## Project Structure

```
market-research-system/
├── agents/
│   ├── technical_agent.py
│   ├── news_agent.py
│   ├── sentiment_agent.py
│   ├── risk_agent.py
│   └── validation_agent.py
├── graph/
│   ├── state.py
│   └── pipeline.py
├── database/
│   └── queries.py
├── evaluation/
│   └── build_technical_dataset.py   # LangSmith ground-truth eval harness
├── tools/
├── .github/
│   └── workflows/
│       └── deploy.yml               # CI/CD pipeline
├── api.py                           # FastAPI app + auth middleware (production entry point)
├── main.py                          # local dev/test orchestrator (not deployed)
├── utils.py                         # shared helpers (utc_now, score validation)
├── Dockerfile
├── .dockerignore
├── task-definition.json             # ECS task definition template (placeholders only)
├── graph_visualization.png
├── requirements.txt
└── README.md
```

---

## Local Setup

```bash
# Clone the repo
git clone https://github.com/ShubhamDKondewar98/market-research-system.git
cd market-research-system

# Create environment
python -m venv market_venv
source market_venv/bin/activate   # or market_venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Fill in your API keys (see below)

# Run FastAPI locally
uvicorn api:app --reload --port 8000

# Or run the local test orchestrator directly against the DB
python main.py
```

### Running with Docker

```bash
docker build -t market-research-api .
docker run --env-file .env -p 8000:8000 market-research-api
```

---

## Environment Variables

```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
FINNHUB_API_KEY=
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=market-research-system
DATABASE_URL=postgresql://...
API_SECRET_KEY=              # required header (X-API-Key) for the /analyze endpoint
```

**Note:** avoid special URL-reserved characters (`@`, `/`, `:`, `#`, `%`, `?`) in the database password — they will break `DATABASE_URL` parsing. Avoid surrounding values with quotes in `.env` — some tools (Docker's `--env-file`, CI substitution) don't strip them the way `python-dotenv` does.

For CI/CD, the same values are stored as encrypted **GitHub Actions Secrets**, plus `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

---

## LLM Evaluation

`evaluation/build_technical_dataset.py` builds a LangSmith dataset of hand-designed scenarios (clean bullish, clean bearish, neutral, and two internally-conflicting signal cases), each constructed so every rule in the technical agent's own prompt points toward a specific expected score range. Running the script's `run_evaluation()` function calls the agent's real scoring logic against each scenario and reports pass/fail against the expected range — a regression check to run after changing the prompt or switching models, not part of the live application.

---

## Known Limitations / Deliberate Scope Decisions

A few common patterns were evaluated and intentionally left out, since none solved a problem this system actually has at its current scale:

- **LLM Gateway** — LangSmith already provides cross-provider cost/latency tracing; existing retry-and-cache-fallback already handles provider downtime gracefully
- **Additional input guardrails** — data sources (Finnhub, yfinance) are curated and reputable, not arbitrary user input; empty/malformed-data handling was tested empirically rather than assumed to be risky
- **Rate limiting** — the only client is an internal, scheduled n8n workflow, already gated by API-key auth
- **Automated test suite** — verification was done through extensive manual end-to-end testing (local, containerized, and live deployment) at every stage; a `pytest` suite around the validation and confidence-calculation logic is the clear next step
- **HTTPS on the load balancer** — currently HTTP only; adding a TLS certificate via AWS Certificate Manager is a planned hardening step

---

## Market Coverage

**Current:** US Markets (NYSE, NASDAQ)

---

## Disclaimer

For research and educational purposes only. Not financial advice. Always do your own research before making investment decisions.

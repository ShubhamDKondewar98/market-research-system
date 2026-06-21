# Multi-Agent AI Market Research & Alert System

An AI-powered personal watchlist intelligence platform that monitors market conditions, analyzes news and sentiment, validates opportunities using multiple specialized AI agents, and delivers high-confidence research insights and alerts via Email.

---

## What This System Does

Not an autonomous trading bot. Not a market screener.

A personal watchlist intelligence engine that monitors only the stocks you care about, runs AI reasoning only when needed, and alerts you only when something genuinely important happens.

---

## Architecture Overview

```
n8n (Orchestration) → FastAPI → LangGraph (AI Reasoning) → PostgreSQL (Memory) → Email (Alerts)
```

**LangGraph owns:** Intelligence, agent reasoning, conflict resolution, confidence scoring

**n8n owns:** Scheduling, DB reads/writes, freshness checks, alert routing, tier management

**FastAPI owns:** HTTP wrapper exposing LangGraph pipeline to n8n

**Option C — Stateless LangGraph:** n8n handles ALL database operations. LangGraph is a pure function — input in, reasoning out, zero side effects.

---

## Agent Pipeline

Four agents run in parallel → Signal Validation Agent produces final decision

| Agent | Responsibility | Data Sources | Output |
|---|---|---|---|
| Technical | Trend, breakout, RSI, MACD, EMA | Finnhub + yfinance | Technical score + summary |
| News | Company news, macro events | Finnhub (cached general news) | News score + summary |
| Sentiment | Insider sentiment, analyst recommendations | Finnhub + yfinance | Sentiment score + summary |
| Risk | Volatility, liquidity, short interest | yfinance | Risk score + summary |
| Validation (Claude) | Aggregates all scores, resolves conflicts | All agent outputs | Final decision + confidence % |

---

## Key Engineering Features

- **Parallel agent execution** — 4 agents run simultaneously, reducing latency ~60%
- **Selective agent invalidation** — agents only re-run when their data is stale
- **Option C stateless LangGraph** — pure function, no DB side effects, horizontally scalable
- **Tier-based scanning** — HOT (30 min), WATCH (2 hrs), RADAR (24 hrs)
- **Delta analysis** — detects confidence trends, not just point-in-time scores
- **Two-trigger alert system** — absolute score threshold + rate of change threshold
- **General news cache** — fetched once per hour, shared across all tickers
- **Connection pooling** — psycopg2 pool, min=1 max=10 connections
- **Full observability** — every agent traced in LangSmith with token cost and latency

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
| HOT | Every 30 min | confidence >75% | confidence <55% |
| WATCH | Every 2 hours | — | confidence <55% |
| RADAR | Every 24 hours | — | — |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agentic AI | LangGraph |
| LLM Ecosystem | LangChain |
| LLM (4 agents) | OpenAI GPT-4o |
| LLM (Validation) | Claude claude-sonnet-4-6 |
| Orchestration | n8n (cloud) |
| API Layer | FastAPI + uvicorn |
| Tunnel | ngrok |
| Database | PostgreSQL (Supabase) |
| Notifications | Gmail (SMTP) |
| Observability | LangSmith |
| Market Data | Finnhub |
| Technical Indicators | yfinance + pandas_ta |

---

## Database Schema

```sql
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
│   ├── queries.py
│   └── schema.sql
├── tools/
├── api.py
├── main.py
├── graph_visualization.png
├── .env
├── requirements.txt
└── README.md
```

---

## Setup

```bash
# Clone the repo
git clone https://github.com/ShubhamDKondewar98/market-research-system.git
cd market-research-system

# Create environment
conda create -p market_venv python==3.13
conda activate market_venv/

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Fill in your API keys

# Run FastAPI
uvicorn api:app --reload --port 8000

# Run ngrok tunnel
ngrok http 8000

# Run local pipeline
python main.py
```

---

## Environment Variables

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
FINNHUB_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=market-research-system
DATABASE_URL=postgresql://.........
```

---

## Watchlist

| Ticker | Company | Tier |
|---|---|---|
| AAPL | Apple | WATCH |
| NVDA | Nvidia | RADAR |
| TSLA | Tesla | RADAR |
| MSFT | Microsoft | WATCH |
| JPM | JPMorgan | RADAR |

---

## Market Coverage

**Current:** US Markets (NYSE, NASDAQ)

---

## Disclaimer

For research and educational purposes only.
Not financial advice. Always do your own research before making investment decisions.
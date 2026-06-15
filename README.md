# Multi-Agent AI Market Research & Alert System

An AI-powered personal watchlist intelligence platform that monitors market conditions, analyzes news and sentiment, validates opportunities using multiple specialized AI agents, and delivers high-confidence research insights and alerts via Telegram.

---

## What This System Does

Not an autonomous trading bot. Not a market screener.

A personal watchlist intelligence engine that monitors only the stocks you care about, runs AI reasoning only when needed, and alerts you only when something genuinely important happens.

---

## Architecture Overview 

n8n (Orchestration) → LangGraph (AI Reasoning) → PostgreSQL (Memory) → Telegram (Alerts)

**LangGraph owns:** Intelligence, agent reasoning, conflict resolution, confidence scoring

**n8n owns:** Scheduling, API routing, alert delivery, tier management, retry logic

---

## Agent Pipeline

Four agents run in parallel → Signal Validation Agent produces final decision

| Agent | Responsibility | Output |
|---|---|---|
| Technical Agent | Trend, breakout, RSI, MACD, support/resistance | Technical score + summary |
| News Agent | Company news, earnings, sector developments | News score + summary |
| Sentiment Agent | Bullish/bearish bias from multiple sources | Sentiment score + summary |
| Risk Agent | Volatility, liquidity, conflicting signals | Risk score + summary |
| Validation Agent | Aggregates all scores, resolves conflicts | Final decision + confidence % |

---

## Key Engineering Features

- **Parallel agent execution** — 4 agents run simultaneously, reducing latency
- **Selective agent invalidation** — agents only re-run when their data is stale
- **Tier-based scanning** — HOT (15 min), WATCH (2 hrs), RADAR (24 hrs)
- **Delta analysis** — detects confidence trends, not just point-in-time scores
- **Two-trigger alert system** — absolute score threshold + rate of change threshold
- **Daily digest** — batches medium-confidence updates into one evening message
- **Full observability** — every agent traced in LangSmith with token cost and latency

---

## Alert System

Two independent triggers for immediate Telegram alerts:

- **Trigger 1:** Confidence drops below 30%
- **Trigger 2:** Confidence drops more than 25 points in a single run

Confidence bands:
- Above 80% → Immediate alert
- 60-80% → Daily digest
- 30-60% → Store only
- Below 30% → Immediate alert

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agentic AI | LangGraph |
| LLM Ecosystem | LangChain |
| LLM | OpenAI GPT-4o |
| Orchestration | n8n |
| Database | PostgreSQL |
| Notifications | Telegram |
| Observability | LangSmith |
| Market Data | Finnhub |
| News Data | NewsAPI / Finnhub News |

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
│   ├── models.py
│   └── queries.py
├── tools/
│   └── market_data.py
├── .env
├── .gitignore
├── requirements.txt
└── main.py
```


---

## Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/market-research-system.git
cd market-research-system

# Create environment
conda create -p market_venv python==3.13
conda activate market_venv/

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Fill in your API keys
```

---

## Environment Variables

```env
OPENAI_API_KEY=
FINNHUB_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=market-research-system
DATABASE_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## Build Phases

| Phase | What Gets Built | Status |
|---|---|---|
| Phase 1 | Technical Agent + real Finnhub data | 🔄 In Progress |
| Phase 2 | All 4 agents running in parallel | ⏳ Pending |
| Phase 3 | Signal Validation Agent + complete pipeline | ⏳ Pending |
| Phase 4 | Watchlist Memory Layer + delta analysis | ⏳ Pending |
| Phase 5 | Tier system + PostgreSQL | ⏳ Pending |
| Phase 6 | n8n integration + Telegram alerts | ⏳ Pending |
| Phase 7 | Error handling + production hardening | ⏳ Pending |

---

## Disclaimer

This system is for research and educational purposes only.
Not financial advice. Always do your own research before making investment decisions.
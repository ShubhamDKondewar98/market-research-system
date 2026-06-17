-- ============================================================
-- Multi-Agent AI Market Research & Alert System
-- PostgreSQL Schema (hosted on Supabase)
-- ============================================================

-- Table 1: Watchlist
-- Stores user's tracked tickers and their scan tier
create table watchlist (
  id SERIAL PRIMARY KEY,
  ticker TEXT UNIQUE NOT NULL,
  tier TEXT DEFAULT 'WATCH' CHECK (tier IN ('HOT', 'WATCH', 'RADAR')),
  added_on TIMESTAMP DEFAULT NOW(),
  last_scan TIMESTAMP
);

-- Table 2: Agent Scores
-- Stores individual agent scores for each pipeline run
create table agent_scores (
  id SERIAL PRIMARY KEY,
  ticker TEXT REFERENCES watchlist(ticker),
  technical_score FLOAT,
  news_score FLOAT,
  sentiment_score FLOAT,
  risk_score FLOAT,
  run_timestamp TIMESTAMP DEFAULT NOW(),
  agents_run TEXT[]
);

-- Table 3: Confidence History
-- Tracks confidence score trend over time for delta analysis
create table confidence_history (
  id SERIAL PRIMARY KEY,
  ticker TEXT REFERENCES watchlist(ticker),
  confidence_score FLOAT,
  decision TEXT DEFAULT 'NEUTRAL' CHECK (decision IN ('WATCH','IGNORE','HIGH_INTEREST','NEUTRAL')),
  delta FLOAT,
  recorded_at TIMESTAMP DEFAULT NOW()
);

-- Table 4: Alert Log
-- Records every alert sent to the user
create table alert_log (
  id SERIAL PRIMARY KEY,
  ticker TEXT REFERENCES watchlist(ticker),
  alert_type TEXT DEFAULT 'SILENT' CHECK (alert_type IN ('IMMEDIATE','DAILY_DIGEST','SILENT','CRITICAL_DROP','ABSOLUTE_LOW')),
  message TEXT,
  confidence_score_at_alert FLOAT,
  sent_when TIMESTAMP DEFAULT NOW()
);

-- Table 5: Execution Log
-- Audit trail for every pipeline run — success/failure tracking
create table execution_log (
  id SERIAL PRIMARY KEY,
  ticker TEXT REFERENCES watchlist(ticker),
  run_result TEXT DEFAULT 'succeeded' CHECK (run_result IN ('succeeded', 'failed')),
  run_time INTERVAL,
  error_msg TEXT,
  run_when TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- Design Notes:
-- - Foreign keys reference watchlist(ticker) to enforce data integrity
-- - CHECK constraints prevent invalid enum-like values from being stored
-- - TIMESTAMP defaults use NOW() to auto-capture insert time
-- - RLS (Row Level Security) disabled: this system connects via direct
--   PostgreSQL connection string (Python/n8n), not Supabase's public
--   REST API with anon/authenticated keys. In a multi-tenant production
--   system, RLS would be enabled per-user.
-- ============================================================

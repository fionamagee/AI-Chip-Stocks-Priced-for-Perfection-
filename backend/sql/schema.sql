-- =============================================================
-- AI Chip Stocks: Priced for Perfection?
-- PostgreSQL Schema
-- Run with: psql -U <user> -d <dbname> -f backend/sql/schema.sql
-- =============================================================

-- 1. COMPANIES
--    Static reference table for the ticker universe.
CREATE TABLE IF NOT EXISTS companies (
    ticker              TEXT        PRIMARY KEY,
    company_name        TEXT,
    sector              TEXT,
    industry            TEXT,
    supply_chain_tier   TEXT,       -- e.g. "Tier 2 - Designers", "Tier 4 - Fabrication"
    description         TEXT
);

-- 2. DAILY PRICES
--    One row per ticker per trading day.
CREATE TABLE IF NOT EXISTS daily_prices (
    id              BIGSERIAL   PRIMARY KEY,
    ticker          TEXT        NOT NULL,
    date            DATE        NOT NULL,
    open            NUMERIC(18, 6),
    high            NUMERIC(18, 6),
    low             NUMERIC(18, 6),
    close           NUMERIC(18, 6),
    adjusted_close  NUMERIC(18, 6),
    volume          BIGINT,
    UNIQUE (ticker, date)
);

-- 3. QUARTERLY FUNDAMENTALS
--    Income statement, balance sheet, and cash flow data combined.
--    period is typically "Q1", "Q2", "Q3", "Q4", or "FY".
CREATE TABLE IF NOT EXISTS quarterly_fundamentals (
    id                  BIGSERIAL   PRIMARY KEY,
    ticker              TEXT        NOT NULL,
    fiscal_date         DATE        NOT NULL,
    period              TEXT        NOT NULL,
    revenue             NUMERIC(20, 2),
    gross_profit        NUMERIC(20, 2),
    operating_income    NUMERIC(20, 2),
    net_income          NUMERIC(20, 2),
    eps                 NUMERIC(12, 6),
    free_cash_flow      NUMERIC(20, 2),
    capital_expenditure NUMERIC(20, 2),
    cash                NUMERIC(20, 2),
    total_debt          NUMERIC(20, 2),
    UNIQUE (ticker, fiscal_date, period)
);

-- 4. VALUATION METRICS
--    Point-in-time valuation snapshot, updated on pull date.
CREATE TABLE IF NOT EXISTS valuation_metrics (
    id                      BIGSERIAL   PRIMARY KEY,
    ticker                  TEXT        NOT NULL,
    date                    DATE        NOT NULL,
    pe_ratio                NUMERIC(12, 4),
    price_to_sales          NUMERIC(12, 4),
    ev_to_sales             NUMERIC(12, 4),
    ev_to_ebitda            NUMERIC(12, 4),
    price_to_free_cash_flow NUMERIC(12, 4),
    roe                     NUMERIC(12, 6),
    roic                    NUMERIC(12, 6),
    debt_to_equity          NUMERIC(12, 6),
    UNIQUE (ticker, date)
);

-- 5. ANALYST ESTIMATES
--    Point-in-time consensus snapshots. One row per ticker/period/snapshot_date.
--    Running load_estimates.py weekly builds a revision time series that cannot
--    be reconstructed retroactively — collect from day one.
CREATE TABLE IF NOT EXISTS analyst_estimates (
    id                    BIGSERIAL   PRIMARY KEY,
    ticker                TEXT        NOT NULL,
    fiscal_date           DATE        NOT NULL,
    period                TEXT        NOT NULL,
    snapshot_date         DATE        NOT NULL,   -- date this consensus was recorded
    estimated_revenue_avg NUMERIC(20, 2),
    estimated_eps_avg     NUMERIC(12, 6),
    number_analysts       INTEGER,
    UNIQUE (ticker, fiscal_date, period, snapshot_date)
);

-- 6. EARNINGS EVENTS
--    Historical earnings beats/misses — the basis for PEAD analysis.
CREATE TABLE IF NOT EXISTS earnings_events (
    id                  BIGSERIAL   PRIMARY KEY,
    ticker              TEXT        NOT NULL,
    earnings_date       DATE        NOT NULL,
    eps_actual          NUMERIC(12, 6),
    eps_estimated       NUMERIC(12, 6),
    revenue_actual      NUMERIC(20, 2),
    revenue_estimated   NUMERIC(20, 2),
    surprise_percentage NUMERIC(10, 4),
    UNIQUE (ticker, earnings_date)
);

-- 7. NEWS ARTICLES
--    Finnhub news, keyed by URL to prevent duplicates.
CREATE TABLE IF NOT EXISTS news_articles (
    id              BIGSERIAL       PRIMARY KEY,
    ticker          TEXT,           -- primary ticker this article was fetched for
    headline        TEXT,
    summary         TEXT,
    source          TEXT,
    url             TEXT            UNIQUE,   -- deduplicate across tickers
    image           TEXT,
    published_at    TIMESTAMPTZ,
    related_tickers TEXT            -- comma-separated list from API
);

-- 8. EARNINGS TRANSCRIPTS
--    Raw transcript text stored in full so it can be reprocessed with
--    improved LLM prompts at any future point.
CREATE TABLE IF NOT EXISTS earnings_transcripts (
    id          BIGSERIAL   PRIMARY KEY,
    ticker      TEXT        NOT NULL,
    fiscal_date DATE        NOT NULL,
    period      TEXT        NOT NULL,   -- "Q1", "Q2", "Q3", "Q4", "FY"
    call_date   DATE,
    raw_text    TEXT,
    word_count  INTEGER,
    source      TEXT,                   -- "seeking_alpha", "fmp", "manual", etc.
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, fiscal_date, period)
);

-- 9. THESIS SIGNALS
--    Time-stamped readings of composite signals and thesis health scores.
--    Every score written here can later be compared to subsequent price returns
--    to validate or falsify the analytical framework.
CREATE TABLE IF NOT EXISTS thesis_signals (
    id               BIGSERIAL    PRIMARY KEY,
    snapshot_date    DATE         NOT NULL,
    ticker           TEXT,        -- NULL for portfolio-level or macro signals
    signal_name      TEXT         NOT NULL,
    signal_value     NUMERIC(10, 4),
    signal_direction TEXT,        -- "strengthening" | "neutral" | "weakening"
    notes            TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (snapshot_date, ticker, signal_name)
);

-- 10. PRICE TARGET SNAPSHOTS
--     Weekly consensus price target snapshots per ticker.
--     Tracks analyst price target revision momentum independently of EPS revisions.
CREATE TABLE IF NOT EXISTS price_target_snapshots (
    id                BIGSERIAL   PRIMARY KEY,
    ticker            TEXT        NOT NULL,
    snapshot_date     DATE        NOT NULL,
    price_target_avg  NUMERIC(12, 4),
    price_target_high NUMERIC(12, 4),
    price_target_low  NUMERIC(12, 4),
    number_analysts   INTEGER,
    source            TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, snapshot_date)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_date       ON daily_prices (ticker, date DESC);
CREATE INDEX IF NOT EXISTS idx_quarterly_fundamentals_tick    ON quarterly_fundamentals (ticker, fiscal_date DESC);
CREATE INDEX IF NOT EXISTS idx_valuation_metrics_ticker       ON valuation_metrics (ticker, date DESC);
CREATE INDEX IF NOT EXISTS idx_analyst_estimates_ticker_snap  ON analyst_estimates (ticker, fiscal_date DESC, snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_earnings_events_ticker         ON earnings_events (ticker, earnings_date DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_ticker_pub       ON news_articles (ticker, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_transcripts_ticker_date        ON earnings_transcripts (ticker, fiscal_date DESC);
CREATE INDEX IF NOT EXISTS idx_thesis_signals_ticker_date     ON thesis_signals (ticker, snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_thesis_signals_name_date       ON thesis_signals (signal_name, snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_price_targets_ticker_date      ON price_target_snapshots (ticker, snapshot_date DESC);

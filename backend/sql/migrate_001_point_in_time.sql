-- =============================================================
-- Migration 001: Point-in-time snapshot infrastructure
-- =============================================================
-- Safe to rerun. All changes are wrapped in existence checks.
--
-- What this migration does:
--   1. Adds snapshot_date to analyst_estimates
--   2. Drops the old 3-column unique constraint
--   3. Adds the new 4-column unique constraint (includes snapshot_date)
--   4. Creates earnings_transcripts table
--   5. Creates thesis_signals table
--   6. Creates price_target_snapshots table
--   7. Adds supporting indexes
--
-- Run with:
--   psql -U <user> -d <dbname> -f backend/sql/migrate_001_point_in_time.sql
-- =============================================================


-- =============================================================
-- STEP 1: Migrate analyst_estimates to point-in-time snapshots
-- =============================================================

DO $$
BEGIN

    -- 1a. Add snapshot_date column if it does not already exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'analyst_estimates'
          AND column_name = 'snapshot_date'
    ) THEN
        ALTER TABLE analyst_estimates ADD COLUMN snapshot_date DATE;

        -- Backfill existing rows so we can apply NOT NULL.
        -- Existing rows get today's date as their first snapshot.
        UPDATE analyst_estimates SET snapshot_date = CURRENT_DATE WHERE snapshot_date IS NULL;

        ALTER TABLE analyst_estimates ALTER COLUMN snapshot_date SET NOT NULL;

        RAISE NOTICE 'analyst_estimates: added snapshot_date column and backfilled existing rows with %', CURRENT_DATE;
    ELSE
        RAISE NOTICE 'analyst_estimates: snapshot_date column already exists, skipping add';
    END IF;

    -- 1b. Drop the old 3-column unique constraint if it still exists
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name       = 'analyst_estimates'
          AND constraint_name  = 'analyst_estimates_ticker_fiscal_date_period_key'
          AND constraint_type  = 'UNIQUE'
    ) THEN
        ALTER TABLE analyst_estimates
            DROP CONSTRAINT analyst_estimates_ticker_fiscal_date_period_key;
        RAISE NOTICE 'analyst_estimates: dropped old 3-column unique constraint';
    ELSE
        RAISE NOTICE 'analyst_estimates: old 3-column constraint not found, skipping drop';
    END IF;

    -- 1c. Add the new 4-column unique constraint if it does not already exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name      = 'analyst_estimates'
          AND constraint_name = 'analyst_estimates_snapshot_unique'
          AND constraint_type = 'UNIQUE'
    ) THEN
        ALTER TABLE analyst_estimates
            ADD CONSTRAINT analyst_estimates_snapshot_unique
            UNIQUE (ticker, fiscal_date, period, snapshot_date);
        RAISE NOTICE 'analyst_estimates: added 4-column snapshot unique constraint';
    ELSE
        RAISE NOTICE 'analyst_estimates: 4-column snapshot constraint already exists, skipping';
    END IF;

END $$;


-- =============================================================
-- STEP 2: earnings_transcripts
-- =============================================================

CREATE TABLE IF NOT EXISTS earnings_transcripts (
    id          BIGSERIAL   PRIMARY KEY,
    ticker      TEXT        NOT NULL,
    fiscal_date DATE        NOT NULL,
    period      TEXT        NOT NULL,   -- e.g. "Q1", "Q2", "Q3", "Q4", "FY"
    call_date   DATE,
    raw_text    TEXT,                   -- full transcript text — store always, parse later
    word_count  INTEGER,
    source      TEXT,                   -- "seeking_alpha", "fmp", "manual", etc.
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, fiscal_date, period)
);

CREATE INDEX IF NOT EXISTS idx_transcripts_ticker_date
    ON earnings_transcripts (ticker, fiscal_date DESC);


-- =============================================================
-- STEP 3: thesis_signals
-- =============================================================

CREATE TABLE IF NOT EXISTS thesis_signals (
    id               BIGSERIAL    PRIMARY KEY,
    snapshot_date    DATE         NOT NULL,
    ticker           TEXT,        -- NULL for portfolio-level or macro signals
    signal_name      TEXT         NOT NULL,
    -- Examples:
    --   "capex_trajectory"          — hyperscaler CapEx trend direction
    --   "estimate_revision_momentum"— 30/60/90-day EPS revision direction
    --   "monetization_signal"       — AI revenue vs CapEx ratio signal
    --   "supply_constraint_signal"  — bottleneck severity reading
    --   "valuation_signal"          — current multiple vs 5yr median
    --   "thesis_health_score"       — composite 0-100 score
    signal_value     NUMERIC(10, 4),
    signal_direction TEXT,        -- "strengthening" | "neutral" | "weakening"
    notes            TEXT,        -- free-text reasoning or source reference
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (snapshot_date, ticker, signal_name)
);

CREATE INDEX IF NOT EXISTS idx_thesis_signals_ticker_date
    ON thesis_signals (ticker, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_thesis_signals_name_date
    ON thesis_signals (signal_name, snapshot_date DESC);


-- =============================================================
-- STEP 4: price_target_snapshots
-- =============================================================

CREATE TABLE IF NOT EXISTS price_target_snapshots (
    id                BIGSERIAL   PRIMARY KEY,
    ticker            TEXT        NOT NULL,
    snapshot_date     DATE        NOT NULL,
    price_target_avg  NUMERIC(12, 4),
    price_target_high NUMERIC(12, 4),
    price_target_low  NUMERIC(12, 4),
    number_analysts   INTEGER,
    source            TEXT,       -- "fmp", "manual", etc.
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_price_targets_ticker_date
    ON price_target_snapshots (ticker, snapshot_date DESC);


-- =============================================================
-- STEP 5: Update existing analyst_estimates index
-- =============================================================

-- Drop the old index (it indexed on 3 columns; snapshot_date is now needed)
DROP INDEX IF EXISTS idx_analyst_estimates_ticker;

-- New index covers the snapshot query pattern
CREATE INDEX IF NOT EXISTS idx_analyst_estimates_ticker_snapshot
    ON analyst_estimates (ticker, fiscal_date DESC, snapshot_date DESC);


-- =============================================================
-- Done
-- =============================================================
-- Verify with:
--   \d analyst_estimates
--   \d earnings_transcripts
--   \d thesis_signals
--   \d price_target_snapshots
-- =============================================================

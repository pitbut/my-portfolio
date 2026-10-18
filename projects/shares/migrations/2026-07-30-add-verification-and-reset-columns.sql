-- One-off migration for site_shares_db: bring the live schema up to date
-- with the current schema.sql before re-running it. Checked row counts
-- first: users=1 (the admin), shares_ledger=0, sell_orders=0, buy_orders=0,
-- trades=0, purchase_intents=1, referral_views=1, site_stats=2.
--
-- ALREADY APPLIED to production on 2026-07-30 (followed by schema.sql).
-- Kept here as a historical record, not meant to be re-run — the ALTER
-- TABLE ADD COLUMN statements below will error with "duplicate column
-- name" if run again against a database that already has them.

-- users: add columns needed for email verification + password reset.
-- Existing users predate the verification requirement, so grandfather
-- them in as already verified (otherwise the admin account would get
-- locked out of login).
ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN verification_token TEXT;
ALTER TABLE users ADD COLUMN verification_sent_at TEXT;
ALTER TABLE users ADD COLUMN password_reset_token TEXT;
ALTER TABLE users ADD COLUMN password_reset_sent_at TEXT;
UPDATE users SET email_verified = 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_password_reset_token ON users(password_reset_token);

-- shares_ledger: old CHECK only allowed ('primary','secondary','bonus'),
-- rejecting the new 'transfer_in'/'transfer_out'/'dividend' sources, and
-- quantity was INTEGER instead of REAL. Table is empty (0 rows) — safe to
-- drop and recreate instead of a column-by-column rebuild.
DROP TABLE IF EXISTS shares_ledger;
CREATE TABLE shares_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  quantity REAL NOT NULL,
  price_paid REAL NOT NULL,
  acquired_at TEXT NOT NULL DEFAULT (datetime('now')),
  source TEXT NOT NULL CHECK (source IN ('primary','secondary','bonus','transfer_in','transfer_out','dividend'))
);
CREATE INDEX IF NOT EXISTS idx_shares_ledger_user ON shares_ledger(user_id);

-- sell_orders / buy_orders / trades: quantity/remaining were INTEGER,
-- now REAL for fractional share support. All empty (0 rows) — safe to
-- drop and recreate.
DROP TABLE IF EXISTS sell_orders;
CREATE TABLE sell_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  quantity REAL NOT NULL,
  remaining REAL NOT NULL,
  price_per_share REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','matched','cancelled'))
);

DROP TABLE IF EXISTS buy_orders;
CREATE TABLE buy_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  quantity REAL NOT NULL,
  remaining REAL NOT NULL,
  price_per_share REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','matched','cancelled'))
);

DROP TABLE IF EXISTS trades;
CREATE TABLE trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  buy_order_id INTEGER REFERENCES buy_orders(id),
  sell_order_id INTEGER REFERENCES sell_orders(id),
  quantity REAL NOT NULL,
  price_per_share REAL NOT NULL,
  platform_fee REAL NOT NULL,
  executed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sell_orders_status_price ON sell_orders(status, price_per_share);
CREATE INDEX IF NOT EXISTS idx_buy_orders_status_price ON buy_orders(status, price_per_share);

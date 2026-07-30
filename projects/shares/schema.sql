-- Cloudflare D1 schema for "site shares" project
-- Apply with: wrangler d1 execute site_shares_db --file=./schema.sql

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'ru',
  referral_code TEXT UNIQUE NOT NULL,
  referred_by INTEGER REFERENCES users(id),
  is_admin INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Сообщения администратора конкретному держателю акций (видны в его кабинете)
CREATE TABLE IF NOT EXISTS admin_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  admin_id INTEGER NOT NULL REFERENCES users(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  read_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_admin_messages_user ON admin_messages(user_id);

CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  expires_at TEXT NOT NULL
);

-- Одна запись = один "пакет" акций, купленных/переданных/начисленных за одну операцию.
-- transfer_out/transfer_in — прямая передача акций между двумя участниками (см. таблицу transfers).
-- dividend — бонусные акции-дивиденды, начисленные бесплатно (см. distributeDividends, НИКОГДА не деньги).
CREATE TABLE IF NOT EXISTS shares_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  quantity INTEGER NOT NULL,
  price_paid REAL NOT NULL,
  acquired_at TEXT NOT NULL DEFAULT (datetime('now')),
  source TEXT NOT NULL CHECK (source IN ('primary','secondary','bonus','transfer_in','transfer_out','dividend'))
);

-- Заявки на продажу (вторичный рынок)
CREATE TABLE IF NOT EXISTS sell_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  quantity INTEGER NOT NULL,
  remaining INTEGER NOT NULL,
  price_per_share REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','matched','cancelled'))
);

-- Заявки на покупку (вторичный рынок)
CREATE TABLE IF NOT EXISTS buy_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  quantity INTEGER NOT NULL,
  remaining INTEGER NOT NULL,
  price_per_share REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','matched','cancelled'))
);

-- Исполненные сделки вторичного рынка
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  buy_order_id INTEGER REFERENCES buy_orders(id),
  sell_order_id INTEGER REFERENCES sell_orders(id),
  quantity INTEGER NOT NULL,
  price_per_share REAL NOT NULL,
  platform_fee REAL NOT NULL,
  executed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Первичные покупки (у "эмитента", то есть напрямую у проекта, лимит 10000 навсегда)
CREATE TABLE IF NOT EXISTS purchase_intents (
  id TEXT PRIMARY KEY, -- uuid, используется как order id для платёжного провайдера
  user_id INTEGER NOT NULL REFERENCES users(id),
  quantity INTEGER NOT NULL,
  price_per_share REAL NOT NULL,
  total_amount REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','paid','failed','cancelled')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  paid_at TEXT
);

-- Общие счётчики сайта
CREATE TABLE IF NOT EXISTS site_stats (
  key TEXT PRIMARY KEY,
  value INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO site_stats (key, value) VALUES ('total_views', 0);
INSERT OR IGNORE INTO site_stats (key, value) VALUES ('total_shares_sold_primary', 0);

-- Настройки сайта, задаваемые администратором (ключ-значение).
-- total_valuation — общая сумма (оценка стоимости проекта), которую вводит админ;
-- цена одной акции = total_valuation / PRIMARY_SUPPLY_LIMIT (см. worker/src/index.js).
CREATE TABLE IF NOT EXISTS site_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

INSERT OR IGNORE INTO site_settings (key, value) VALUES ('total_valuation', '10000');
-- monthly_dividend_pool — сколько бонусных акций (не денег!) раздаётся всем держателям
-- за месяц, пропорционально их доле (см. distributeDividends в worker/src/index.js).
INSERT OR IGNORE INTO site_settings (key, value) VALUES ('monthly_dividend_pool', '100');

-- История начислений дивидендов (бонусных акций, без денег) держателям.
CREATE TABLE IF NOT EXISTS dividend_distributions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  total_shares INTEGER NOT NULL,
  total_holders INTEGER NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Прямая передача акций от одного участника другому. Любая покупка/продажа/дарение
-- акций между людьми — это в итоге такая передача: деньгами или иным способом
-- стороны договариваются между собой вне сайта, а здесь только меняется владелец.
CREATE TABLE IF NOT EXISTS transfers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_user_id INTEGER NOT NULL REFERENCES users(id),
  to_user_id INTEGER NOT NULL REFERENCES users(id),
  quantity INTEGER NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_transfers_from ON transfers(from_user_id);
CREATE INDEX IF NOT EXISTS idx_transfers_to ON transfers(to_user_id);

-- Личные сообщения между участниками (например, чтобы договориться о сделке
-- из стакана заявок, кликнув на чужую заявку).
CREATE TABLE IF NOT EXISTS user_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sender_id INTEGER NOT NULL REFERENCES users(id),
  recipient_id INTEGER NOT NULL REFERENCES users(id),
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  read_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_user_messages_recipient ON user_messages(recipient_id);

-- Учёт просмотров по рефералкам (для блока "по твоей ссылке заходили N раз")
CREATE TABLE IF NOT EXISTS referral_views (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  referrer_id INTEGER NOT NULL REFERENCES users(id),
  viewed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sell_orders_status_price ON sell_orders(status, price_per_share);
CREATE INDEX IF NOT EXISTS idx_buy_orders_status_price ON buy_orders(status, price_per_share);
CREATE INDEX IF NOT EXISTS idx_shares_ledger_user ON shares_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_referral_views_referrer ON referral_views(referrer_id);

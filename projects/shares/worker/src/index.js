// Cloudflare Worker — API для проекта "акции сайта"
// Деплой: wrangler deploy (см. wrangler.toml)
//
// ВАЖНО (юридическая рамка, не менять без пересмотра всей схемы):
//  - Дивиденды — это ТОЛЬКО бонусные акции, никогда не деньги (см. distributeDividends).
//  - Обратный выкуп акций деньгами проекта не производится — только
//    сведение продавца с покупателем на вторичном рынке (см. matchSellOrder/matchBuyOrder)
//    либо прямая передача акций между участниками (см. handleTransfer).
//  - PLATFORM_FEE — комиссия платформы за посредничество на вторичном рынке.

const PRIMARY_SUPPLY_LIMIT = 10000; // сколько акций максимум может продать сам проект напрямую
const DEFAULT_VALUATION = 10000; // используется, пока админ ни разу не задавал оценку ($1 за акцию)
const DEFAULT_MONTHLY_DIVIDEND_POOL = 100; // бонусных акций в месяц, пока админ не задал своё значение
const PLATFORM_FEE_RATE = 0.07; // 7% комиссия платформы на вторичном рынке

function corsHeaders(env) {
  return {
    "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN || "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
  };
}

function json(data, status, env) {
  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers: { "Content-Type": "application/json", ...corsHeaders(env) },
  });
}

function bufToHex(buf) {
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function hexToBuf(hex) {
  const arr = new Uint8Array(hex.length / 2);
  for (let i = 0; i < arr.length; i++) arr[i] = parseInt(hex.substr(i * 2, 2), 16);
  return arr.buffer;
}

async function hashPassword(password, saltHex) {
  const enc = new TextEncoder();
  const salt = saltHex ? hexToBuf(saltHex) : crypto.getRandomValues(new Uint8Array(16)).buffer;
  const saltHexOut = saltHex || bufToHex(salt);
  const keyMaterial = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: 100000, hash: "SHA-256" },
    keyMaterial,
    256
  );
  return `${saltHexOut}:${bufToHex(bits)}`;
}

async function verifyPassword(password, stored) {
  const [saltHex, hashHex] = stored.split(":");
  const check = await hashPassword(password, saltHex);
  return check === stored;
}

function randomToken() {
  return bufToHex(crypto.getRandomValues(new Uint8Array(32)).buffer);
}

function randomReferralCode() {
  return bufToHex(crypto.getRandomValues(new Uint8Array(4)).buffer);
}

async function getUser(request, env) {
  const auth = request.headers.get("Authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : null;
  if (!token) return null;
  const row = await env.DB.prepare(
    `SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
     WHERE s.token = ? AND s.expires_at > datetime('now')`
  )
    .bind(token)
    .first();
  return row || null;
}

// Цену акции задаёт не алгоритм, а сам админ: он вводит общую сумму (оценку всего
// проекта), и она делится поровну на весь пул акций — так и получается цена одной акции.
// Поднять оценку можно, например, когда на сайт привлечена новая реклама/спонсор.
async function getTotalValuation(env) {
  const row = await env.DB.prepare(`SELECT value FROM site_settings WHERE key = 'total_valuation'`).first();
  const value = row ? parseFloat(row.value) : DEFAULT_VALUATION;
  return value > 0 ? value : DEFAULT_VALUATION;
}

// Сколько акций вообще существует прямо сейчас — включая первичные покупки,
// бонусы за рефералов и бонусные акции-дивиденды (растёт со временем, как при
// обычном stock dividend/bonus issue: доля каждого держателя не размывается,
// потому что дивиденды начисляются всем держателям пропорционально).
async function totalOutstandingShares(env) {
  const row = await env.DB.prepare(`SELECT COALESCE(SUM(quantity), 0) as total FROM shares_ledger`).first();
  return row.total > 0 ? row.total : 0;
}

async function currentPrimaryPrice(env) {
  const stat = await env.DB.prepare(`SELECT value FROM site_stats WHERE key = 'total_shares_sold_primary'`).first();
  const sold = stat ? stat.value : 0;
  const valuation = await getTotalValuation(env);
  const totalShares = (await totalOutstandingShares(env)) || PRIMARY_SUPPLY_LIMIT;
  const price = valuation / totalShares;
  return {
    price: Math.round(price * 100) / 100,
    sold,
    remaining: PRIMARY_SUPPLY_LIMIT - sold,
    valuation,
    total_shares_outstanding: totalShares,
  };
}

// Пул дивидендов на месяц (в акциях, не в деньгах) — настраивается админом,
// используется и ручным /api/admin/dividends/distribute, и автоматическим cron'ом.
async function getMonthlyDividendPool(env) {
  const row = await env.DB.prepare(`SELECT value FROM site_settings WHERE key = 'monthly_dividend_pool'`).first();
  const value = row ? parseInt(row.value, 10) : DEFAULT_MONTHLY_DIVIDEND_POOL;
  return value >= 0 ? value : DEFAULT_MONTHLY_DIVIDEND_POOL;
}

// Дивиденды = бесплатные бонусные акции, никогда не деньги. Раздаются всем
// текущим держателям строго пропорционально их доле в общем количестве акций;
// остаток от округления вниз просто не раздаётся в этом месяце.
async function distributeDividends(env, poolSize, note) {
  const pool = Math.max(0, Math.floor(poolSize || 0));
  if (pool <= 0) return { distributed: 0, holders: 0 };

  const holdings = await env.DB.prepare(
    `SELECT user_id, SUM(quantity) as total FROM shares_ledger GROUP BY user_id HAVING total > 0`
  ).all();
  const totalOutstanding = holdings.results.reduce(function (sum, h) { return sum + h.total; }, 0);
  if (totalOutstanding <= 0) return { distributed: 0, holders: 0 };

  const statements = [];
  let distributed = 0;
  let holdersCount = 0;
  for (const h of holdings.results) {
    const allotment = Math.floor((pool * h.total) / totalOutstanding);
    if (allotment > 0) {
      statements.push(
        env.DB.prepare(`INSERT INTO shares_ledger (user_id, quantity, price_paid, source) VALUES (?, ?, 0, 'dividend')`)
          .bind(h.user_id, allotment)
      );
      distributed += allotment;
      holdersCount += 1;
    }
  }
  if (statements.length === 0) return { distributed: 0, holders: 0 };

  statements.push(
    env.DB.prepare(`INSERT INTO dividend_distributions (total_shares, total_holders, note) VALUES (?, ?, ?)`)
      .bind(distributed, holdersCount, note || null)
  );
  await env.DB.batch(statements);

  return { distributed, holders: holdersCount };
}

// --- Матчинг вторичного рынка --------------------------------------------
// Простая price-time priority модель. Для реального продакшена с высокой
// нагрузкой стоит вынести это в Durable Object ради строгой атомарности;
// для MVP с ожидаемым низким объёмом сделок последовательных запросов достаточно.

async function matchNewSellOrder(env, sellOrder) {
  let remaining = sellOrder.remaining;
  const candidates = await env.DB.prepare(
    `SELECT * FROM buy_orders WHERE status = 'open' AND price_per_share >= ?
     ORDER BY price_per_share DESC, created_at ASC`
  )
    .bind(sellOrder.price_per_share)
    .all();

  for (const buy of candidates.results) {
    if (remaining <= 0) break;
    const tradeQty = Math.min(remaining, buy.remaining);
    const fee = Math.round(tradeQty * buy.price_per_share * PLATFORM_FEE_RATE * 100) / 100;

    await env.DB.batch([
      env.DB.prepare(`INSERT INTO trades (buy_order_id, sell_order_id, quantity, price_per_share, platform_fee)
                       VALUES (?, ?, ?, ?, ?)`).bind(buy.id, sellOrder.id, tradeQty, buy.price_per_share, fee),
      env.DB.prepare(`UPDATE buy_orders SET remaining = remaining - ?, status = CASE WHEN remaining - ? <= 0 THEN 'matched' ELSE status END WHERE id = ?`)
        .bind(tradeQty, tradeQty, buy.id),
      env.DB.prepare(`INSERT INTO shares_ledger (user_id, quantity, price_paid, source) VALUES (?, ?, ?, 'secondary')`)
        .bind(buy.user_id, tradeQty, buy.price_per_share),
      // Списываем проданное количество у продавца — без этой строки акции
      // задваивались бы (продавец формально оставался их держателем).
      env.DB.prepare(`INSERT INTO shares_ledger (user_id, quantity, price_paid, source) VALUES (?, ?, ?, 'secondary')`)
        .bind(sellOrder.user_id, -tradeQty, buy.price_per_share),
    ]);

    remaining -= tradeQty;
  }

  await env.DB.prepare(
    `UPDATE sell_orders SET remaining = ?, status = CASE WHEN ? <= 0 THEN 'matched' ELSE 'open' END WHERE id = ?`
  )
    .bind(remaining, remaining, sellOrder.id)
    .run();

  return remaining;
}

async function matchNewBuyOrder(env, buyOrder) {
  let remaining = buyOrder.remaining;
  const candidates = await env.DB.prepare(
    `SELECT * FROM sell_orders WHERE status = 'open' AND price_per_share <= ?
     ORDER BY price_per_share ASC, created_at ASC`
  )
    .bind(buyOrder.price_per_share)
    .all();

  for (const sell of candidates.results) {
    if (remaining <= 0) break;
    const tradeQty = Math.min(remaining, sell.remaining);
    const fee = Math.round(tradeQty * sell.price_per_share * PLATFORM_FEE_RATE * 100) / 100;

    await env.DB.batch([
      env.DB.prepare(`INSERT INTO trades (buy_order_id, sell_order_id, quantity, price_per_share, platform_fee)
                       VALUES (?, ?, ?, ?, ?)`).bind(buyOrder.id, sell.id, tradeQty, sell.price_per_share, fee),
      env.DB.prepare(`UPDATE sell_orders SET remaining = remaining - ?, status = CASE WHEN remaining - ? <= 0 THEN 'matched' ELSE status END WHERE id = ?`)
        .bind(tradeQty, tradeQty, sell.id),
      env.DB.prepare(`INSERT INTO shares_ledger (user_id, quantity, price_paid, source) VALUES (?, ?, ?, 'secondary')`)
        .bind(buyOrder.user_id, tradeQty, sell.price_per_share),
      // Списываем проданное количество у продавца — без этой строки акции
      // задваивались бы (продавец формально оставался их держателем).
      env.DB.prepare(`INSERT INTO shares_ledger (user_id, quantity, price_paid, source) VALUES (?, ?, ?, 'secondary')`)
        .bind(sell.user_id, -tradeQty, sell.price_per_share),
    ]);

    remaining -= tradeQty;
  }

  await env.DB.prepare(
    `UPDATE buy_orders SET remaining = ?, status = CASE WHEN ? <= 0 THEN 'matched' ELSE 'open' END WHERE id = ?`
  )
    .bind(remaining, remaining, buyOrder.id)
    .run();

  return remaining;
}

// --- Роуты ------------------------------------------------------------

async function handleRegister(request, env) {
  const { email, password, display_name, language, ref } = await request.json();
  if (!email || !password || password.length < 8) {
    return json({ error: "email и пароль (мин. 8 символов) обязательны" }, 400, env);
  }
  const existing = await env.DB.prepare(`SELECT id FROM users WHERE email = ?`).bind(email).first();
  if (existing) return json({ error: "пользователь с таким email уже существует" }, 409, env);

  let referrerId = null;
  if (ref) {
    const referrer = await env.DB.prepare(`SELECT id FROM users WHERE referral_code = ?`).bind(ref).first();
    if (referrer) referrerId = referrer.id;
  }

  const passwordHash = await hashPassword(password);
  const referralCode = randomReferralCode();

  const result = await env.DB.prepare(
    `INSERT INTO users (email, password_hash, display_name, language, referral_code, referred_by)
     VALUES (?, ?, ?, ?, ?, ?)`
  )
    .bind(email, passwordHash, display_name || email.split("@")[0], language || "ru", referralCode, referrerId)
    .run();

  const userId = result.meta.last_row_id;
  const token = randomToken();
  await env.DB.prepare(
    `INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, datetime('now', '+30 days'))`
  )
    .bind(token, userId)
    .run();

  return json({ token, user: { id: userId, email, display_name, referral_code: referralCode } }, 201, env);
}

async function handleLogin(request, env) {
  const { email, password } = await request.json();
  const user = await env.DB.prepare(`SELECT * FROM users WHERE email = ?`).bind(email).first();
  if (!user || !(await verifyPassword(password, user.password_hash))) {
    return json({ error: "неверный email или пароль" }, 401, env);
  }
  const token = randomToken();
  await env.DB.prepare(
    `INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, datetime('now', '+30 days'))`
  )
    .bind(token, user.id)
    .run();
  return json(
    { token, user: { id: user.id, email: user.email, display_name: user.display_name, referral_code: user.referral_code } },
    200,
    env
  );
}

async function handleStats(env) {
  const { price, sold, remaining, valuation, total_shares_outstanding } = await currentPrimaryPrice(env);
  const viewsRow = await env.DB.prepare(`SELECT value FROM site_stats WHERE key = 'total_views'`).first();
  return json(
    {
      price,
      sold_primary: sold,
      remaining_primary: remaining,
      total_supply: PRIMARY_SUPPLY_LIMIT,
      total_shares_outstanding,
      total_views: viewsRow.value,
      valuation,
    },
    200,
    env
  );
}

async function handleTrackView(request, env) {
  const url = new URL(request.url);
  const ref = url.searchParams.get("ref");
  await env.DB.prepare(`UPDATE site_stats SET value = value + 1 WHERE key = 'total_views'`).run();
  if (ref) {
    const referrer = await env.DB.prepare(`SELECT id FROM users WHERE referral_code = ?`).bind(ref).first();
    if (referrer) {
      await env.DB.prepare(`INSERT INTO referral_views (referrer_id) VALUES (?)`).bind(referrer.id).run();
    }
  }
  return json({ ok: true }, 200, env);
}

// Создаёт "намерение покупки" — реальный платёж проводится через Payme/Click,
// см. paymentProvider.js. Акции зачисляются только после подтверждённого вебхука.
async function handlePurchaseIntent(request, env) {
  const user = await getUser(request, env);
  if (!user) return json({ error: "требуется вход" }, 401, env);

  const { quantity } = await request.json();
  const qty = parseInt(quantity, 10);
  if (!qty || qty < 1) return json({ error: "некорректное количество" }, 400, env);

  const { price, remaining } = await currentPrimaryPrice(env);
  if (qty > remaining) return json({ error: `доступно только ${remaining} акций` }, 400, env);

  const id = crypto.randomUUID();
  const totalAmount = Math.round(price * qty * 100) / 100;

  await env.DB.prepare(
    `INSERT INTO purchase_intents (id, user_id, quantity, price_per_share, total_amount)
     VALUES (?, ?, ?, ?, ?)`
  )
    .bind(id, user.id, qty, price, totalAmount)
    .run();

  // TODO: заменить на реальный вызов Payme/Click checkout API (см. README —
  // "Подключение оплаты"), передав id как order_id для последующей сверки в вебхуке.
  const paymentUrl = `${env.PAYMENT_CHECKOUT_BASE_URL || "https://checkout.example/pending"}?order_id=${id}&amount=${totalAmount}`;

  return json({ intent_id: id, total_amount: totalAmount, price_per_share: price, payment_url: paymentUrl }, 200, env);
}

// Вебхук от платёжного провайдера (Payme/Click). Подпись и формат payload
// нужно будет адаптировать под конкретного провайдера — см. README.
async function handlePaymentWebhook(request, env) {
  const payload = await request.json();
  const orderId = payload.order_id; // адаптировать под реальный формат провайдера

  const intent = await env.DB.prepare(`SELECT * FROM purchase_intents WHERE id = ?`).bind(orderId).first();
  if (!intent) return json({ error: "заявка не найдена" }, 404, env);
  if (intent.status === "paid") return json({ ok: true }, 200, env); // идемпотентность

  // TODO: здесь должна быть проверка подписи/статуса от провайдера перед зачислением

  await env.DB.batch([
    env.DB.prepare(`UPDATE purchase_intents SET status = 'paid', paid_at = datetime('now') WHERE id = ?`).bind(orderId),
    env.DB.prepare(`INSERT INTO shares_ledger (user_id, quantity, price_paid, source) VALUES (?, ?, ?, 'primary')`)
      .bind(intent.user_id, intent.quantity, intent.price_per_share),
    env.DB.prepare(`UPDATE site_stats SET value = value + ? WHERE key = 'total_shares_sold_primary'`).bind(intent.quantity),
  ]);

  // Неденежный бонус пригласившему (см. концепцию: только неденежные плюшки)
  const buyer = await env.DB.prepare(`SELECT referred_by FROM users WHERE id = ?`).bind(intent.user_id).first();
  if (buyer && buyer.referred_by) {
    await env.DB.prepare(
      `INSERT INTO shares_ledger (user_id, quantity, price_paid, source) VALUES (?, 1, 0, 'bonus')`
    )
      .bind(buyer.referred_by)
      .run();
  }

  return json({ ok: true }, 200, env);
}

async function handleCabinet(request, env) {
  const user = await getUser(request, env);
  if (!user) return json({ error: "требуется вход" }, 401, env);

  const holdings = await env.DB.prepare(
    `SELECT COALESCE(SUM(quantity), 0) as total FROM shares_ledger WHERE user_id = ?`
  )
    .bind(user.id)
    .first();

  const referralViews = await env.DB.prepare(
    `SELECT COUNT(*) as cnt FROM referral_views WHERE referrer_id = ?`
  )
    .bind(user.id)
    .first();

  const referredCount = await env.DB.prepare(
    `SELECT COUNT(*) as cnt FROM users WHERE referred_by = ?`
  )
    .bind(user.id)
    .first();

  const rank = await env.DB.prepare(
    `SELECT COUNT(*) + 1 as rank FROM (
       SELECT user_id, SUM(quantity) as total FROM shares_ledger GROUP BY user_id HAVING total > ?
     )`
  )
    .bind(holdings.total)
    .first();

  const transfers = await env.DB.prepare(
    `SELECT t.id, t.quantity, t.created_at,
            CASE WHEN t.from_user_id = ? THEN 'out' ELSE 'in' END as direction,
            CASE WHEN t.from_user_id = ? THEN ru.display_name ELSE su.display_name END as counterparty
     FROM transfers t
     JOIN users su ON su.id = t.from_user_id
     JOIN users ru ON ru.id = t.to_user_id
     WHERE t.from_user_id = ? OR t.to_user_id = ?
     ORDER BY t.created_at DESC LIMIT 30`
  )
    .bind(user.id, user.id, user.id, user.id)
    .all();

  // Дивиденды — бонусные акции, начисленные бесплатно (см. distributeDividends).
  const dividendsTotal = await env.DB.prepare(
    `SELECT COALESCE(SUM(quantity), 0) as total FROM shares_ledger WHERE user_id = ? AND source = 'dividend'`
  )
    .bind(user.id)
    .first();
  const dividendsRecent = await env.DB.prepare(
    `SELECT quantity, acquired_at FROM shares_ledger WHERE user_id = ? AND source = 'dividend'
     ORDER BY acquired_at DESC LIMIT 12`
  )
    .bind(user.id)
    .all();

  return json(
    {
      user_id: user.id,
      display_name: user.display_name,
      email: user.email,
      referral_code: user.referral_code,
      shares_held: holdings.total,
      rank: rank.rank,
      referral_views: referralViews.cnt,
      referred_friends: referredCount.cnt,
      transfers: transfers.results,
      dividends_total: dividendsTotal.total,
      dividends_recent: dividendsRecent.results,
    },
    200,
    env
  );
}

// Прямая передача акций между двумя участниками — все "продажи", "покупки" и подарки
// акций на вторичном рынке в конечном счёте сводятся именно к этому: стороны сами
// договариваются об оплате вне сайта, а здесь только меняется владелец нужного
// количества акций. Получателя ищем по email или по реферальному коду.
async function handleTransfer(request, env) {
  const user = await getUser(request, env);
  if (!user) return json({ error: "требуется вход" }, 401, env);

  const { to, quantity, note } = await request.json();
  const qty = parseInt(quantity, 10);
  if (!to || !String(to).trim() || !qty || qty < 1) {
    return json({ error: "укажи получателя (email или реферальный код) и количество акций" }, 400, env);
  }

  const target = String(to).trim();
  const recipient = await env.DB.prepare(
    `SELECT * FROM users WHERE referral_code = ? OR email = ?`
  )
    .bind(target, target)
    .first();
  if (!recipient) return json({ error: "получатель не найден — проверь email или реферальный код" }, 404, env);
  if (recipient.id === user.id) return json({ error: "нельзя передать акции самому себе" }, 400, env);

  const holdings = await env.DB.prepare(
    `SELECT COALESCE(SUM(quantity), 0) as total FROM shares_ledger WHERE user_id = ?`
  )
    .bind(user.id)
    .first();
  const openSells = await env.DB.prepare(
    `SELECT COALESCE(SUM(remaining), 0) as total FROM sell_orders WHERE user_id = ? AND status = 'open'`
  )
    .bind(user.id)
    .first();
  const free = holdings.total - openSells.total;
  if (qty > free) {
    return json({ error: `доступно для передачи только ${free} акций (часть уже выставлена на продажу)` }, 400, env);
  }

  await env.DB.batch([
    env.DB.prepare(`INSERT INTO shares_ledger (user_id, quantity, price_paid, source) VALUES (?, ?, 0, 'transfer_out')`)
      .bind(user.id, -qty),
    env.DB.prepare(`INSERT INTO shares_ledger (user_id, quantity, price_paid, source) VALUES (?, ?, 0, 'transfer_in')`)
      .bind(recipient.id, qty),
    env.DB.prepare(`INSERT INTO transfers (from_user_id, to_user_id, quantity, note) VALUES (?, ?, ?, ?)`)
      .bind(user.id, recipient.id, qty, note ? String(note).slice(0, 300) : null),
  ]);

  return json({ ok: true, transferred: qty, to: recipient.display_name }, 200, env);
}

// --- Админка -------------------------------------------------------------
// requireAdmin возвращает пользователя, только если у него is_admin = 1.
// Первого администратора нужно назначить вручную одной SQL-командой
// после регистрации своего аккаунта — см. README, раздел "Админ-доступ".

async function requireAdmin(request, env) {
  const user = await getUser(request, env);
  if (!user || !user.is_admin) return null;
  return user;
}

async function handleAdminUsersList(request, env) {
  const admin = await requireAdmin(request, env);
  if (!admin) return json({ error: "требуется доступ администратора" }, 403, env);

  const rows = await env.DB.prepare(
    `SELECT u.id, u.email, u.display_name, u.created_at,
            COALESCE(SUM(sl.quantity), 0) as shares_held
     FROM users u
     LEFT JOIN shares_ledger sl ON sl.user_id = u.id
     GROUP BY u.id
     ORDER BY shares_held DESC`
  ).all();

  return json({ users: rows.results }, 200, env);
}

async function handleAdminUserDetail(request, env, userId) {
  const admin = await requireAdmin(request, env);
  if (!admin) return json({ error: "требуется доступ администратора" }, 403, env);

  const user = await env.DB.prepare(
    `SELECT id, email, display_name, language, referral_code, created_at FROM users WHERE id = ?`
  ).bind(userId).first();
  if (!user) return json({ error: "пользователь не найден" }, 404, env);

  const holdings = await env.DB.prepare(
    `SELECT COALESCE(SUM(quantity), 0) as total FROM shares_ledger WHERE user_id = ?`
  ).bind(userId).first();

  const ledger = await env.DB.prepare(
    `SELECT quantity, price_paid, source, acquired_at FROM shares_ledger WHERE user_id = ? ORDER BY acquired_at DESC LIMIT 50`
  ).bind(userId).all();

  const referredCount = await env.DB.prepare(
    `SELECT COUNT(*) as cnt FROM users WHERE referred_by = ?`
  ).bind(userId).first();

  const messages = await env.DB.prepare(
    `SELECT id, admin_id, body, created_at FROM admin_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 50`
  ).bind(userId).all();

  return json(
    {
      user,
      shares_held: holdings.total,
      referred_friends: referredCount.cnt,
      ledger: ledger.results,
      messages: messages.results,
    },
    200,
    env
  );
}

// Админ вводит общую сумму (оценку стоимости проекта целиком) — она делится на
// PRIMARY_SUPPLY_LIMIT акций, так формируется цена одной акции (см. currentPrimaryPrice).
async function handleAdminSetValuation(request, env) {
  const admin = await requireAdmin(request, env);
  if (!admin) return json({ error: "требуется доступ администратора" }, 403, env);

  const { total_valuation } = await request.json();
  const value = parseFloat(total_valuation);
  if (!value || value <= 0) return json({ error: "укажи корректную общую сумму (оценку проекта)" }, 400, env);

  await env.DB.prepare(
    `INSERT INTO site_settings (key, value) VALUES ('total_valuation', ?)
     ON CONFLICT(key) DO UPDATE SET value = excluded.value`
  )
    .bind(String(value))
    .run();

  const { price } = await currentPrimaryPrice(env);
  return json({ ok: true, total_valuation: value, price_per_share: price }, 200, env);
}

// Админ настраивает размер месячного пула дивидендов (в акциях, не в деньгах).
async function handleAdminSetDividendPool(request, env) {
  const admin = await requireAdmin(request, env);
  if (!admin) return json({ error: "требуется доступ администратора" }, 403, env);

  const { monthly_pool } = await request.json();
  const value = parseInt(monthly_pool, 10);
  if (isNaN(value) || value < 0) return json({ error: "укажи корректный размер пула (0 или больше)" }, 400, env);

  await env.DB.prepare(
    `INSERT INTO site_settings (key, value) VALUES ('monthly_dividend_pool', ?)
     ON CONFLICT(key) DO UPDATE SET value = excluded.value`
  )
    .bind(String(value))
    .run();

  return json({ ok: true, monthly_pool: value }, 200, env);
}

// Ручное начисление дивидендов прямо сейчас (например, в конце месяца, если
// автоматический cron ещё не настроен в Cloudflare). Можно передать свой
// размер пула через body.pool, иначе используется настроенный monthly_pool.
async function handleAdminDistributeDividendsNow(request, env) {
  const admin = await requireAdmin(request, env);
  if (!admin) return json({ error: "требуется доступ администратора" }, 403, env);

  const body = await request.json().catch(function () { return {}; });
  const pool = body && body.pool != null ? parseInt(body.pool, 10) : await getMonthlyDividendPool(env);
  if (isNaN(pool) || pool < 0) return json({ error: "некорректный размер пула" }, 400, env);

  const result = await distributeDividends(env, pool, "ручное начисление администратором");
  return json({ ok: true, distributed: result.distributed, holders: result.holders }, 200, env);
}

async function handleAdminDividendHistory(request, env) {
  const admin = await requireAdmin(request, env);
  if (!admin) return json({ error: "требуется доступ администратора" }, 403, env);

  const rows = await env.DB.prepare(
    `SELECT id, total_shares, total_holders, note, created_at FROM dividend_distributions
     ORDER BY created_at DESC LIMIT 24`
  ).all();
  const monthlyPool = await getMonthlyDividendPool(env);
  return json({ distributions: rows.results, monthly_pool: monthlyPool }, 200, env);
}

async function handleAdminSendMessage(request, env) {
  const admin = await requireAdmin(request, env);
  if (!admin) return json({ error: "требуется доступ администратора" }, 403, env);

  const { user_id, body } = await request.json();
  if (!user_id || !body || !body.trim()) return json({ error: "укажи получателя и текст сообщения" }, 400, env);

  await env.DB.prepare(
    `INSERT INTO admin_messages (admin_id, user_id, body) VALUES (?, ?, ?)`
  ).bind(admin.id, user_id, body.trim()).run();

  return json({ ok: true }, 201, env);
}

// Пользователь видит в своём кабинете и сообщения от администратора, и личные
// сообщения от других участников (например, написанные из стакана заявок).
async function handleMyMessages(request, env) {
  const user = await getUser(request, env);
  if (!user) return json({ error: "требуется вход" }, 401, env);

  const admin = await env.DB.prepare(
    `SELECT id, body, created_at FROM admin_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 50`
  ).bind(user.id).all();

  const peer = await env.DB.prepare(
    `SELECT um.id, um.body, um.created_at, um.sender_id, u.display_name as sender_name
     FROM user_messages um JOIN users u ON u.id = um.sender_id
     WHERE um.recipient_id = ? ORDER BY um.created_at DESC LIMIT 50`
  ).bind(user.id).all();

  await env.DB.batch([
    env.DB.prepare(`UPDATE admin_messages SET read_at = datetime('now') WHERE user_id = ? AND read_at IS NULL`).bind(user.id),
    env.DB.prepare(`UPDATE user_messages SET read_at = datetime('now') WHERE recipient_id = ? AND read_at IS NULL`).bind(user.id),
  ]);

  const messages = admin.results
    .map(function (m) {
      return { id: "a" + m.id, body: m.body, created_at: m.created_at, from: "admin", from_user_id: null, from_name: null };
    })
    .concat(
      peer.results.map(function (m) {
        return { id: "u" + m.id, body: m.body, created_at: m.created_at, from: "user", from_user_id: m.sender_id, from_name: m.sender_name };
      })
    )
    .sort(function (a, b) { return a.created_at < b.created_at ? 1 : -1; });

  return json({ messages }, 200, env);
}

// Личное сообщение одного держателя акций другому — например, чтобы договориться
// о цене и оплате перед тем, как воспользоваться /api/transfer.
async function handleSendUserMessage(request, env) {
  const user = await getUser(request, env);
  if (!user) return json({ error: "требуется вход" }, 401, env);

  const { to_user_id, body } = await request.json();
  const recipientId = parseInt(to_user_id, 10);
  if (!recipientId || !body || !body.trim()) return json({ error: "укажи получателя и текст сообщения" }, 400, env);
  if (recipientId === user.id) return json({ error: "нельзя написать самому себе" }, 400, env);

  const recipient = await env.DB.prepare(`SELECT id FROM users WHERE id = ?`).bind(recipientId).first();
  if (!recipient) return json({ error: "получатель не найден" }, 404, env);

  await env.DB.prepare(
    `INSERT INTO user_messages (sender_id, recipient_id, body) VALUES (?, ?, ?)`
  )
    .bind(user.id, recipientId, body.trim().slice(0, 1000))
    .run();

  return json({ ok: true }, 201, env);
}

async function handleCreateSellOrder(request, env) {
  const user = await getUser(request, env);
  if (!user) return json({ error: "требуется вход" }, 401, env);

  const { quantity, price_per_share } = await request.json();
  const qty = parseInt(quantity, 10);
  const price = parseFloat(price_per_share);
  if (!qty || qty < 1 || !price || price <= 0) return json({ error: "некорректные параметры" }, 400, env);

  const holdings = await env.DB.prepare(
    `SELECT COALESCE(SUM(quantity), 0) as total FROM shares_ledger WHERE user_id = ?`
  )
    .bind(user.id)
    .first();
  const openSells = await env.DB.prepare(
    `SELECT COALESCE(SUM(remaining), 0) as total FROM sell_orders WHERE user_id = ? AND status = 'open'`
  )
    .bind(user.id)
    .first();
  if (qty > holdings.total - openSells.total) {
    return json({ error: "недостаточно свободных акций (часть уже выставлена на продажу)" }, 400, env);
  }

  const result = await env.DB.prepare(
    `INSERT INTO sell_orders (user_id, quantity, remaining, price_per_share) VALUES (?, ?, ?, ?)`
  )
    .bind(user.id, qty, qty, price)
    .run();

  const orderId = result.meta.last_row_id;
  const order = { id: orderId, user_id: user.id, quantity: qty, remaining: qty, price_per_share: price };
  const remaining = await matchNewSellOrder(env, order);

  return json({ order_id: orderId, remaining_after_match: remaining }, 201, env);
}

async function handleCreateBuyOrder(request, env) {
  const user = await getUser(request, env);
  if (!user) return json({ error: "требуется вход" }, 401, env);

  const { quantity, price_per_share } = await request.json();
  const qty = parseInt(quantity, 10);
  const price = parseFloat(price_per_share);
  if (!qty || qty < 1 || !price || price <= 0) return json({ error: "некорректные параметры" }, 400, env);

  // Примечание: оплата за buy-заявку на вторичном рынке должна списываться
  // через тот же платёжный провайдер при фактическом исполнении сделки —
  // в MVP для простоты предполагается предоплаченный баланс либо
  // отдельный purchase_intent на сумму qty*price (реализовать по аналогии
  // с handlePurchaseIntent перед вызовом этого роута).

  const result = await env.DB.prepare(
    `INSERT INTO buy_orders (user_id, quantity, remaining, price_per_share) VALUES (?, ?, ?, ?)`
  )
    .bind(user.id, qty, qty, price)
    .run();

  const orderId = result.meta.last_row_id;
  const order = { id: orderId, user_id: user.id, quantity: qty, remaining: qty, price_per_share: price };
  const remaining = await matchNewBuyOrder(env, order);

  return json({ order_id: orderId, remaining_after_match: remaining }, 201, env);
}

// Заявки отдаются поштучно (не агрегированные по цене), с именем автора заявки —
// это нужно, чтобы участник мог кликнуть по чужой заявке в стакане и написать
// её автору личное сообщение, договориться о сделке и затем сделать /api/transfer.
async function handleOrderbook(env) {
  const sells = await env.DB.prepare(
    `SELECT so.id, so.user_id, u.display_name, so.remaining as qty, so.price_per_share
     FROM sell_orders so JOIN users u ON u.id = so.user_id
     WHERE so.status = 'open' ORDER BY so.price_per_share ASC, so.created_at ASC LIMIT 20`
  ).all();
  const buys = await env.DB.prepare(
    `SELECT bo.id, bo.user_id, u.display_name, bo.remaining as qty, bo.price_per_share
     FROM buy_orders bo JOIN users u ON u.id = bo.user_id
     WHERE bo.status = 'open' ORDER BY bo.price_per_share DESC, bo.created_at ASC LIMIT 20`
  ).all();
  return json({ sells: sells.results, buys: buys.results }, 200, env);
}

async function handleRecentTrades(env) {
  const trades = await env.DB.prepare(
    `SELECT quantity, price_per_share, executed_at FROM trades ORDER BY executed_at DESC LIMIT 50`
  ).all();
  return json({ trades: trades.results }, 200, env);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders(env) });
    }

    try {
      if (url.pathname === "/api/register" && request.method === "POST") return await handleRegister(request, env);
      if (url.pathname === "/api/login" && request.method === "POST") return await handleLogin(request, env);
      if (url.pathname === "/api/stats" && request.method === "GET") return await handleStats(env);
      if (url.pathname === "/api/view" && request.method === "POST") return await handleTrackView(request, env);
      if (url.pathname === "/api/purchase/intent" && request.method === "POST") return await handlePurchaseIntent(request, env);
      if (url.pathname === "/api/payment/webhook" && request.method === "POST") return await handlePaymentWebhook(request, env);
      if (url.pathname === "/api/cabinet" && request.method === "GET") return await handleCabinet(request, env);
      if (url.pathname === "/api/transfer" && request.method === "POST") return await handleTransfer(request, env);
      if (url.pathname === "/api/orders/sell" && request.method === "POST") return await handleCreateSellOrder(request, env);
      if (url.pathname === "/api/orders/buy" && request.method === "POST") return await handleCreateBuyOrder(request, env);
      if (url.pathname === "/api/orderbook" && request.method === "GET") return await handleOrderbook(env);
      if (url.pathname === "/api/trades/recent" && request.method === "GET") return await handleRecentTrades(env);
      if (url.pathname === "/api/messages" && request.method === "GET") return await handleMyMessages(request, env);
      if (url.pathname === "/api/messages/send" && request.method === "POST") return await handleSendUserMessage(request, env);

      if (url.pathname === "/api/admin/users" && request.method === "GET") return await handleAdminUsersList(request, env);
      if (url.pathname === "/api/admin/message" && request.method === "POST") return await handleAdminSendMessage(request, env);
      if (url.pathname === "/api/admin/valuation" && request.method === "POST") return await handleAdminSetValuation(request, env);
      if (url.pathname === "/api/admin/dividends/pool" && request.method === "POST") return await handleAdminSetDividendPool(request, env);
      if (url.pathname === "/api/admin/dividends/distribute" && request.method === "POST") return await handleAdminDistributeDividendsNow(request, env);
      if (url.pathname === "/api/admin/dividends" && request.method === "GET") return await handleAdminDividendHistory(request, env);
      const userDetailMatch = url.pathname.match(/^\/api\/admin\/users\/(\d+)$/);
      if (userDetailMatch && request.method === "GET") return await handleAdminUserDetail(request, env, userDetailMatch[1]);

      return json({ error: "not found" }, 404, env);
    } catch (err) {
      return json({ error: "internal error", detail: String(err) }, 500, env);
    }
  },

  // Автоматическое ежемесячное начисление дивидендов бонусными акциями —
  // расписание задаётся в wrangler.toml ([triggers] crons), например
  // "5 0 1 * *" (00:05 UTC 1-го числа каждого месяца). Деньги здесь никогда
  // не участвуют — только акции, пропорционально текущим держателям.
  async scheduled(event, env, ctx) {
    const pool = await getMonthlyDividendPool(env);
    await distributeDividends(env, pool, "автоматическое ежемесячное начисление (cron)");
  },
};

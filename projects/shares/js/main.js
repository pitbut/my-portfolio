let priceChart = null;

function renderAuthArea() {
    const area = document.getElementById("auth-area");
    if (authToken()) {
        area.innerHTML = '<a class="link-inline" href="cabinet.html" style="margin-left:10px;">' + t("nav_cabinet") + '</a>';
    } else {
        area.innerHTML =
            '<a class="link-inline" href="login.html" style="margin-left:10px;">' + t("nav_login") + '</a>' +
            '<a class="link-inline" href="register.html" style="margin-left:10px;">' + t("nav_register") + '</a>';
    }
}

async function loadStats() {
    const stats = await api("/api/stats");
    document.getElementById("stat-price").textContent = "$" + stats.price.toFixed(2);
    document.getElementById("stat-sold").textContent = stats.sold_primary + " / " + stats.total_supply;
    document.getElementById("stat-views").textContent = stats.total_views.toLocaleString("ru-RU");
}

async function loadChart() {
    const data = await api("/api/trades/recent");
    const trades = data.trades.slice().reverse();
    const labels = trades.map(function (t, i) { return i + 1; });
    const prices = trades.map(function (t) { return t.price_per_share; });

    const ctx = document.getElementById("priceChart");
    if (priceChart) priceChart.destroy();
    priceChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                data: prices,
                borderColor: "#2a78d6",
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.3,
                fill: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: { ticks: { callback: function (v) { return "$" + v.toFixed(2); } } },
            },
        },
    });
}

async function loadReferral() {
    if (!authToken()) return;
    try {
        const cabinet = await api("/api/cabinet");
        document.getElementById("ref-link").value = myReferralLink(cabinet.referral_code);
        document.getElementById("ref-stats").textContent = t("referral_stats", {
            views: cabinet.referral_views,
            friends: cabinet.referred_friends,
        });
    } catch (e) {
        // токен истёк — тихо игнорируем на главной странице
    }
}

// Не считаем повторным просмотром каждое сворачивание/разворачивание вкладки —
// на мобильных браузер часто перезагружает страницу при возврате из фона,
// и trackView() запускался бы заново за доли секунды. Поэтому считаем не чаще
// одного просмотра с одного браузера за VIEW_THROTTLE_MS.
const VIEW_THROTTLE_MS = 30 * 60 * 1000; // 30 минут

function trackView() {
    const last = parseInt(localStorage.getItem("shares_last_view") || "0", 10);
    const now = Date.now();
    if (now - last < VIEW_THROTTLE_MS) return;
    localStorage.setItem("shares_last_view", String(now));

    const ref = getReferralCodeFromUrl();
    const path = ref ? "/api/view?ref=" + encodeURIComponent(ref) : "/api/view";
    api(path, { method: "POST" }).catch(function () {});
}

document.getElementById("buy-btn").addEventListener("click", async function () {
    const errorEl = document.getElementById("buy-error");
    errorEl.textContent = "";
    if (!authToken()) {
        window.location.href = "register.html" + window.location.search;
        return;
    }
    const qty = parseInt(document.getElementById("buy-qty").value, 10);
    try {
        const intent = await api("/api/purchase/intent", { method: "POST", body: { quantity: qty } });
        // Реальная оплата происходит на стороне провайдера (Payme/Click),
        // после успешной оплаты провайдер вызовет /api/payment/webhook,
        // и акции будут зачислены автоматически.
        window.location.href = intent.payment_url;
    } catch (e) {
        errorEl.textContent = e.message;
    }
});

document.getElementById("copy-ref").addEventListener("click", function () {
    const input = document.getElementById("ref-link");
    input.select();
    document.execCommand("copy");
});

renderAuthArea();
trackView();
loadStats();
loadChart();
loadReferral();

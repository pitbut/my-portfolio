let selectedUserId = null;

async function loadValuation() {
    try {
        const stats = await api("/api/stats");
        document.getElementById("valuation-input").value = stats.valuation;
        document.getElementById("valuation-current").textContent =
            t("valuation_current", { valuation: stats.valuation, price: stats.price.toFixed(2) });
    } catch (e) {
        // не критично для остальной страницы — просто оставляем поле пустым
    }
}

document.getElementById("valuation-btn").addEventListener("click", async function () {
    const errorEl = document.getElementById("valuation-error");
    errorEl.textContent = "";
    try {
        const res = await api("/api/admin/valuation", {
            method: "POST",
            body: { total_valuation: parseFloat(document.getElementById("valuation-input").value) },
        });
        document.getElementById("valuation-current").textContent =
            t("valuation_current", { valuation: res.total_valuation, price: res.price_per_share.toFixed(2) });
    } catch (e) {
        errorEl.textContent = e.message;
    }
});

function renderDividendHistory(rows) {
    const box = document.getElementById("dividend-history");
    box.innerHTML = rows
        .map(function (d) {
            return (
                "<div class='ledger-row'>" +
                    escapeHtml(t("dividend_history_row", { date: d.created_at.slice(0, 16), shares: d.total_shares, holders: d.total_holders })) +
                "</div>"
            );
        })
        .join("") || "<div class='ledger-row'>" + t("no_dividend_history") + "</div>";
}

async function loadDividendHistory() {
    try {
        const data = await api("/api/admin/dividends");
        renderDividendHistory(data.distributions);
        document.getElementById("dividend-pool-input").value = data.monthly_pool;
    } catch (e) {
        // недостаточно прав или не загрузилось — просто оставляем пустым
    }
}

document.getElementById("dividend-pool-btn").addEventListener("click", async function () {
    const errorEl = document.getElementById("dividend-error");
    errorEl.textContent = "";
    try {
        const res = await api("/api/admin/dividends/pool", {
            method: "POST",
            body: { monthly_pool: parseInt(document.getElementById("dividend-pool-input").value, 10) },
        });
        errorEl.style.color = "#1e824c";
        errorEl.textContent = t("save_dividend_pool_button") + ": " + res.monthly_pool;
    } catch (e) {
        errorEl.style.color = "#c0392b";
        errorEl.textContent = e.message;
    }
});

document.getElementById("dividend-distribute-btn").addEventListener("click", async function () {
    const errorEl = document.getElementById("dividend-error");
    errorEl.textContent = "";
    if (!window.confirm(t("distribute_confirm"))) return;
    try {
        const poolValue = document.getElementById("dividend-pool-input").value;
        const body = poolValue ? { pool: parseInt(poolValue, 10) } : {};
        const res = await api("/api/admin/dividends/distribute", { method: "POST", body: body });
        errorEl.style.color = "#1e824c";
        errorEl.textContent = t("dividend_distribute_success", { shares: res.distributed, holders: res.holders });
        loadDividendHistory();
        loadUsersList();
    } catch (e) {
        errorEl.style.color = "#c0392b";
        errorEl.textContent = e.message;
    }
});

async function loadUsersList() {
    try {
        const data = await api("/api/admin/users");
        const body = document.getElementById("users-table-body");
        body.innerHTML = data.users
            .map(function (u) {
                return (
                    "<tr data-user-id='" + u.id + "'>" +
                        "<td>" + escapeHtml(u.display_name) + "</td>" +
                        "<td>" + escapeHtml(u.email) + "</td>" +
                        "<td>" + u.shares_held + "</td>" +
                        "<td>" + u.created_at.slice(0, 10) + "</td>" +
                    "</tr>"
                );
            })
            .join("");
        body.querySelectorAll("tr[data-user-id]").forEach(function (row) {
            row.addEventListener("click", function () {
                openUserDetail(parseInt(row.getAttribute("data-user-id"), 10));
            });
        });
    } catch (e) {
        document.getElementById("admin-content").classList.add("detail-hidden");
        document.getElementById("access-denied").classList.remove("detail-hidden");
    }
}

async function openUserDetail(userId) {
    selectedUserId = userId;
    const data = await api("/api/admin/users/" + userId);
    document.getElementById("user-detail-card").classList.remove("detail-hidden");
    document.getElementById("detail-name").textContent = data.user.display_name;
    document.getElementById("detail-email").textContent = data.user.email;
    document.getElementById("detail-shares").textContent = data.shares_held;
    document.getElementById("detail-referred").textContent = data.referred_friends;

    document.getElementById("detail-ledger").innerHTML = data.ledger
        .map(function (l) {
            return (
                "<div class='ledger-row'>" +
                    l.acquired_at.slice(0, 16) + " · " + l.quantity + " акц. · $" + l.price_paid.toFixed(2) +
                    " · " + l.source +
                "</div>"
            );
        })
        .join("") || "<div class='ledger-row'>" + t("no_operations") + "</div>";

    document.getElementById("detail-messages").innerHTML = data.messages
        .map(function (m) {
            return "<div class='msg-item'>" + escapeHtml(m.body) + "<div class='msg-date'>" + m.created_at.slice(0, 16) + "</div></div>";
        })
        .join("") || "<div class='msg-item'>" + t("no_sent_messages") + "</div>";
}

document.getElementById("send-message-btn").addEventListener("click", async function () {
    const errorEl = document.getElementById("message-error");
    errorEl.textContent = "";
    const body = document.getElementById("message-body").value;
    if (!selectedUserId) return;
    try {
        await api("/api/admin/message", { method: "POST", body: { user_id: selectedUserId, body: body } });
        document.getElementById("message-body").value = "";
        openUserDetail(selectedUserId);
    } catch (e) {
        errorEl.textContent = e.message;
    }
});

if (!authToken()) {
    window.location.href = "login.html";
} else {
    loadUsersList();
    loadValuation();
    loadDividendHistory();
}

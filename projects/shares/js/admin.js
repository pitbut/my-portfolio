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
}

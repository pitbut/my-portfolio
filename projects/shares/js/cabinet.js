if (!authToken()) {
    window.location.href = "login.html";
}

let myUserId = null;
let composeToUserId = null;

async function loadCabinet() {
    try {
        const c = await api("/api/cabinet");
        myUserId = c.user_id;
        document.getElementById("cab-name").textContent = c.display_name;
        document.getElementById("cab-rank").textContent = t("rank_label", { rank: c.rank });
        document.getElementById("cab-shares").textContent = c.shares_held;
        document.getElementById("cab-refviews").textContent = c.referral_views;
        document.getElementById("cab-reffriends").textContent = c.referred_friends;
        document.getElementById("cab-ref-link").value = myReferralLink(c.referral_code);
        renderTransferHistory(c.transfers || []);
        renderDividends(c.dividends_total || 0, c.dividends_recent || []);
    } catch (e) {
        localStorage.removeItem("shares_token");
        window.location.href = "login.html";
    }
}

function renderDividends(total, recent) {
    document.getElementById("dividends-total").textContent = total;
    const box = document.getElementById("dividends-history");
    box.innerHTML = recent
        .map(function (d) {
            return (
                "<div class='transfer-row'>" +
                    t("dividend_row", { qty: d.quantity }) +
                    "<span style='color:#999;'> · " + d.acquired_at.slice(0, 16) + "</span>" +
                "</div>"
            );
        })
        .join("") || "<div class='transfer-row' style='color:#999;'>" + t("no_dividends") + "</div>";
}

function renderTransferHistory(transfers) {
    const box = document.getElementById("transfer-history");
    box.innerHTML = transfers
        .map(function (tr) {
            const sign = tr.direction === "out" ? "−" : "+";
            const label = tr.direction === "out"
                ? t("transfer_sent_to", { name: tr.counterparty })
                : t("transfer_received_from", { name: tr.counterparty });
            return (
                "<div class='transfer-row'>" +
                    sign + tr.quantity + " · " + escapeHtml(label) +
                    "<span style='color:#999;'> · " + tr.created_at.slice(0, 16) + "</span>" +
                "</div>"
            );
        })
        .join("") || "<div class='transfer-row' style='color:#999;'>" + t("no_transfers") + "</div>";
}

async function loadOrderbook() {
    const data = await api("/api/orderbook");
    const rows = [];
    const maxLen = Math.max(data.sells.length, data.buys.length);
    rows.push("<tr><td><strong>" + t("orderbook_selling") + "</strong></td><td><strong>" + t("orderbook_buying") + "</strong></td></tr>");
    for (let i = 0; i < maxLen; i++) {
        const s = data.sells[i];
        const b = data.buys[i];
        rows.push(
            "<tr>" +
                "<td class='sell'" + (s ? " data-user='" + s.user_id + "' data-name=\"" + escapeAttr(s.display_name) + "\"" : "") + ">" +
                    (s ? "$" + s.price_per_share.toFixed(2) + " × " + s.qty + " (" + escapeHtml(s.display_name) + ")" : "") +
                "</td>" +
                "<td class='buy'" + (b ? " data-user='" + b.user_id + "' data-name=\"" + escapeAttr(b.display_name) + "\"" : "") + ">" +
                    (b ? "$" + b.price_per_share.toFixed(2) + " × " + b.qty + " (" + escapeHtml(b.display_name) + ")" : "") +
                "</td>" +
            "</tr>"
        );
    }
    const table = document.getElementById("orderbook-table");
    table.innerHTML = rows.join("");
    table.querySelectorAll("td[data-user]").forEach(function (td) {
        td.addEventListener("click", function () {
            openCompose(parseInt(td.getAttribute("data-user"), 10), td.getAttribute("data-name"));
        });
    });
}

function openCompose(userId, name) {
    if (!userId || userId === myUserId) return;
    composeToUserId = userId;
    document.getElementById("compose-card").classList.remove("detail-hidden");
    document.getElementById("compose-to").textContent = t("compose_to", { name: name });
    document.getElementById("compose-body").value = "";
    document.getElementById("compose-error").textContent = "";
    document.getElementById("compose-card").scrollIntoView({ behavior: "smooth", block: "center" });
}

document.getElementById("compose-send-btn").addEventListener("click", async function () {
    const errorEl = document.getElementById("compose-error");
    errorEl.textContent = "";
    try {
        await api("/api/messages/send", {
            method: "POST",
            body: { to_user_id: composeToUserId, body: document.getElementById("compose-body").value },
        });
        document.getElementById("compose-card").classList.add("detail-hidden");
        loadMessages();
    } catch (e) {
        errorEl.textContent = e.message;
    }
});

document.getElementById("sell-btn").addEventListener("click", async function () {
    const errorEl = document.getElementById("sell-error");
    errorEl.textContent = "";
    try {
        await api("/api/orders/sell", {
            method: "POST",
            body: {
                quantity: parseInt(document.getElementById("sell-qty").value, 10),
                price_per_share: parseFloat(document.getElementById("sell-price").value),
            },
        });
        loadOrderbook();
        loadCabinet();
    } catch (e) {
        errorEl.textContent = e.message;
    }
});

document.getElementById("transfer-btn").addEventListener("click", async function () {
    const errorEl = document.getElementById("transfer-error");
    errorEl.textContent = "";
    errorEl.style.color = "#c0392b";
    try {
        const res = await api("/api/transfer", {
            method: "POST",
            body: {
                to: document.getElementById("transfer-to").value.trim(),
                quantity: parseInt(document.getElementById("transfer-qty").value, 10),
            },
        });
        errorEl.style.color = "#1e824c";
        errorEl.textContent = t("transfer_success", { qty: res.transferred, name: res.to });
        document.getElementById("transfer-to").value = "";
        document.getElementById("transfer-qty").value = "";
        loadCabinet();
    } catch (e) {
        errorEl.style.color = "#c0392b";
        errorEl.textContent = e.message;
    }
});

document.getElementById("cab-copy-ref").addEventListener("click", function () {
    const input = document.getElementById("cab-ref-link");
    input.select();
    document.execCommand("copy");
});

document.getElementById("logout-btn").addEventListener("click", function () {
    localStorage.removeItem("shares_token");
    window.location.href = "index.html";
});

async function loadMessages() {
    const data = await api("/api/messages");
    const list = document.getElementById("messages-list");
    list.innerHTML = data.messages
        .map(function (m) {
            const from = m.from === "admin" ? t("from_admin") : t("from_user", { name: m.from_name });
            const replyAttr = m.from === "user"
                ? " data-reply-user='" + m.from_user_id + "' data-reply-name=\"" + escapeAttr(m.from_name) + "\""
                : "";
            return (
                "<div class='msg-row'" + replyAttr + " style='font-size:13px; padding:6px 0; border-bottom:1px dashed #eee;'>" +
                    "<div style='color:#777; font-size:11px;'>" + escapeHtml(from) + "</div>" +
                    "<div>" + escapeHtml(m.body) + "</div>" +
                    "<div style='color:#999; font-size:11px;'>" + m.created_at.slice(0, 16) + "</div>" +
                    (m.from === "user" ? "<button class='secondary reply-btn' data-i18n='reply_button'>" + t("reply_button") + "</button>" : "") +
                "</div>"
            );
        })
        .join("") || "<div style='font-size:13px; color:#999;'>" + t("no_messages") + "</div>";

    list.querySelectorAll(".reply-btn").forEach(function (btn) {
        const row = btn.closest(".msg-row");
        btn.addEventListener("click", function () {
            openCompose(parseInt(row.getAttribute("data-reply-user"), 10), row.getAttribute("data-reply-name"));
        });
    });
}

loadCabinet();
loadOrderbook();
loadMessages();

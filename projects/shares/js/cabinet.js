if (!authToken()) {
    window.location.href = "login.html";
}

async function loadCabinet() {
    try {
        const c = await api("/api/cabinet");
        document.getElementById("cab-name").textContent = c.display_name;
        document.getElementById("cab-rank").textContent = "Место в рейтинге: #" + c.rank;
        document.getElementById("cab-shares").textContent = c.shares_held;
        document.getElementById("cab-refviews").textContent = c.referral_views;
        document.getElementById("cab-reffriends").textContent = c.referred_friends;
        document.getElementById("cab-ref-link").value = myReferralLink(c.referral_code);
    } catch (e) {
        localStorage.removeItem("shares_token");
        window.location.href = "login.html";
    }
}

async function loadOrderbook() {
    const data = await api("/api/orderbook");
    const rows = [];
    const maxLen = Math.max(data.sells.length, data.buys.length);
    rows.push("<tr><td><strong>Продают</strong></td><td><strong>Покупают</strong></td></tr>");
    for (let i = 0; i < maxLen; i++) {
        const s = data.sells[i];
        const b = data.buys[i];
        rows.push(
            "<tr>" +
                "<td class='sell'>" + (s ? "$" + s.price_per_share.toFixed(2) + " × " + s.qty : "") + "</td>" +
                "<td class='buy'>" + (b ? "$" + b.price_per_share.toFixed(2) + " × " + b.qty : "") + "</td>" +
            "</tr>"
        );
    }
    document.getElementById("orderbook-table").innerHTML = rows.join("");
}

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
            return (
                "<div style='font-size:13px; padding:6px 0; border-bottom:1px dashed #eee;'>" +
                    m.body +
                    "<div style='color:#999; font-size:11px;'>" + m.created_at.slice(0, 16) + "</div>" +
                "</div>"
            );
        })
        .join("") || "<div style='font-size:13px; color:#999;'>сообщений пока нет</div>";
}

loadCabinet();
loadOrderbook();
loadMessages();

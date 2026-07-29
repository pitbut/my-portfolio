let selectedUserId = null;

async function loadUsersList() {
    try {
        const data = await api("/api/admin/users");
        const body = document.getElementById("users-table-body");
        body.innerHTML = data.users
            .map(function (u) {
                return (
                    "<tr onclick='openUserDetail(" + u.id + ")'>" +
                        "<td>" + u.display_name + "</td>" +
                        "<td>" + u.email + "</td>" +
                        "<td>" + u.shares_held + "</td>" +
                        "<td>" + u.created_at.slice(0, 10) + "</td>" +
                    "</tr>"
                );
            })
            .join("");
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
        .join("") || "<div class='ledger-row'>нет операций</div>";

    document.getElementById("detail-messages").innerHTML = data.messages
        .map(function (m) {
            return "<div class='msg-item'>" + m.body + "<div class='msg-date'>" + m.created_at.slice(0, 16) + "</div></div>";
        })
        .join("") || "<div class='msg-item'>сообщений пока не было</div>";
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
}

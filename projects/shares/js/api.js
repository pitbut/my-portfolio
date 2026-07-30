// Базовый адрес API — Cloudflare Worker, задеплоенный из папки /worker.
// После деплоя (wrangler deploy) подставь сюда реальный адрес,
// например https://robutpit-shares-api.<твой-субдомен>.workers.dev
// либо настрой Custom Domain на api.robutpit.com для красоты.
const API_BASE = "https://api.robutpit.com";

function authToken() {
    return localStorage.getItem("shares_token");
}

async function api(path, options) {
    options = options || {};
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const token = authToken();
    if (token) headers["Authorization"] = "Bearer " + token;

    const res = await fetch(API_BASE + path, {
        method: options.method || "GET",
        headers: headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
    });

    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) {
        const err = new Error(data.error || "Ошибка запроса");
        err.data = data; // например, data.needs_verification — email ещё не подтверждён
        throw err;
    }
    return data;
}

function getReferralCodeFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get("ref");
}

function myReferralLink(code) {
    return "https://www.robutpit.com/projects/shares/?ref=" + code;
}

function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeAttr(s) {
    return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}

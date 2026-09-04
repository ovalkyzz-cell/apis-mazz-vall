const crypto = require('crypto');

const BASE = 'https://www.dapjimotionpro.my.id';
const UA = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Mobile Safari/537.36';
const TIMEOUT = 45000;

const baseHeaders = {
    'User-Agent': UA,
    'Accept': '*/*',
    'Content-Type': 'application/json',
    'Origin': BASE,
    'Accept-Language': 'en-US,en;q=0.9,id-ID;q=0.8,id;q=0.7'
};

async function post(url, body, referer) {
    const res = await fetch(url, {
        method: 'POST',
        signal: AbortSignal.timeout(TIMEOUT),
        headers: { ...baseHeaders, 'Referer': referer },
        body: JSON.stringify(body)
    });
    const text = await res.text();
    try { return { http: res.status, data: JSON.parse(text) }; }
    catch { return { http: res.status, data: { success: false, raw: text.slice(0, 300) } }; }
}

// V3 Rafael
async function v3Send(email) {
    const { http, data } = await post(
        `${BASE}/api/proxy-rafael?action=send`,
        { email },
        `${BASE}/generator-v3`
    );
    if (data.status === false || data.status === 'error' || (data.success !== undefined && !data.success)) {
        return { ok: false, version: 'v3', message: data.msg || data.message || data.error || `HTTP ${http}` };
    }
    return { ok: true, version: 'v3', message: data.msg || data.message || 'Link berhasil dikirim', email };
}

async function v3Verify(email, link) {
    const { http, data } = await post(
        `${BASE}/api/proxy-rafael?action=verify`,
        { email, rawLink: link.trim() },
        `${BASE}/generator-v3`
    );
    if (data.status === false || data.status === 'error' || (data.success !== undefined && !data.success)) {
        return { ok: false, version: 'v3', message: data.msg || data.message || data.error || `HTTP ${http}` };
    }
    return { ok: true, version: 'v3', message: data.msg || data.message || 'Premium activated!', data: data.data || data };
}

// V4 QSR
async function v4Send(email) {
    const { http, data } = await post(
        `${BASE}/api/proxy-qsr`,
        { action: 'send', email },
        `${BASE}/generator-v4`
    );
    if (data.status === false || data.status === 'error' || (data.success !== undefined && !data.success)) {
        return { ok: false, version: 'v4', message: data.msg || data.message || data.error || `HTTP ${http}` };
    }
    return { ok: true, version: 'v4', message: data.msg || data.message || 'Link berhasil dikirim', email };
}

async function v4Verify(email, link) {
    const { http, data } = await post(
        `${BASE}/api/proxy-qsr`,
        { action: 'verify', email, link: link.trim() },
        `${BASE}/generator-v4`
    );
    if (data.status === false || data.status === 'error' || (data.success !== undefined && !data.success)) {
        return { ok: false, version: 'v4', message: data.msg || data.message || data.error || `HTTP ${http}` };
    }
    return { ok: true, version: 'v4', message: data.msg || data.message || 'Premium activated!', data: data.data || data };
}

module.exports = { v3Send, v3Verify, v4Send, v4Verify };

from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
import json, os, uuid, string, random, hashlib, time, re, secrets
from datetime import datetime, timedelta
from functools import wraps
import requests
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mazvall-official-secret-key-2026-secure')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')

# ============================================
# KONFIGURASI
# ============================================
CONFIG = {
    "DAILYMOTION_BASE": "https://www.kuroneko.biz.id/api/dailymotion",
    "KEYRAFA_BASE": "https://www.keyrafara.com",
    "ALIGHT_BASE": "https://www.alightpro.my.id",
    "ALIGHT_SECRET": "amprem-human-v3-secret-2026",
    "TIMEOUT": 45,
    "API_KEY_DB": "api_keys_external.json"
}

# ============================================
# SISTEM API KEY UNTUK TOOLS
# ============================================
_memory_ext_keys = {"keys": []}

def load_external_keys():
    return _memory_ext_keys

def save_external_keys(data):
    global _memory_ext_keys
    _memory_ext_keys = data

def generate_external_key():
    return f"TOOL-{uuid.uuid4().hex[:16].upper()}"

def validate_external_key(api_key):
    if not api_key:
        return False
    data = load_external_keys()
    for key_data in data.get("keys", []):
        if key_data["key"] == api_key:
            if key_data.get("expired_at"):
                if datetime.fromisoformat(key_data["expired_at"]) < datetime.now():
                    return False
            return True
    return False

def require_tool_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key") or request.form.get("api_key")
        if not api_key:
            return jsonify({"status": "error", "message": "API key required"}), 401
        if not validate_external_key(api_key):
            return jsonify({"status": "error", "message": "Invalid or expired API key"}), 401
        return f(*args, **kwargs)
    return decorated

# ============================================
# CLASS: DAILYMOTION API
# ============================================
class DailymotionAPI:
    def __init__(self):
        self.base_url = CONFIG["DAILYMOTION_BASE"]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})

    def _request(self, endpoint="", params=None):
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=CONFIG["TIMEOUT"])
            if resp.status_code == 200:
                return resp.json()
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_videos(self, **kwargs):
        return self._request("", {k: v for k, v in kwargs.items() if v is not None})

    def get_video(self, video_id):
        return self._request(f"/video/{video_id}")

    def get_channels(self, page=None, limit=None):
        params = {}
        if page: params["page"] = page
        if limit: params["limit"] = limit
        return self._request("/channels", params)

    def health(self):
        return self._request("/health")

# ============================================
# CLASS: KEYRAFA API
# ============================================
class KeyrafaAPI:
    def __init__(self):
        self.base_url = CONFIG["KEYRAFA_BASE"]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})

    def _request(self, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=CONFIG["TIMEOUT"])
            if resp.status_code == 200:
                try:
                    return resp.json()
                except:
                    return {"status": "error", "message": "Invalid JSON", "raw": resp.text[:200]}
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def bittv(self, type_param="EV"):
        return self._request("/streaming/bittv", {"type": type_param})

    def vidio(self, q, id_param=None):
        params = {"q": q}
        if id_param: params["id"] = id_param
        return self._request("/streaming/vidio", params)

    def nexoratv(self, channel=""):
        return self._request("/streaming/nexoratv", {"channel": channel})

    def netshort(self, book_id, episode):
        return self._request("/streaming/netshort", {"bookId": book_id, "episode": episode})

    def ssweb(self, url):
        return self._request("/tools/ssweb", {"url": url})

    def translate(self, text, to="en", from_lang="auto"):
        return self._request("/tools/translate", {"text": text, "to": to, "from": from_lang})

    def tiktok(self, username):
        return self._request("/social/tiktok", {"username": username})

    def moviebox_horror(self, page=1, per_page=20):
        return self._request("/film/moviebox-horror", {"page": page, "perPage": per_page})

    def moviebox_global(self, page=1, per_page=20):
        return self._request("/film/moviebox-global", {"page": page, "perPage": per_page})

    def gempa(self, type_param="auto"):
        return self._request("/info/gempa", {"type": type_param})

# ============================================
# CLASS: ALIGHT PREMIUM GENERATOR (REAL)
# ============================================
class AlightPremium:
    def __init__(self):
        self.base_url = CONFIG["ALIGHT_BASE"]
        self.secret = CONFIG["ALIGHT_SECRET"]
        self.timeout = CONFIG["TIMEOUT"]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Linux; Android 13)", "Accept": "application/json"})

    def _sha256(self, text):
        return hashlib.sha256(text.encode()).hexdigest()

    def _get_session(self):
        try:
            resp = self.session.get(f"{self.base_url}/api/session", timeout=self.timeout)
            if resp.status_code != 200:
                return {"status": False, "error": f"HTTP {resp.status_code}"}
            data = resp.json()
            if not data.get("status"):
                return {"status": False, "error": "Invalid session"}
            return {
                "status": True,
                "sessionId": data.get("sessionId"),
                "token": data.get("token"),
                "nonce": data.get("nonce"),
                "timestamp": data.get("timestamp"),
                "difficulty": data.get("difficulty", "0"),
                "cookie": resp.headers.get("set-cookie", "").split(";")[0]
            }
        except Exception as e:
            return {"status": False, "error": str(e)}

    def _solve_pow(self, session, email, action, human_proof):
        base = f"{session['sessionId']}:{session['nonce']}:{session['timestamp']}:{email.lower()}:{action}:{human_proof}:"
        difficulty = session.get("difficulty", "0")
        for i in range(500000):
            if self._sha256(base + str(i)).startswith(difficulty):
                return str(i)
        return str(int(time.time() * 1000))

    def _call_api(self, body):
        try:
            session = self._get_session()
            if not session.get("status"):
                return {"status": False, "error": session.get("error")}
            delay = 2300 - (int(time.time() * 1000) - int(session.get("timestamp", 0)))
            if delay > 0:
                time.sleep(delay / 1000)
            human_proof = self._sha256(f"human:{session['sessionId']}:{session['nonce']}:{session['timestamp']}:{body.get('email', '').lower()}:5:{self.secret}")
            pow_solution = self._solve_pow(session, body.get("email", ""), body.get("action", ""), human_proof)
            headers = {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-Amprem-Token": session["token"],
                "X-Amprem-Nonce": session["nonce"],
                "X-Amprem-Pow": pow_solution,
                "X-Amprem-Human-Proof": human_proof,
                "Cookie": session["cookie"],
            }
            resp = self.session.post(f"{self.base_url}/api/alight-motion", json=body, headers=headers, timeout=self.timeout)
            try:
                return {"status": True, "data": resp.json()}
            except:
                return {"status": False, "error": "Invalid response"}
        except Exception as e:
            return {"status": False, "error": str(e)}

    def send_magic_link(self, email):
        if not email or "@" not in email:
            return {"status": False, "error": "Email tidak valid"}
        result = self._call_api({"action": "send", "email": email})
        if not result.get("status"):
            return {"status": False, "error": result.get("error")}
        data = result.get("data", {})
        if not data.get("status"):
            return {"status": False, "error": data.get("msg", "Failed")}
        return {"status": True, "email": email, "message": data.get("msg", "Link sent to email")}

    def activate_premium(self, email, link):
        if not email or "@" not in email:
            return {"status": False, "error": "Email tidak valid"}
        if not link:
            return {"status": False, "error": "Link required"}
        result = self._call_api({"action": "verify", "email": email, "link": link.strip()})
        if not result.get("status"):
            return {"status": False, "error": result.get("error")}
        data = result.get("data", {})
        if not data.get("status"):
            return {"status": False, "error": data.get("msg", "Failed")}
        premium_data = data.get("data", {}).get("premium", {}).get("result", {})
        return {
            "status": True,
            "email": email,
            "message": data.get("msg", "Premium activated!"),
            "premium": {
                "active": premium_data.get("accountLinkStatus", False),
                "expiry": premium_data.get("expiryTimeMillis", 0),
                "auto_renew": premium_data.get("autoRenewing", False)
            }
        }

# ============================================
# INISIALISASI API
# ============================================
dailymotion = DailymotionAPI()
keyrafa = KeyrafaAPI()
alight = AlightPremium()

# ============================================
# FUNGSI DATABASE (IN-MEMORY FOR VERCEL)
# ============================================
DEFAULT_ADMIN_PASSWORD = "mazvalky098889"

def ensure_admin(data):
    has_admin = any(u.get('username') == 'mazvall' for u in data.get('users', []))
    if not has_admin:
        data.setdefault('users', []).insert(0, {
            "id": "1",
            "username": "mazvall",
            "password_hash": generate_password_hash(DEFAULT_ADMIN_PASSWORD),
            "role": "admin",
            "device_id": None,
            "created_at": datetime.now().isoformat()
        })
    for u in data.get('users', []):
        if u.get('username') == 'mazvall':
            if not u.get('password_hash'):
                if u.get('password'):
                    u['password_hash'] = generate_password_hash(u['password'])
                    del u['password']
                else:
                    u['password_hash'] = generate_password_hash(DEFAULT_ADMIN_PASSWORD)
            if u.get('password') and u.get('password_hash'):
                del u['password']
    return data

_memory_db = None

def load_db():
    global _memory_db
    if _memory_db is not None:
        return _memory_db
    _memory_db = {"users": [], "items": [], "api_keys": [], "user_accounts": []}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                _memory_db = json.load(f)
        except:
            pass
    _memory_db = ensure_admin(_memory_db)
    return _memory_db

def save_db(data):
    global _memory_db
    _memory_db = data
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass

def get_device_id():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua = request.headers.get('User-Agent', '')
    return hashlib.md5(f"{ip}|{ua}".encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        data = load_db()
        user = next((u for u in data['users'] if u['username'] == session['user']), None)
        if not user or user.get('role') != 'admin':
            return "Akses ditolak! Hanya admin.", 403
        return f(*args, **kwargs)
    return decorated

def generate_api_key():
    chars = string.ascii_uppercase + string.digits
    segment = ''.join(random.choices(chars, k=10))
    return f"MZval -X{segment}"

def get_device_fingerprint(req):
    ip = req.headers.get('X-Forwarded-For', req.remote_addr)
    ua = req.headers.get('User-Agent', '')
    return f"{ip}|{ua}"

def validate_api_key(api_key, req):
    data = load_db()
    key_obj = next((k for k in data.get('api_keys', []) if k['key'] == api_key), None)
    if not key_obj:
        return False, "API key tidak ditemukan"
    if not key_obj.get('active', False):
        return False, "API key tidak aktif"
    exp = datetime.fromisoformat(key_obj['expires_at'])
    if datetime.now() > exp:
        return False, "API key sudah expired"
    fingerprint = get_device_fingerprint(req)
    if key_obj.get('device_fingerprint') and key_obj['device_fingerprint'] != fingerprint:
        return False, "API key tidak bisa digunakan di device lain"
    if not key_obj.get('device_fingerprint'):
        key_obj['device_fingerprint'] = fingerprint
        save_db(data)
    return True, "OK"

# ============================================
# TEMPLATE HTML
# ============================================
COPYRIGHT = "&copy; Created Mazvall official Hak cipta"

BASE_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter',sans-serif;background:#f0f0f0;min-height:100vh;}
.fade-in{opacity:0;transform:translateY(30px);transition:opacity .6s ease,transform .6s ease;}
.fade-in.visible{opacity:1;transform:translateY(0);}
.scale-in{opacity:0;transform:scale(.9);transition:opacity .5s ease,transform .5s ease;}
.scale-in.visible{opacity:1;transform:scale(1);}
.credit{text-align:center;padding:20px;font-size:12px;color:#888;border-top:3px solid #000;background:#fff;margin-top:30px;border-radius:0 0 16px 16px;}
.credit span{font-weight:700;color:#000;}
.navbar{display:flex;justify-content:space-between;align-items:center;background:#FFD60A;border:4px solid #000;border-radius:16px;padding:16px 24px;box-shadow:6px 6px 0 #000;margin:20px;flex-wrap:wrap;}
.navbar .logo{font-weight:800;font-size:20px;}
.navbar .nav-links{display:flex;gap:8px;flex-wrap:wrap;}
.navbar .nav-links a{text-decoration:none;color:#000;font-weight:600;padding:8px 14px;border:3px solid #000;border-radius:10px;background:#fff;transition:all .15s;font-size:13px;}
.navbar .nav-links a:hover{box-shadow:4px 4px 0 #000;transform:translate(-2px,-2px);}
.navbar .nav-links a.active{background:#4ECDC4;}
.container{max-width:1100px;margin:0 auto;padding:0 20px;}
.card{background:#fff;border:4px solid #000;border-radius:16px;padding:30px;box-shadow:6px 6px 0 #000;margin-bottom:24px;overflow:hidden;}
.card h2{font-size:20px;margin-bottom:16px;}
.btn{font-family:'Inter',sans-serif;font-weight:700;font-size:13px;padding:10px 18px;border:3px solid #000;border-radius:10px;cursor:pointer;transition:all .15s;text-decoration:none;display:inline-block;}
.btn:hover{box-shadow:4px 4px 0 #000;transform:translate(-2px,-2px);}
.btn-primary{background:#4ECDC4;color:#000;}
.btn-danger{background:#FF6B6B;color:#000;}
.btn-warning{background:#FFD60A;color:#000;}
.btn-secondary{background:#fff;color:#000;}
.btn-sm{padding:6px 12px;font-size:11px;}
input,select,textarea{font-family:'Inter',sans-serif;font-size:14px;padding:10px 14px;border:3px solid #000;border-radius:8px;background:#fff;outline:none;width:100%;margin-bottom:12px;}
input:focus,select:focus,textarea:focus{box-shadow:3px 3px 0 #000;}
.table-wrapper{overflow-x:auto;}
table{width:100%;border-collapse:collapse;min-width:500px;}
th,td{padding:12px 14px;text-align:left;border:3px solid #000;}
th{background:#FFD60A;font-weight:700;}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:24px;}
.stat-card{background:#fff;border:4px solid #000;border-radius:14px;padding:20px;box-shadow:5px 5px 0 #000;text-align:center;}
.stat-card .number{font-size:28px;font-weight:800;}
.stat-card .label{font-size:12px;color:#666;margin-top:4px;}
.badge{display:inline-block;padding:4px 10px;border-radius:50px;font-size:11px;font-weight:700;border:2px solid #000;}
.badge-green{background:#CAFFBF;}
.badge-red{background:#FFB4B4;}
.badge-blue{background:#B8F3FF;}
.badge-purple{background:#C8B6FF;}
.badge-gold{background:#FFD700;color:#000;}
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.5);z-index:100;justify-content:center;align-items:center;padding:20px;}
.modal-overlay.active{display:flex;}
.modal{background:#fff;border:4px solid #000;border-radius:16px;padding:30px;box-shadow:8px 8px 0 #000;max-width:500px;width:100%;max-height:90vh;overflow-y:auto;}
.page-title{margin-top:20px;margin-bottom:20px;}
.page-title h1{font-size:26px;margin-bottom:6px;}
.page-title p{color:#666;font-size:14px;}
.marquee{background:#FFD60A;border:4px solid #000;border-radius:10px;padding:12px 20px;margin-bottom:20px;font-weight:700;color:#000;overflow:hidden;white-space:nowrap;}
.video-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-top:12px;}
.video-card{background:#f5f5f5;border:3px solid #000;border-radius:10px;padding:12px;text-align:center;}
.video-card img{width:100%;border-radius:6px;border:3px solid #000;max-height:150px;object-fit:cover;}
.video-card h3{font-size:13px;margin:8px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.video-card .link{font-size:11px;color:#666;word-break:break-all;}
pre{background:#1a1a2e;color:#4ECDC4;padding:16px;border-radius:10px;border:3px solid #000;font-size:12px;min-height:60px;white-space:pre-wrap;word-wrap:break-word;display:none;}
.api-endpoint{background:#f5f5f5;border:3px solid #000;border-radius:10px;padding:16px;margin-bottom:12px;word-wrap:break-word;}
.api-method{display:inline-block;padding:4px 10px;border-radius:6px;font-weight:700;font-size:12px;margin-right:8px;white-space:nowrap;}
.method-get{background:#4ECDC4;}
.method-post{background:#FFD60A;}
.method-put{background:#C8B6FF;}
.method-delete{background:#FF6B6B;}
@media(max-width:600px){
.navbar{flex-direction:column;gap:10px;}
.navbar .logo{font-size:16px;}
.navbar .nav-links a{padding:6px 10px;font-size:12px;}
.stats{grid-template-columns:1fr 1fr;}
.card{padding:20px;}
table{min-width:400px;}
.video-grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr));}
}
</style>
"""

SCROLL_JS = """
<script>
document.addEventListener('DOMContentLoaded',function(){
var o=new IntersectionObserver(function(e){e.forEach(function(x){if(x.isIntersecting)x.target.classList.add('visible');});},{threshold:.1});
document.querySelectorAll('.fade-in,.scale-in').forEach(function(el){o.observe(el);});
});
</script>
"""

LOGIN_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Login - Mazvall official</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter',sans-serif;background:#f0f0f0;min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px;}
.login-container{width:100%;max-width:420px;}
.login-box{background:#fff;border:4px solid #000;border-radius:20px;padding:40px;box-shadow:8px 8px 0 #000;opacity:0;transform:translateY(30px);animation:slideUp .6s ease forwards;}
@keyframes slideUp{to{opacity:1;transform:translateY(0);}}
.login-box h1{font-size:24px;text-align:center;margin-bottom:4px;}
.login-box .subtitle{text-align:center;color:#666;margin-bottom:30px;font-size:13px;}
.login-box .icon{width:80px;height:80px;background:#FFD60A;border:4px solid #000;border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:36px;margin:0 auto 20px;box-shadow:4px 4px 0 #000;}
.form-group{margin-bottom:16px;}
.form-group label{display:block;font-weight:700;margin-bottom:6px;font-size:13px;}
.form-group input{width:100%;padding:12px 16px;border:3px solid #000;border-radius:10px;font-size:14px;font-family:'Inter',sans-serif;outline:none;}
.login-btn{width:100%;padding:14px;background:#4ECDC4;color:#000;border:3px solid #000;border-radius:12px;font-size:16px;font-weight:700;font-family:'Inter',sans-serif;cursor:pointer;box-shadow:4px 4px 0 #000;margin-top:8px;}
.login-btn:hover{box-shadow:6px 6px 0 #000;transform:translate(-2px,-2px);}
.error-msg{background:#FF6B6B;border:3px solid #000;border-radius:10px;padding:12px;text-align:center;font-weight:600;font-size:13px;margin-bottom:16px;}
.credit{text-align:center;margin-top:24px;font-size:12px;color:#888;}
.credit span{font-weight:700;color:#000;}
</style></head><body>
<div class="login-container"><div class="login-box">
<div class="icon">&#128274;</div>
<h1>Mazvall official</h1>
<p class="subtitle">Masuk ke dashboard admin</p>
{% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
<form method="POST" action="/login">
<div class="form-group"><label>Username</label><input type="text" name="username" placeholder="Masukkan username" required></div>
<div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Masukkan password" required></div>
<button type="submit" class="login-btn">Masuk &#8594;</button>
</form>
<p class="credit">&copy; Created Mazvall official Hak cipta</p>
</div></div></body></html>"""

DASHBOARD_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Dashboard - Mazvall official</title>{style}</head><body>
<nav class="navbar"><div class="logo">&#9889; Mazvall official</div><div class="nav-links">
<a href="/" class="active">Dashboard</a>
<a href="/items">Items</a>
<a href="/api-keys">API Keys</a>
<a href="/api/docs">Docs</a>
<a href="/users">Users</a>
<a href="/tools">Tools</a>
<a href="/logout" style="background:#FF6B6B;">Logout</a>
</div></nav>
<div class="container">
<div class="page-title fade-in"><h1>Dashboard</h1><p>Selamat datang, {{ user }}!</p></div>
<div class="stats">
<div class="stat-card fade-in"><div class="number">{{ total_items }}</div><div class="label">Total Items</div></div>
<div class="stat-card fade-in"><div class="number">{{ total_keys }}</div><div class="label">API Keys</div></div>
<div class="stat-card fade-in"><div class="number">{{ active_keys }}</div><div class="label">Active Keys</div></div>
<div class="stat-card fade-in"><div class="number">{{ total_users }}</div><div class="label">Total Users</div></div>
</div>
<div class="card fade-in">
<h2>Quick Info</h2>
<p style="color:#666;font-size:14px;margin-bottom:12px;">Selamat datang di panel admin <strong>Mazvall official</strong>.</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;">
<a href="/api-keys" class="btn btn-primary">Kelola API Keys</a>
<a href="/items" class="btn btn-warning">Kelola Items</a>
<a href="/users" class="btn btn-secondary">Kelola Users</a>
<a href="/tools" class="btn btn-secondary">Tools</a>
</div>
</div>
</div>
<p class="credit">&copy; Created Mazvall official Hak cipta</p>
{script}</body></html>"""

ITEMS_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Items - Mazvall official</title>{style}</head><body>
<nav class="navbar"><div class="logo">&#9889; Mazvall official</div><div class="nav-links">
<a href="/">Dashboard</a>
<a href="/items" class="active">Items</a>
<a href="/api-keys">API Keys</a>
<a href="/api/docs">Docs</a>
<a href="/users">Users</a>
<a href="/tools">Tools</a>
<a href="/logout" style="background:#FF6B6B;">Logout</a>
</div></nav>
<div class="container">
<div class="page-title fade-in" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
<div><h1>Items</h1><p>Kelola data items Anda</p></div>
<button class="btn btn-primary" onclick="openModal()">+ Tambah Item</button>
</div>
<div class="card fade-in">
<div class="table-wrapper">
<table>
<thead><tr><th>ID</th><th>Nama</th><th>Harga</th><th>Status</th><th>Aksi</th></tr></thead>
<tbody>
{% for item in items %}
<tr>
<td style="font-family:monospace;font-size:11px;">{{ item.id[:8] }}</td>
<td><strong>{{ item.name }}</strong></td>
<td>Rp {{ "{:,.0f}".format(item.price) }}</td>
<td><span class="badge {{ 'badge-green' if item.active else 'badge-red' }}">{{ 'Active' if item.active else 'Inactive' }}</span></td>
<td style="white-space:nowrap;">
<button class="btn btn-warning btn-sm" onclick="editItem('{{ item.id }}','{{ item.name }}',{{ item.price }},{{ 'true' if item.active else 'false' }})">Edit</button>
<button class="btn btn-danger btn-sm" onclick="deleteItem('{{ item.id }}')">Hapus</button>
</td>
</tr>
{% endfor %}
{% if not items %}<tr><td colspan="5" style="text-align:center;color:#999;padding:30px;">Belum ada data</td></tr>{% endif %}
</tbody></table>
</div>
</div>
</div>
<div class="modal-overlay" id="modal">
<div class="modal scale-in">
<h2 style="margin-bottom:16px;" id="modal-title">Tambah Item</h2>
<form onsubmit="submitForm(event)">
<input type="hidden" id="edit-id" value="">
<div class="form-group"><label>Nama Item</label><input type="text" id="item-name" required></div>
<div class="form-group"><label>Harga (Rp)</label><input type="number" id="item-price" required></div>
<div class="form-group"><label>Status</label><select id="item-active"><option value="true">Active</option><option value="false">Inactive</option></select></div>
<div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap;">
<button type="submit" class="btn btn-primary">Simpan</button>
<button type="button" class="btn btn-secondary" onclick="closeModal()">Batal</button>
</div>
</form>
</div>
</div>
<p class="credit">&copy; Created Mazvall official Hak cipta</p>
<script>
function openModal(){document.getElementById('edit-id').value='';document.getElementById('item-name').value='';document.getElementById('item-price').value='';document.getElementById('item-active').value='true';document.getElementById('modal-title').textContent='Tambah Item';document.getElementById('modal').classList.add('active');}
function closeModal(){document.getElementById('modal').classList.remove('active');}
function editItem(id,name,price,active){document.getElementById('edit-id').value=id;document.getElementById('item-name').value=name;document.getElementById('item-price').value=price;document.getElementById('item-active').value=active;document.getElementById('modal-title').textContent='Edit Item';document.getElementById('modal').classList.add('active');}
function submitForm(e){e.preventDefault();var id=document.getElementById('edit-id').value;var data={name:document.getElementById('item-name').value,price:parseFloat(document.getElementById('item-price').value),active:document.getElementById('item-active').value==='true'};var url=id?'/api/items/'+id:'/api/items';fetch(url,{method:id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).then(function(r){return r.json();}).then(function(){location.reload();});}
function deleteItem(id){if(confirm('Yakin hapus?')){fetch('/api/items/'+id,{method:'DELETE'}).then(function(r){return r.json();}).then(function(){location.reload();});}}
</script>
{script}</body></html>"""

API_KEYS_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>API Keys - Mazvall official</title>{style}</head><body>
<nav class="navbar"><div class="logo">&#9889; Mazvall official</div><div class="nav-links">
<a href="/">Dashboard</a>
<a href="/items">Items</a>
<a href="/api-keys" class="active">API Keys</a>
<a href="/api/docs">Docs</a>
<a href="/users">Users</a>
<a href="/tools">Tools</a>
<a href="/logout" style="background:#FF6B6B;">Logout</a>
</div></nav>
<div class="container">
<div class="page-title fade-in" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
<div><h1>API Keys</h1><p>Kelola API keys untuk akses REST API</p></div>
<button class="btn btn-primary" onclick="openModal()">+ Generate Key</button>
</div>
<div class="card fade-in">
<div class="table-wrapper">
<table>
<thead><tr><th>API Key</th><th>User</th><th>Device</th><th>Expires</th><th>Status</th><th>Aksi</th></tr></thead>
<tbody>
{% for k in keys %}
<tr>
<td style="font-family:monospace;font-size:11px;max-width:180px;">{{ k.key }}</td>
<td><strong>{{ k.user }}</strong></td>
<td style="font-size:11px;max-width:120px;overflow:hidden;text-overflow:ellipsis;">{{ k.device_fingerprint[:20] if k.device_fingerprint else 'Belum dipakai' }}</td>
<td style="white-space:nowrap;font-size:12px;">{{ k.expires_at[:16] }}</td>
<td>
{% if k.active %}
  {% if k.expired %}
    <span class="badge badge-red">Expired</span>
  {% else %}
    <span class="badge badge-green">Active</span>
  {% endif %}
{% else %}
  <span class="badge badge-red">Disabled</span>
{% endif %}
</td>
<td style="white-space:nowrap;">
<button class="btn btn-warning btn-sm" onclick="toggleKey('{{ k.key }}')">{{ 'Disable' if k.active else 'Enable' }}</button>
<button class="btn btn-danger btn-sm" onclick="deleteKey('{{ k.key }}')">Hapus</button>
</td>
</tr>
{% endfor %}
{% if not keys %}<tr><td colspan="6" style="text-align:center;color:#999;padding:30px;">Belum ada API key</td></tr>{% endif %}
</tbody></table>
</div>
</div>
</div>
<div class="modal-overlay" id="modal">
<div class="modal scale-in">
<h2 style="margin-bottom:16px;">Generate API Key</h2>
<form onsubmit="generateKey(event)">
<div class="form-group"><label>User / Nama</label><input type="text" id="key-user" required placeholder="Nama pemilik key"></div>
<div class="form-group"><label>Durasi Expiry</label>
<select id="key-duration">
<option value="1h">1 Jam</option>
<option value="6h">6 Jam</option>
<option value="12h">12 Jam</option>
<option value="1d" selected>1 Hari</option>
<option value="7d">7 Hari</option>
<option value="30d">30 Hari</option>
<option value="3m">3 Bulan</option>
<option value="6m">6 Bulan</option>
<option value="12m">12 Bulan</option>
</select></div>
<div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap;">
<button type="submit" class="btn btn-primary">Generate</button>
<button type="button" class="btn btn-secondary" onclick="closeModal()">Batal</button>
</div>
</form>
</div>
</div>
<p class="credit">&copy; Created Mazvall official Hak cipta</p>
<script>
function openModal(){document.getElementById('modal').classList.add('active');}
function closeModal(){document.getElementById('modal').classList.remove('active');}
function generateKey(e){e.preventDefault();var user=document.getElementById('key-user').value;var duration=document.getElementById('key-duration').value;fetch('/api/keys/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:user,duration:duration})}).then(function(r){return r.json();}).then(function(d){if(d.status==='success')location.reload();else alert(d.message);});}
function toggleKey(key){fetch('/api/keys/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:key})}).then(function(r){return r.json();}).then(function(){location.reload();});}
function deleteKey(key){if(confirm('Yakin hapus API key ini?')){fetch('/api/keys/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:key})}).then(function(r){return r.json();}).then(function(){location.reload();});}}
</script>
{script}</body></html>"""

API_DOCS_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>API Docs - Mazvall official</title>{style}</head><body>
<nav class="navbar"><div class="logo">&#9889; Mazvall official</div><div class="nav-links">
<a href="/">Dashboard</a>
<a href="/items">Items</a>
<a href="/api-keys">API Keys</a>
<a href="/api/docs" class="active">Docs</a>
<a href="/users">Users</a>
<a href="/tools">Tools</a>
<a href="/logout" style="background:#FF6B6B;">Logout</a>
</div></nav>
<div class="container">
<div class="page-title fade-in"><h1>API Documentation</h1><p>Cara menggunakan REST API dengan API key</p></div>
<div class="card fade-in"><h2>Autentikasi</h2><p style="color:#666;font-size:14px;margin-bottom:12px;">Semua request harus menyertakan API key di header:</p><pre>X-API-Key: MZval -Xxxxxxxxxxx</pre><p style="color:#666;font-size:13px;margin-top:10px;">API key terkunci ke 1 device.</p></div>
<div class="card fade-in"><h2>Base URL</h2><pre id="base-url"></pre></div>
<div class="card fade-in"><h2>Endpoints</h2>
<div class="api-endpoint"><span class="api-method method-get">GET</span><strong>/api/items</strong><p style="margin-top:8px;color:#666;">Ambil semua items</p></div>
<div class="api-endpoint"><span class="api-method method-get">GET</span><strong>/api/items/{id}</strong><p style="margin-top:8px;color:#666;">Ambil satu item</p></div>
<div class="api-endpoint"><span class="api-method method-post">POST</span><strong>/api/items</strong><p style="margin-top:8px;color:#666;">Tambah item. Body: {"name":"...","price":0,"active":true}</p></div>
<div class="api-endpoint"><span class="api-method method-put">PUT</span><strong>/api/items/{id}</strong><p style="margin-top:8px;color:#666;">Update item</p></div>
<div class="api-endpoint"><span class="api-method method-delete">DELETE</span><strong>/api/items/{id}</strong><p style="margin-top:8px;color:#666;">Hapus item</p></div>
</div>
<div class="card fade-in">
<h2>Test API</h2>
<p style="margin-bottom:12px;color:#666;font-size:14px;">Masukkan API key untuk test</p>
<div class="form-group"><label>API Key</label><input type="text" id="test-key" placeholder="MZval -X..."></div>
<div style="display:flex;gap:10px;flex-wrap:wrap;">
<button class="btn btn-primary" onclick="testApi('GET','/api/items')">GET /items</button>
<button class="btn btn-warning" onclick="testApi('POST','/api/items')">POST /items</button>
<button class="btn btn-danger" onclick="testApi('DELETE','/api/items/test')">DELETE /items/test</button>
</div>
<pre id="api-result" style="background:#1a1a2e;color:#4ECDC4;padding:16px;border-radius:10px;border:3px solid #000;margin-top:16px;font-size:12px;min-height:60px;display:none;white-space:pre-wrap;word-wrap:break-word;"></pre>
</div>
</div>
<p class="credit">&copy; Created Mazvall official Hak cipta</p>
<script>
document.getElementById('base-url').textContent=window.location.origin+'/api';
function testApi(method,url){
var result=document.getElementById('api-result');
var apiKey=document.getElementById('test-key').value;
if(!apiKey){result.style.display='block';result.textContent='Masukkan API key terlebih dahulu!';return;}
result.style.display='block';result.textContent='Loading...';
var opts={method:method,headers:{'Content-Type':'application/json','X-API-Key':apiKey}};
if(method==='POST')opts.body=JSON.stringify({name:'Test Item',price:25000,active:true});
fetch(url,opts).then(function(r){return r.json();}).then(function(d){result.textContent=JSON.stringify(d,null,2);}).catch(function(e){result.textContent='Error: '+e.message;});
}
</script>
{script}</body></html>"""

USERS_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Users - Mazvall official</title>{style}</head><body>
<nav class="navbar"><div class="logo">&#9889; Mazvall official</div><div class="nav-links">
<a href="/">Dashboard</a>
<a href="/items">Items</a>
<a href="/api-keys">API Keys</a>
<a href="/api/docs">Docs</a>
<a href="/users" class="active">Users</a>
<a href="/tools">Tools</a>
<a href="/logout" style="background:#FF6B6B;">Logout</a>
</div></nav>
<div class="container">
<div class="page-title fade-in" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
<div><h1>User Management</h1><p>Kelola user dengan role: Harian, Mingguan, Bulanan, Permanen</p></div>
<button class="btn btn-primary" onclick="openUserModal()">+ Create User</button>
</div>
<div class="card fade-in">
<div class="table-wrapper">
<table>
<thead><tr><th>Username</th><th>Role</th><th>Expired At</th><th>Device</th><th>Status</th><th>Aksi</th></tr></thead>
<tbody>
{% for u in users %}
<tr>
<td><strong>{{ u.username }}</strong></td>
<td><span class="badge {{ 'badge-blue' if u.role == 'harian' else 'badge-green' if u.role == 'mingguan' else 'badge-purple' if u.role == 'bulanan' else 'badge-gold' }}">{{ u.role.upper() }}</span></td>
<td style="font-size:12px;">{{ u.expired_at[:16] if u.expired_at else 'Permanen' }}</td>
<td style="font-size:10px;max-width:100px;overflow:hidden;text-overflow:ellipsis;">{{ u.device_id[:16] if u.device_id else 'Belum login' }}</td>
<td>
{% if u.expired_at %}
  {% if u.expired %}
    <span class="badge badge-red">Expired</span>
  {% else %}
    <span class="badge badge-green">Active</span>
  {% endif %}
{% else %}
  <span class="badge badge-gold">Permanen</span>
{% endif %}
</td>
<td style="white-space:nowrap;">
<button class="btn btn-danger btn-sm" onclick="deleteUser('{{ u.id }}')">Hapus</button>
</td>
</tr>
{% endfor %}
{% if not users %}<tr><td colspan="6" style="text-align:center;color:#999;padding:30px;">Belum ada user</td></tr>{% endif %}
</tbody></table>
</div>
</div>
</div>
<div class="modal-overlay" id="user-modal">
<div class="modal scale-in">
<h2 style="margin-bottom:16px;">Create User Account</h2>
<form onsubmit="createUser(event)">
<div class="form-group"><label>Username</label><input type="text" id="user-username" required placeholder="Nama user"></div>
<div class="form-group"><label>Password</label><input type="text" id="user-password" required placeholder="Password"></div>
<div class="form-group"><label>Role</label>
<select id="user-role">
<option value="harian">Harian (1 hari)</option>
<option value="mingguan">Mingguan (7 hari)</option>
<option value="bulanan">Bulanan (30 hari)</option>
<option value="permanen">Permanen</option>
</select></div>
<div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap;">
<button type="submit" class="btn btn-primary">Create</button>
<button type="button" class="btn btn-secondary" onclick="closeUserModal()">Batal</button>
</div>
</form>
</div>
</div>
<p class="credit">&copy; Created Mazvall official Hak cipta</p>
<script>
function openUserModal(){document.getElementById('user-modal').classList.add('active');}
function closeUserModal(){document.getElementById('user-modal').classList.remove('active');}
function createUser(e){e.preventDefault();var username=document.getElementById('user-username').value;var password=document.getElementById('user-password').value;var role=document.getElementById('user-role').value;fetch('/api/users/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:username,password:password,role:role})}).then(function(r){return r.json();}).then(function(d){if(d.status==='success')location.reload();else alert(d.message);});}
function deleteUser(id){if(confirm('Yakin hapus user ini?')){fetch('/api/users/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})}).then(function(r){return r.json();}).then(function(){location.reload();});}}
</script>
{script}</body></html>"""

TOOLS_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Tools - Mazvall official</title>{style}</head><body>
<nav class="navbar"><div class="logo">&#9889; Mazvall official</div><div class="nav-links">
<a href="/">Dashboard</a>
<a href="/items">Items</a>
<a href="/api-keys">API Keys</a>
<a href="/api/docs">Docs</a>
<a href="/users">Users</a>
<a href="/tools" class="active">Tools</a>
<a href="/logout" style="background:#FF6B6B;">Logout</a>
</div></nav>
<div class="container">
<div class="marquee"><marquee behavior="scroll" direction="left" scrollamount="5">&#9889; Welcome to Tools Center - All access requires API Key - Admin Only Access - Alight Motion Premium Real & Work - Dailymotion - Bittv - MovieBox - TikTok - Translator - Screenshot - Info Gempa</marquee></div>
<div class="page-title fade-in"><h1>Tools Center</h1><p>Admin Only - Semua tools wajib API Key</p></div>
<div class="card fade-in">
<h2>API Key</h2>
<p style="color:#666;font-size:14px;margin-bottom:12px;">Masukkan API Key untuk mengakses tools:</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;">
<input type="text" id="tool-api-key" placeholder="Masukkan API Key" style="flex:1;min-width:200px;">
<button class="btn btn-primary" onclick="setApiKey()">Set API Key</button>
<button class="btn btn-warning" onclick="generateApiKey()">+ Generate Key</button>
</div>
<div id="key-status" style="margin-top:10px;color:#666;font-size:13px;"></div>
</div>
<div class="card fade-in"><h2>Dailymotion</h2>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
<input type="text" id="dm-search" placeholder="Cari video..." style="flex:1;min-width:150px;">
<select id="dm-sort"><option value="trending">Trending</option><option value="recent">Terbaru</option><option value="relevance">Relevansi</option></select>
<select id="dm-limit"><option value="5">5</option><option value="10" selected>10</option><option value="20">20</option></select>
<button class="btn btn-primary" onclick="searchDailymotion()">Cari</button>
</div>
<div id="dm-result" style="margin-top:10px;"></div>
</div>
<div class="card fade-in"><h2>Bittv Events</h2>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
<select id="bittv-type"><option value="EV">Events</option><option value="SP">Sports TV</option><option value="ID">Indonesia</option><option value="GB">UK</option><option value="US">US</option></select>
<button class="btn btn-primary" onclick="getBittv()">Lihat Events</button>
</div>
<div id="bittv-result" style="margin-top:10px;"></div>
</div>
<div class="card fade-in"><h2>MovieBox</h2>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
<select id="moviebox-type"><option value="global">Trending Global</option><option value="horror">Horror Indonesia</option></select>
<button class="btn btn-primary" onclick="getMoviebox()">Lihat Film</button>
</div>
<div id="moviebox-result" style="margin-top:10px;"></div>
</div>
<div class="card fade-in"><h2>Alight Motion Premium</h2>
<p style="color:#666;font-size:14px;margin-bottom:12px;">Kirim email & verifikasi OOB link - Real Work!</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
<input type="email" id="alight-email" placeholder="Email tujuan" style="flex:1;min-width:200px;">
<button class="btn btn-primary" onclick="sendAlightLink()">Send Magic Link</button>
</div>
<div id="alight-status" style="color:#666;font-size:13px;margin-bottom:10px;"></div>
<input type="text" id="alight-link" placeholder="Masukkan OOB link dari email" style="flex:1;min-width:200px;display:none;">
<button class="btn btn-warning" id="alight-activate-btn" onclick="activateAlight()" style="display:none;">Activate Premium</button>
<div id="alight-result" style="margin-top:10px;"></div>
</div>
<div class="card fade-in"><h2>Tools Lainnya</h2>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;">
<button class="btn btn-secondary" onclick="getGempa()">Info Gempa</button>
<button class="btn btn-secondary" onclick="getTikTok()">TikTok Profile</button>
<button class="btn btn-secondary" onclick="showTranslate()">Translator</button>
<button class="btn btn-secondary" onclick="showScreenshot()">Screenshot</button>
</div>
<div id="tool-result" style="margin-top:10px;"></div>
</div>
</div>
<p class="credit">&copy; Created Mazvall official Hak cipta</p>
{script}
<script>
var apiKey = localStorage.getItem('toolApiKey') || '';
function setApiKey(){var key=document.getElementById('tool-api-key').value.trim();if(key){apiKey=key;localStorage.setItem('toolApiKey',key);document.getElementById('key-status').textContent='API Key set: '+key.substring(0,8)+'...';}}
function generateApiKey(){fetch('/api/external/keys/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'Tool User'})}).then(function(r){return r.json();}).then(function(d){if(d.status==='success'&&d.api_key){document.getElementById('tool-api-key').value=d.api_key;setApiKey();document.getElementById('key-status').innerHTML='<span style="color:#4ECDC4;">Key generated: <strong>'+d.api_key+'</strong></span>';}});}
function getHeaders(){return{'X-API-Key':apiKey,'Content-Type':'application/json'};}
function showLoading(containerId){document.getElementById(containerId).innerHTML='<div style="text-align:center;padding:20px;"><strong>Loading...</strong></div>';}
function renderVideos(data,containerId){var container=document.getElementById(containerId);var items=data.data||data.items||data.videos||[];if(!items||items.length===0){container.innerHTML='<p style="color:#666;">Tidak ada video ditemukan.</p>';return;}var html='<div class="video-grid">';for(var i=0;i<Math.min(items.length,20);i++){var item=items[i];var title=item.title||'No Title';var thumb=item.thumbnail||item.poster||item.image||'';var videoId=item.id||item.video_id||'';var views=item.views||item.view_count||0;if(typeof views==='number')views=views.toLocaleString();html+='<div class="video-card fade-in">';if(thumb)html+='<img src="'+thumb+'" alt="'+title+'" onerror="this.style.display=\'none\'">';html+='<h3 title="'+title+'">'+title.substring(0,40)+'</h3>';html+='<div class="link">ID: '+videoId+'</div>';if(views)html+='<div class="link">'+views+' views</div>';html+='</div>';}html+='</div>';container.innerHTML=html;var observer=new IntersectionObserver(function(e){e.forEach(function(x){if(x.isIntersecting)x.target.classList.add('visible');});},{threshold:0.1});document.querySelectorAll('.fade-in').forEach(function(el){observer.observe(el);});}
function renderEvents(data,containerId){var container=document.getElementById(containerId);var info=data.result&&data.result.info?data.result.info:[];if(!info||info.length===0){container.innerHTML='<p style="color:#666;">Tidak ada event ditemukan.</p>';return;}var html='<div class="video-grid">';for(var i=0;i<Math.min(info.length,20);i++){var ev=info[i];html+='<div class="video-card fade-in">';if(ev.image)html+='<img src="'+ev.image+'" alt="'+ev.name+'" onerror="this.style.display=\'none\'">';html+='<h3 title="'+ev.name+'">'+ev.name.substring(0,40)+'</h3>';if(ev.tagline)html+='<div class="link">'+ev.tagline+'</div>';if(ev.hls)html+='<div class="link" style="font-size:10px;word-break:break-all;">'+ev.hls.substring(0,40)+'...</div>';html+='</div>';}html+='</div>';container.innerHTML=html;}
function renderMovies(data,containerId){var container=document.getElementById(containerId);var items=data.result&&data.result.items?data.result.items:[];if(!items||items.length===0){container.innerHTML='<p style="color:#666;">Tidak ada film ditemukan.</p>';return;}var html='<div class="video-grid">';for(var i=0;i<Math.min(items.length,20);i++){var m=items[i];html+='<div class="video-card fade-in">';if(m.poster)html+='<img src="'+m.poster+'" alt="'+m.title+'" onerror="this.style.display=\'none\'">';html+='<h3 title="'+m.title+'">'+m.title.substring(0,40)+'</h3>';html+='<div class="link">'+(m.genres?m.genres.join(', ').substring(0,30):'')+'</div>';if(m.year)html+='<div class="link">'+m.year+'</div>';if(m.imdbRating)html+='<div class="link">'+m.imdbRating+'</div>';html+='</div>';}html+='</div>';container.innerHTML=html;}
function searchDailymotion(){if(!apiKey){alert('Set API Key dulu!');return;}showLoading('dm-result');var search=document.getElementById('dm-search').value;var sort=document.getElementById('dm-sort').value;var limit=document.getElementById('dm-limit').value;var url='/api/dailymotion?limit='+limit+'&sort='+sort;if(search)url+='&search='+encodeURIComponent(search);fetch(url,{headers:getHeaders()}).then(function(r){return r.json();}).then(function(d){renderVideos(d,'dm-result');}).catch(function(e){document.getElementById('dm-result').innerHTML='<p style="color:#FF6B6B;">Error: '+e.message+'</p>';});}
function getBittv(){if(!apiKey){alert('Set API Key dulu!');return;}showLoading('bittv-result');var type=document.getElementById('bittv-type').value;fetch('/api/keyrafa/bittv?type='+type,{headers:getHeaders()}).then(function(r){return r.json();}).then(function(d){renderEvents(d,'bittv-result');}).catch(function(e){document.getElementById('bittv-result').innerHTML='<p style="color:#FF6B6B;">Error: '+e.message+'</p>';});}
function getMoviebox(){if(!apiKey){alert('Set API Key dulu!');return;}showLoading('moviebox-result');var type=document.getElementById('moviebox-type').value;var endpoint=type==='horror'?'/api/keyrafa/moviebox-horror':'/api/keyrafa/moviebox-global';fetch(endpoint+'?page=1&perPage=10',{headers:getHeaders()}).then(function(r){return r.json();}).then(function(d){renderMovies(d,'moviebox-result');}).catch(function(e){document.getElementById('moviebox-result').innerHTML='<p style="color:#FF6B6B;">Error: '+e.message+'</p>';});}
function getGempa(){if(!apiKey){alert('Set API Key dulu!');return;}showLoading('tool-result');fetch('/api/keyrafa/gempa?type=auto',{headers:getHeaders()}).then(function(r){return r.json();}).then(function(d){var container=document.getElementById('tool-result');var gempa=d.result&&d.result.gempa?d.result.gempa:[];if(!gempa||gempa.length===0){container.innerHTML='<p style="color:#666;">Tidak ada gempa terkini.</p>';return;}var html='<div class="video-grid">';for(var i=0;i<Math.min(gempa.length,10);i++){var g=gempa[i];html+='<div class="video-card fade-in">';html+='<h3>'+(g.wilayah||'Unknown')+'</h3>';if(g.magnitude)html+='<div class="link">Magnitude: '+g.magnitude+'</div>';if(g.kedalaman)html+='<div class="link">Kedalaman: '+g.kedalaman+' km</div>';if(g.waktu)html+='<div class="link">'+g.waktu+'</div>';html+='</div>';}html+='</div>';container.innerHTML=html;}).catch(function(e){document.getElementById('tool-result').innerHTML='<p style="color:#FF6B6B;">Error: '+e.message+'</p>';});}
function getTikTok(){if(!apiKey){alert('Set API Key dulu!');return;}var username=prompt('Masukkan username TikTok:');if(!username)return;showLoading('tool-result');fetch('/api/keyrafa/tiktok?username='+encodeURIComponent(username),{headers:getHeaders()}).then(function(r){return r.json();}).then(function(d){var container=document.getElementById('tool-result');var u=d.result||d;var html='<div class="card" style="margin-top:10px;">';if(u.avatar)html+='<img src="'+u.avatar+'" style="width:80px;height:80px;border-radius:50%;border:3px solid #000;object-fit:cover;">';html+='<h3 style="margin:8px 0;">'+(u.nickname||u.username||username)+'</h3>';if(u.signature)html+='<p style="color:#666;font-size:13px;">'+u.signature+'</p>';if(u.followerCount!==undefined)html+='<div style="margin-top:8px;"><strong>Followers:</strong> '+u.followerCount.toLocaleString()+'</div>';if(u.heartCount!==undefined)html+='<div><strong>Likes:</strong> '+u.heartCount.toLocaleString()+'</div>';if(u.videoCount!==undefined)html+='<div><strong>Videos:</strong> '+u.videoCount.toLocaleString()+'</div>';html+='</div>';container.innerHTML=html;}).catch(function(e){document.getElementById('tool-result').innerHTML='<p style="color:#FF6B6B;">Error: '+e.message+'</p>';});}
function showTranslate(){if(!apiKey){alert('Set API Key dulu!');return;}var text=prompt('Masukkan teks yang mau diterjemahkan:');if(!text)return;showLoading('tool-result');fetch('/api/keyrafa/translate?text='+encodeURIComponent(text)+'&to=en&from=auto',{headers:getHeaders()}).then(function(r){return r.json();}).then(function(d){var container=document.getElementById('tool-result');var r=d.result||d;var html='<div class="card" style="margin-top:10px;">';if(r.sourceText)html+='<div style="margin-bottom:8px;"><strong>Asli:</strong><br>'+r.sourceText+'</div>';if(r.translatedText)html+='<div><strong>Terjemahan:</strong><br>'+r.translatedText+'</div>';else if(r.text)html+='<div><strong>Terjemahan:</strong><br>'+r.text+'</div>';html+='</div>';container.innerHTML=html;}).catch(function(e){document.getElementById('tool-result').innerHTML='<p style="color:#FF6B6B;">Error: '+e.message+'</p>';});}
function showScreenshot(){if(!apiKey){alert('Set API Key dulu!');return;}var url=prompt('Masukkan URL website:');if(!url)return;showLoading('tool-result');fetch('/api/keyrafa/ssweb?url='+encodeURIComponent(url),{headers:getHeaders()}).then(function(r){return r.json();}).then(function(d){var container=document.getElementById('tool-result');if(d.result&&d.result.url){container.innerHTML='<div class="video-card" style="margin-top:10px;"><img src="'+d.result.url+'" alt="Screenshot" style="max-width:100%;border:3px solid #000;border-radius:8px;"></div>';}else{container.innerHTML='<p style="color:#FF6B6B;">Gagal mengambil screenshot</p>';}}).catch(function(e){document.getElementById('tool-result').innerHTML='<p style="color:#FF6B6B;">Error: '+e.message+'</p>';});}
var alightEmail='',alightLink='';
function sendAlightLink(){if(!apiKey){alert('Set API Key dulu!');return;}alightEmail=document.getElementById('alight-email').value.trim();if(!alightEmail||alightEmail.indexOf('@')===-1){alert('Masukkan email yang valid!');return;}document.getElementById('alight-status').textContent='Mengirim link ke '+alightEmail+'...';fetch('/api/alight/send',{method:'POST',headers:getHeaders(),body:JSON.stringify({email:alightEmail})}).then(function(r){return r.json();}).then(function(d){if(d.status){document.getElementById('alight-status').innerHTML='<span style="color:#4ECDC4;">Link sent to <strong>'+alightEmail+'</strong>! Cek inbox/spam.</span>';document.getElementById('alight-link').style.display='inline-block';document.getElementById('alight-activate-btn').style.display='inline-block';document.getElementById('alight-result').innerHTML='<p style="color:#4ECDC4;">'+d.message+'</p>';}else{document.getElementById('alight-status').innerHTML='<span style="color:#FF6B6B;">Gagal: '+(d.error||d.message||'Unknown error')+'</span>';}}).catch(function(e){document.getElementById('alight-status').innerHTML='<span style="color:#FF6B6B;">Error: '+e.message+'</span>';});}
function activateAlight(){if(!apiKey){alert('Set API Key dulu!');return;}alightLink=document.getElementById('alight-link').value.trim();if(!alightLink||alightLink.indexOf('http')===-1){alert('Masukkan OOB link yang valid!');return;}document.getElementById('alight-status').textContent='Mengaktivasi premium...';fetch('/api/alight/activate',{method:'POST',headers:getHeaders(),body:JSON.stringify({email:alightEmail,link:alightLink})}).then(function(r){return r.json();}).then(function(d){if(d.status){document.getElementById('alight-status').innerHTML='<span style="color:#4ECDC4;font-weight:700;">Premium activated!</span>';var html='<div style="background:#CAFFBF;padding:16px;border:3px solid #000;border-radius:10px;">';html+='<h3 style="color:#000;">Premium Activated!</h3>';html+='<p>Email: <strong>'+alightEmail+'</strong></p>';if(d.premium){html+='<p>Status: '+(d.premium.active?'Active':'Inactive')+'</p>';if(d.premium.expiry)html+='<p>Expiry: '+new Date(d.premium.expiry).toLocaleString()+'</p>';html+='<p>Auto Renew: '+(d.premium.auto_renew?'Yes':'No')+'</p>';}html+='</div>';document.getElementById('alight-result').innerHTML=html;}else{document.getElementById('alight-status').innerHTML='<span style="color:#FF6B6B;">Gagal aktivasi: '+(d.error||d.message||'Unknown error')+'</span>';}}).catch(function(e){document.getElementById('alight-status').innerHTML='<span style="color:#FF6B6B;">Error: '+e.message+'</span>';});}
if(apiKey){document.getElementById('tool-api-key').value=apiKey;document.getElementById('key-status').textContent='API Key loaded: '+apiKey.substring(0,8)+'...';}
</script>
</body></html>"""

# ============================================
# ROUTES
# ============================================
@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        data = load_db()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        for user in data.get('users', []):
            if user['username'] == username:
                stored_hash = user.get('password_hash') or user.get('password')
                if stored_hash and check_password_hash(stored_hash, password):
                    if user.get('expired_at'):
                        if datetime.fromisoformat(user['expired_at']) < datetime.now():
                            error = 'Akun sudah expired!'
                            return render_template_string(LOGIN_PAGE, error=error)
                    session.permanent = True
                    session['user'] = username
                    session['role'] = user.get('role', 'user')
                    return redirect(url_for('dashboard'))
        error = 'Username atau password salah!'
    return render_template_string(LOGIN_PAGE, error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    data = load_db()
    items = data.get('items', [])
    keys = data.get('api_keys', [])
    users = data.get('users', [])
    now = datetime.now()
    active = sum(1 for k in keys if k.get('active') and datetime.fromisoformat(k['expires_at']) > now)
    expired = sum(1 for k in keys if k.get('active') and datetime.fromisoformat(k['expires_at']) <= now)
    return render_template_string(
        DASHBOARD_PAGE.replace('{style}', BASE_STYLE).replace('{script}', SCROLL_JS),
        user=session['user'], total_items=len(items), total_keys=len(keys), active_keys=active, expired_keys=expired, total_users=len(users)
    )

@app.route('/items')
@login_required
def items_page():
    data = load_db()
    return render_template_string(
        ITEMS_PAGE.replace('{style}', BASE_STYLE).replace('{script}', SCROLL_JS),
        items=data.get('items', [])
    )

@app.route('/api-keys')
@admin_required
def api_keys_page():
    data = load_db()
    keys = data.get('api_keys', [])
    now = datetime.now()
    for k in keys:
        k['expired'] = datetime.fromisoformat(k['expires_at']) <= now
    return render_template_string(
        API_KEYS_PAGE.replace('{style}', BASE_STYLE).replace('{script}', SCROLL_JS),
        keys=keys
    )

@app.route('/api/docs')
@login_required
def api_docs():
    return render_template_string(
        API_DOCS_PAGE.replace('{style}', BASE_STYLE).replace('{script}', SCROLL_JS)
    )

@app.route('/users')
@admin_required
def users_page():
    data = load_db()
    users = data.get('users', [])
    now = datetime.now()
    for u in users:
        if u.get('expired_at'):
            u['expired'] = datetime.fromisoformat(u['expired_at']) <= now
    return render_template_string(
        USERS_PAGE.replace('{style}', BASE_STYLE).replace('{script}', SCROLL_JS),
        users=users
    )

@app.route('/tools')
@admin_required
def tools_page():
    return render_template_string(
        TOOLS_PAGE.replace('{style}', BASE_STYLE).replace('{script}', SCROLL_JS)
    )

# ============================================
# API USER MANAGEMENT
# ============================================
@app.route('/api/users/create', methods=['POST'])
@admin_required
def api_create_user():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'harian').lower()
    if not username or not password:
        return jsonify({"status": "error", "message": "Username dan password required"}), 400
    db = load_db()
    for u in db.get('users', []):
        if u['username'] == username:
            return jsonify({"status": "error", "message": "Username sudah digunakan"}), 400
    expired_at = None
    if role == 'harian':
        expired_at = (datetime.now() + timedelta(days=1)).isoformat()
    elif role == 'mingguan':
        expired_at = (datetime.now() + timedelta(days=7)).isoformat()
    elif role == 'bulanan':
        expired_at = (datetime.now() + timedelta(days=30)).isoformat()
    elif role == 'permanen':
        expired_at = None
    else:
        return jsonify({"status": "error", "message": "Role tidak valid"}), 400
    new_user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password_hash": generate_password_hash(password),
        "role": role,
        "expired_at": expired_at,
        "device_id": None,
        "created_at": datetime.now().isoformat()
    }
    db['users'].append(new_user)
    save_db(db)
    return jsonify({"status": "success", "message": f"User {username} created with role {role}", "user": new_user})

@app.route('/api/users/delete', methods=['POST'])
@admin_required
def api_delete_user():
    data = request.get_json()
    user_id = data.get('id')
    if not user_id:
        return jsonify({"status": "error", "message": "User ID required"}), 400
    db = load_db()
    for i, u in enumerate(db.get('users', [])):
        if u['id'] == user_id:
            if u['username'] == 'mazvall':
                return jsonify({"status": "error", "message": "Tidak bisa hapus admin"}), 400
            removed = db['users'].pop(i)
            save_db(db)
            return jsonify({"status": "success", "message": f"User {removed['username']} deleted"})
    return jsonify({"status": "error", "message": "User not found"}), 404

# ============================================
# API KEY MANAGEMENT
# ============================================
@app.route('/api/keys/generate', methods=['POST'])
@admin_required
def api_generate_key():
    req = request.get_json()
    user = req.get('user', '').strip()
    duration = req.get('duration', '1d')
    if not user:
        return jsonify({"status":"error","message":"User harus diisi"}), 400
    key = generate_api_key()
    now = datetime.now()
    if duration.endswith('h'):
        expires = now + timedelta(hours=int(duration[:-1]))
    elif duration.endswith('d'):
        expires = now + timedelta(days=int(duration[:-1]))
    elif duration.endswith('m'):
        expires = now + timedelta(days=int(duration[:-1])*30)
    else:
        expires = now + timedelta(days=1)
    new_key = {
        "key": key,
        "user": user,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "duration": duration,
        "device_fingerprint": None,
        "active": True
    }
    data = load_db()
    if 'api_keys' not in data:
        data['api_keys'] = []
    data['api_keys'].append(new_key)
    save_db(data)
    return jsonify({"status":"success","key":key,"expires_at":expires.isoformat()})

@app.route('/api/keys/toggle', methods=['POST'])
@admin_required
def api_toggle_key():
    req = request.get_json()
    key = req.get('key')
    data = load_db()
    for k in data.get('api_keys', []):
        if k['key'] == key:
            k['active'] = not k.get('active', True)
            save_db(data)
            return jsonify({"status":"success"})
    return jsonify({"status":"error","message":"Key not found"}), 404

@app.route('/api/keys/delete', methods=['POST'])
@admin_required
def api_delete_key():
    req = request.get_json()
    key = req.get('key')
    data = load_db()
    for i, k in enumerate(data.get('api_keys', [])):
        if k['key'] == key:
            data['api_keys'].pop(i)
            save_db(data)
            return jsonify({"status":"success"})
    return jsonify({"status":"error","message":"Key not found"}), 404

# ============================================
# REST API
# ============================================
def require_api_key():
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return None, jsonify({"status":"error","message":"X-API-Key header required"}), 401
    valid, msg = validate_api_key(api_key, request)
    if not valid:
        return None, jsonify({"status":"error","message":msg}), 401
    return api_key, None, None

@app.route('/api/items', methods=['GET'])
def api_get_items():
    err = require_api_key()
    if err[1]: return err[1], err[2]
    data = load_db()
    return jsonify({"status":"success","data":data.get('items',[])})

@app.route('/api/items/<item_id>', methods=['GET'])
def api_get_item(item_id):
    err = require_api_key()
    if err[1]: return err[1], err[2]
    data = load_db()
    for item in data.get('items',[]):
        if item['id'] == item_id:
            return jsonify({"status":"success","data":item})
    return jsonify({"status":"error","message":"Item not found"}), 404

@app.route('/api/items', methods=['POST'])
def api_create_item():
    err = require_api_key()
    if err[1]: return err[1], err[2]
    req = request.get_json()
    if not req or 'name' not in req or 'price' not in req:
        return jsonify({"status":"error","message":"name and price required"}), 400
    data = load_db()
    new_item = {"id":str(uuid.uuid4()),"name":req['name'],"price":req['price'],"active":req.get('active',True),"created_at":datetime.now().isoformat()}
    data['items'].append(new_item)
    save_db(data)
    return jsonify({"status":"success","data":new_item}), 201

@app.route('/api/items/<item_id>', methods=['PUT'])
def api_update_item(item_id):
    err = require_api_key()
    if err[1]: return err[1], err[2]
    req = request.get_json()
    data = load_db()
    for i, item in enumerate(data.get('items',[])):
        if item['id'] == item_id:
            if 'name' in req: data['items'][i]['name'] = req['name']
            if 'price' in req: data['items'][i]['price'] = req['price']
            if 'active' in req: data['items'][i]['active'] = req['active']
            data['items'][i]['updated_at'] = datetime.now().isoformat()
            save_db(data)
            return jsonify({"status":"success","data":data['items'][i]})
    return jsonify({"status":"error","message":"Item not found"}), 404

@app.route('/api/items/<item_id>', methods=['DELETE'])
def api_delete_item(item_id):
    err = require_api_key()
    if err[1]: return err[1], err[2]
    data = load_db()
    for i, item in enumerate(data.get('items',[])):
        if item['id'] == item_id:
            removed = data['items'].pop(i)
            save_db(data)
            return jsonify({"status":"success","message":"Deleted","data":removed})
    return jsonify({"status":"error","message":"Item not found"}), 404

@app.route('/api/auth', methods=['POST'])
def api_auth():
    req = request.get_json()
    if not req:
        return jsonify({"status":"error","message":"Invalid request"}), 400
    data = load_db()
    for user in data['users']:
        stored_hash = user.get('password_hash') or user.get('password')
        if stored_hash and user['username'] == req.get('username') and check_password_hash(stored_hash, req.get('password', '')):
            return jsonify({"status":"success","user":user['username']})
    return jsonify({"status":"error","message":"Invalid credentials"}), 401

# ============================================
# ROUTE API UNTUK TOOLS (WAJIB API KEY)
# ============================================
@app.route('/api/external/keys/create', methods=['POST'])
def create_external_key():
    data = request.get_json() or request.form
    name = data.get('name', 'Tool User')
    new_key = {
        "key": generate_external_key(),
        "name": name,
        "created_at": datetime.now().isoformat(),
        "expired_at": (datetime.now() + timedelta(days=30)).isoformat()
    }
    db = load_external_keys()
    db["keys"].append(new_key)
    save_external_keys(db)
    return jsonify({"status": "success", "api_key": new_key["key"], "expired_at": new_key["expired_at"]})

@app.route('/api/external/keys/list', methods=['GET'])
def list_external_keys():
    db = load_external_keys()
    keys = []
    for k in db.get("keys", []):
        keys.append({
            "key": k["key"][:8] + "...",
            "name": k["name"],
            "created_at": k["created_at"],
            "expired_at": k["expired_at"],
            "active": datetime.fromisoformat(k["expired_at"]) > datetime.now()
        })
    return jsonify({"status": "success", "keys": keys})

@app.route('/api/dailymotion', methods=['GET'])
@require_tool_key
def api_dailymotion():
    params = {k: v for k, v in request.args.items() if v}
    return jsonify(dailymotion.get_videos(**params))

@app.route('/api/dailymotion/video/<video_id>', methods=['GET'])
@require_tool_key
def api_dailymotion_video(video_id):
    return jsonify(dailymotion.get_video(video_id))

@app.route('/api/dailymotion/channels', methods=['GET'])
@require_tool_key
def api_dailymotion_channels():
    page = request.args.get('page', type=int)
    limit = request.args.get('limit', type=int)
    return jsonify(dailymotion.get_channels(page, limit))

@app.route('/api/dailymotion/health', methods=['GET'])
@require_tool_key
def api_dailymotion_health():
    return jsonify(dailymotion.health())

@app.route('/api/keyrafa/bittv', methods=['GET'])
@require_tool_key
def api_keyrafa_bittv():
    type_param = request.args.get('type', 'EV')
    return jsonify(keyrafa.bittv(type_param))

@app.route('/api/keyrafa/vidio', methods=['GET'])
@require_tool_key
def api_keyrafa_vidio():
    q = request.args.get('q')
    if not q:
        return jsonify({"status": "error", "message": "Parameter 'q' required"}), 400
    return jsonify(keyrafa.vidio(q, request.args.get('id')))

@app.route('/api/keyrafa/nexoratv', methods=['GET'])
@require_tool_key
def api_keyrafa_nexoratv():
    return jsonify(keyrafa.nexoratv(request.args.get('channel', '')))

@app.route('/api/keyrafa/netshort', methods=['GET'])
@require_tool_key
def api_keyrafa_netshort():
    book_id = request.args.get('bookId')
    episode = request.args.get('episode', type=int)
    if not book_id or episode is None:
        return jsonify({"status": "error", "message": "bookId and episode required"}), 400
    return jsonify(keyrafa.netshort(book_id, episode))

@app.route('/api/keyrafa/ssweb', methods=['GET'])
@require_tool_key
def api_keyrafa_ssweb():
    url = request.args.get('url')
    if not url:
        return jsonify({"status": "error", "message": "Parameter 'url' required"}), 400
    return jsonify(keyrafa.ssweb(url))

@app.route('/api/keyrafa/translate', methods=['GET'])
@require_tool_key
def api_keyrafa_translate():
    text = request.args.get('text')
    if not text:
        return jsonify({"status": "error", "message": "Parameter 'text' required"}), 400
    return jsonify(keyrafa.translate(text, request.args.get('to', 'en'), request.args.get('from', 'auto')))

@app.route('/api/keyrafa/tiktok', methods=['GET'])
@require_tool_key
def api_keyrafa_tiktok():
    username = request.args.get('username')
    if not username:
        return jsonify({"status": "error", "message": "Parameter 'username' required"}), 400
    return jsonify(keyrafa.tiktok(username))

@app.route('/api/keyrafa/moviebox-horror', methods=['GET'])
@require_tool_key
def api_keyrafa_moviebox_horror():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('perPage', 20, type=int)
    return jsonify(keyrafa.moviebox_horror(page, per_page))

@app.route('/api/keyrafa/moviebox-global', methods=['GET'])
@require_tool_key
def api_keyrafa_moviebox_global():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('perPage', 20, type=int)
    return jsonify(keyrafa.moviebox_global(page, per_page))

@app.route('/api/keyrafa/gempa', methods=['GET'])
@require_tool_key
def api_keyrafa_gempa():
    return jsonify(keyrafa.gempa(request.args.get('type', 'auto')))

@app.route('/api/alight/send', methods=['POST'])
@require_tool_key
def api_alight_send():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({"status": "error", "message": "Email required"}), 400
    return jsonify(alight.send_magic_link(data['email']))

@app.route('/api/alight/activate', methods=['POST'])
@require_tool_key
def api_alight_activate():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('link'):
        return jsonify({"status": "error", "message": "Email and link required"}), 400
    return jsonify(alight.activate_premium(data['email'], data['link']))

# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    print("=" * 50)
    print("   Mazvall official - REST API Server")
    print("   http://localhost:8086")
    print("   Login: mazvall / H0QwVE5ckXoGp2UU1Y7DA4idSbon4t2n")
    print("   &copy; Created Mazvall official Hak cipta")
    print("=" * 50)
    print(" User Roles: Harian, Mingguan, Bulanan, Permanen")
    print(" 1 akun = 1 device")
    print(" Tools Page: /tools (Admin Only)")
    print(" Alight Motion Premium: Real & Work")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8086, debug=True)

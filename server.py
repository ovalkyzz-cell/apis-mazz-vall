from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
import json, os, uuid, string, random
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {
        "users": [{"id":"1","username":"admin","password":"admin123","role":"admin"}],
        "items": [],
        "api_keys": []
    }

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

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

BASE_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter',sans-serif;background:#f0f0f0;min-height:100vh;word-wrap:break-word;overflow-wrap:break-word;}
.fade-in{opacity:0;transform:translateY(30px);transition:opacity .6s ease,transform .6s ease;}
.fade-in.visible{opacity:1;transform:translateY(0);}
.scale-in{opacity:0;transform:scale(.9);transition:opacity .5s ease,transform .5s ease;}
.scale-in.visible{opacity:1;transform:scale(1);}
.credit{text-align:center;padding:20px;font-size:12px;color:#888;border-top:3px solid #000;background:#fff;margin-top:30px;border-radius:0 0 16px 16px;}
.credit span{font-weight:700;color:#000;}
.navbar{display:flex;justify-content:space-between;align-items:center;background:#FFD60A;border:4px solid #000;border-radius:16px;padding:16px 24px;box-shadow:6px 6px 0 #000;margin:20px;}
.navbar .logo{font-weight:800;font-size:20px;white-space:nowrap;}
.navbar .nav-links{display:flex;gap:8px;flex-wrap:wrap;}
.navbar .nav-links a{text-decoration:none;color:#000;font-weight:600;padding:8px 14px;border:3px solid #000;border-radius:10px;background:#fff;transition:all .15s;white-space:nowrap;font-size:13px;}
.navbar .nav-links a:hover{box-shadow:4px 4px 0 #000;transform:translate(-2px,-2px);}
.navbar .nav-links a.active{background:#4ECDC4;}
.container{max-width:1100px;margin:0 auto;padding:0 20px;overflow:hidden;}
.card{background:#fff;border:4px solid #000;border-radius:16px;padding:30px;box-shadow:6px 6px 0 #000;margin-bottom:24px;overflow:hidden;word-wrap:break-word;overflow-wrap:break-word;}
.card h2{font-size:20px;margin-bottom:16px;word-wrap:break-word;}
.btn{font-family:'Inter',sans-serif;font-weight:700;font-size:13px;padding:10px 18px;border:3px solid #000;border-radius:10px;cursor:pointer;transition:all .15s;text-decoration:none;display:inline-block;white-space:nowrap;}
.btn:hover{box-shadow:4px 4px 0 #000;transform:translate(-2px,-2px);}
.btn:active{box-shadow:1px 1px 0 #000;transform:translate(2px,2px);}
.btn-primary{background:#4ECDC4;color:#000;}
.btn-danger{background:#FF6B6B;color:#000;}
.btn-warning{background:#FFD60A;color:#000;}
.btn-secondary{background:#fff;color:#000;}
.btn-sm{padding:6px 12px;font-size:11px;}
input,select,textarea{font-family:'Inter',sans-serif;font-size:14px;padding:10px 14px;border:3px solid #000;border-radius:8px;background:#fff;outline:none;width:100%;margin-bottom:12px;}
input:focus,select:focus,textarea:focus{box-shadow:3px 3px 0 #000;}
.table-wrapper{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -10px;padding:0 10px;}
table{width:100%;border-collapse:collapse;min-width:500px;}
th,td{padding:12px 14px;text-align:left;border:3px solid #000;word-wrap:break-word;overflow-wrap:break-word;}
th{background:#FFD60A;font-weight:700;white-space:nowrap;}
td{max-width:200px;}
tr:nth-child(even){background:#f9f9f9;}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:24px;}
.stat-card{background:#fff;border:4px solid #000;border-radius:14px;padding:20px;box-shadow:5px 5px 0 #000;text-align:center;}
.stat-card .number{font-size:28px;font-weight:800;}
.stat-card .label{font-size:12px;color:#666;margin-top:4px;}
.stat-card:nth-child(1){border-left:8px solid #4ECDC4;}
.stat-card:nth-child(2){border-left:8px solid #FF6B6B;}
.stat-card:nth-child(3){border-left:8px solid #C8B6FF;}
.stat-card:nth-child(4){border-left:8px solid #FFD60A;}
.badge{display:inline-block;padding:4px 10px;border-radius:50px;font-size:11px;font-weight:700;border:2px solid #000;white-space:nowrap;}
.badge-green{background:#CAFFBF;}
.badge-red{background:#FFB4B4;}
.badge-blue{background:#B8F3FF;}
.badge-purple{background:#C8B6FF;}
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.5);z-index:100;justify-content:center;align-items:center;padding:20px;}
.modal-overlay.active{display:flex;}
.modal{background:#fff;border:4px solid #000;border-radius:16px;padding:30px;box-shadow:8px 8px 0 #000;max-width:500px;width:100%;max-height:90vh;overflow-y:auto;}
.page-title{margin-top:20px;margin-bottom:20px;}
.page-title h1{font-size:26px;margin-bottom:6px;}
.page-title p{color:#666;font-size:14px;}
.key-box{background:#f5f5f5;border:3px solid #000;border-radius:10px;padding:12px 16px;font-family:monospace;font-size:13px;word-break:break-all;margin-top:8px;}
pre{background:#f5f5f5;padding:12px;border-radius:6px;margin-top:8px;font-size:11px;overflow-x:auto;white-space:pre-wrap;word-wrap:break-word;border:2px solid #000;}
.api-endpoint{background:#f5f5f5;border:3px solid #000;border-radius:10px;padding:16px;margin-bottom:12px;word-wrap:break-word;}
.api-method{display:inline-block;padding:4px 10px;border-radius:6px;font-weight:700;font-size:12px;margin-right:8px;white-space:nowrap;}
.method-get{background:#4ECDC4;}
.method-post{background:#FFD60A;}
.method-put{background:#C8B6FF;}
.method-delete{background:#FF6B6B;}
@media(max-width:600px){
.navbar{flex-direction:column;gap:10px;padding:12px;}
.navbar .logo{font-size:16px;}
.navbar .nav-links{justify-content:center;}
.navbar .nav-links a{padding:6px 10px;font-size:12px;}
.stats{grid-template-columns:1fr 1fr;}
.stat-card .number{font-size:22px;}
.card{padding:20px;}
.page-title h1{font-size:20px;}
table{min-width:400px;}
th,td{padding:8px 10px;font-size:12px;}
}
</style>
"""

SCROLL_JS = """
<script>
document.addEventListener('DOMContentLoaded',()=>{
const o=new IntersectionObserver(e=>{e.forEach(x=>{if(x.isIntersecting)x.target.classList.add('visible')});},{threshold:.1});
document.querySelectorAll('.fade-in,.scale-in').forEach(el=>o.observe(el));
});
</script>
"""

LOGIN_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Login - Apis MaZz Vall</title>
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
<h1>Apis MaZz Vall</h1>
<p class="subtitle">Masuk ke dashboard admin</p>
{% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
<form method="POST" action="/login">
<div class="form-group"><label>Username</label><input type="text" name="username" placeholder="Masukkan username" required></div>
<div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Masukkan password" required></div>
<button type="submit" class="login-btn">Masuk &#8594;</button>
</form>
<p class="credit">Created <span>MaZz Vall</span></p>
</div></div></body></html>"""

DASHBOARD_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Dashboard - Apis MaZz Vall</title>{style}</head><body>
<nav class="navbar"><div class="logo">&#9889; Apis MaZz Vall</div><div class="nav-links">
<a href="/" class="active">Dashboard</a><a href="/items">Items</a><a href="/api-keys">API Keys</a><a href="/api/docs">Docs</a><a href="/logout" style="background:#FF6B6B;">Logout</a>
</div></nav>
<div class="container">
<div class="page-title fade-in"><h1>Dashboard</h1><p>Selamat datang, {{ user }}!</p></div>
<div class="stats">
<div class="stat-card fade-in"><div class="number">{{ total_items }}</div><div class="label">Total Items</div></div>
<div class="stat-card fade-in"><div class="number">{{ total_keys }}</div><div class="label">API Keys</div></div>
<div class="stat-card fade-in"><div class="number">{{ active_keys }}</div><div class="label">Active Keys</div></div>
<div class="stat-card fade-in"><div class="number">{{ expired_keys }}</div><div class="label">Expired Keys</div></div>
</div>
<div class="card fade-in">
<h2>Quick Info</h2>
<p style="color:#666;font-size:14px;margin-bottom:12px;">Selamat datang di panel admin <strong>Apis MaZz Vall</strong>.</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;">
<a href="/api-keys" class="btn btn-primary">Kelola API Keys</a>
<a href="/items" class="btn btn-warning">Kelola Items</a>
</div>
</div>
</div>
<p class="credit">Created <span>MaZz Vall</span></p>
{script}</body></html>"""

API_KEYS_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>API Keys - Apis MaZz Vall</title>{style}</head><body>
<nav class="navbar"><div class="logo">&#9889; Apis MaZz Vall</div><div class="nav-links">
<a href="/">Dashboard</a><a href="/items">Items</a><a href="/api-keys" class="active">API Keys</a><a href="/api/docs">Docs</a><a href="/logout" style="background:#FF6B6B;">Logout</a>
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
<p class="credit">Created <span>MaZz Vall</span></p>
<script>
function openModal(){document.getElementById('modal').classList.add('active');}
function closeModal(){document.getElementById('modal').classList.remove('active');}
function generateKey(e){
e.preventDefault();
const user=document.getElementById('key-user').value;
const duration=document.getElementById('key-duration').value;
fetch('/api/keys/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:user,duration:duration})})
.then(r=>r.json()).then(d=>{if(d.status==='success')location.reload();else alert(d.message);});
}
function toggleKey(key){
fetch('/api/keys/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:key})})
.then(r=>r.json()).then(()=>location.reload());
}
function deleteKey(key){
if(confirm('Yakin hapus API key ini?')){
fetch('/api/keys/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:key})})
.then(r=>r.json()).then(()=>location.reload());
}
}
</script>
{script}</body></html>"""

ITEMS_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Items - Apis MaZz Vall</title>{style}</head><body>
<nav class="navbar"><div class="logo">&#9889; Apis MaZz Vall</div><div class="nav-links">
<a href="/">Dashboard</a><a href="/items" class="active">Items</a><a href="/api-keys">API Keys</a><a href="/api/docs">Docs</a><a href="/logout" style="background:#FF6B6B;">Logout</a>
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
<p class="credit">Created <span>MaZz Vall</span></p>
<script>
function openModal(){document.getElementById('edit-id').value='';document.getElementById('item-name').value='';document.getElementById('item-price').value='';document.getElementById('item-active').value='true';document.getElementById('modal-title').textContent='Tambah Item';document.getElementById('modal').classList.add('active');}
function closeModal(){document.getElementById('modal').classList.remove('active');}
function editItem(id,name,price,active){document.getElementById('edit-id').value=id;document.getElementById('item-name').value=name;document.getElementById('item-price').value=price;document.getElementById('item-active').value=active;document.getElementById('modal-title').textContent='Edit Item';document.getElementById('modal').classList.add('active');}
function submitForm(e){e.preventDefault();const id=document.getElementById('edit-id').value;const data={name:document.getElementById('item-name').value,price:parseFloat(document.getElementById('item-price').value),active:document.getElementById('item-active').value==='true'};const url=id?'/api/items/'+id:'/api/items';fetch(url,{method:id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).then(r=>r.json()).then(()=>location.reload());}
function deleteItem(id){if(confirm('Yakin hapus?')){fetch('/api/items/'+id,{method:'DELETE'}).then(r=>r.json()).then(()=>location.reload());}}
</script>
{script}</body></html>"""

API_DOCS_PAGE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>API Docs - Apis MaZz Vall</title>{style}</head><body>
<nav class="navbar"><div class="logo">&#9889; Apis MaZz Vall</div><div class="nav-links">
<a href="/">Dashboard</a><a href="/items">Items</a><a href="/api-keys">API Keys</a><a href="/api/docs" class="active">Docs</a><a href="/logout" style="background:#FF6B6B;">Logout</a>
</div></nav>
<div class="container">
<div class="page-title fade-in"><h1>API Documentation</h1><p>Cara menggunakan REST API dengan API key</p></div>

<div class="card fade-in">
<h2>Autentikasi</h2>
<p style="color:#666;font-size:14px;margin-bottom:12px;">Semua request harus menyertakan API key di header:</p>
<pre>X-API-Key: MZval -Xxxxxxxxxxx</pre>
<p style="color:#666;font-size:13px;margin-top:10px;">API key terkunci ke 1 device. Tidak bisa dipakai di device lain.</p>
</div>

<div class="card fade-in">
<h2>Base URL</h2>
<pre>http://localhost:8086/api</pre>
</div>

<div class="card fade-in">
<h2>Endpoints</h2>
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
<p class="credit">Created <span>MaZz Vall</span></p>
<script>
function testApi(method,url){
const result=document.getElementById('api-result');
const apiKey=document.getElementById('test-key').value;
if(!apiKey){result.style.display='block';result.textContent='Masukkan API key terlebih dahulu!';return;}
result.style.display='block';result.textContent='Loading...';
const opts={method,headers:{'Content-Type':'application/json','X-API-Key':apiKey}};
if(method==='POST')opts.body=JSON.stringify({name:'Test Item',price:25000,active:true});
fetch(url,opts).then(r=>r.json()).then(d=>{result.textContent=JSON.stringify(d,null,2);}).catch(e=>{result.textContent='Error: '+e.message;});
}
</script>
{script}</body></html>"""

# --- ROUTES ---

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        data = load_db()
        username = request.form.get('username')
        password = request.form.get('password')
        for user in data['users']:
            if user['username'] == username and user['password'] == password:
                session['user'] = username
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
    now = datetime.now()
    active = sum(1 for k in keys if k.get('active') and datetime.fromisoformat(k['expires_at']) > now)
    expired = sum(1 for k in keys if k.get('active') and datetime.fromisoformat(k['expires_at']) <= now)
    return render_template_string(
        DASHBOARD_PAGE.replace('{style}', BASE_STYLE).replace('{script}', SCROLL_JS),
        user=session['user'], total_items=len(items), total_keys=len(keys), active_keys=active, expired_keys=expired
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

# --- API KEY MANAGEMENT ---

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

# --- REST API (WITH API KEY AUTH) ---

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
        if user['username'] == req.get('username') and user['password'] == req.get('password'):
            return jsonify({"status":"success","user":user['username']})
    return jsonify({"status":"error","message":"Invalid credentials"}), 401

if __name__ == '__main__':
    print("=" * 50)
    print("   Apis MaZz Vall - REST API Server")
    print("   http://localhost:8086")
    print("   Login: admin / admin123")
    print("   Created MaZz Vall")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8086, debug=True)

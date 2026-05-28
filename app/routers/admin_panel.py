from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["admin-panel"])

_HTML_FALLBACK = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin — One Piece TCG</title>
<style>
:root {
  --bg:       #0D0D0D;
  --surf:     #1A1A1A;
  --surf2:    #222;
  --border:   #2E2E2E;
  --gold:     #D4A843;
  --gold-dim: rgba(212,168,67,.12);
  --text:     #FFFFFF;
  --muted:    #888;
  --red:      #E94560;
  --green:    #4CAF81;
  --blue:     #4A9EFF;
}
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family: 'Segoe UI',Arial,sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }

/* ─── LOGIN ─────────────────────────────────────────────── */
#login-screen {
  display:flex; align-items:center; justify-content:center;
  min-height:100vh; padding:20px;
}
.login-card {
  background:var(--surf); border:1px solid var(--border); border-radius:18px;
  padding:40px 36px; width:100%; max-width:400px;
}
.login-card h1 { color:var(--gold); font-size:22px; margin-bottom:4px; }
.login-card p  { color:var(--muted); font-size:13px; margin-bottom:28px; }
.field { margin-bottom:16px; }
.field label { display:block; color:var(--muted); font-size:12px; margin-bottom:6px; text-transform:uppercase; letter-spacing:.5px; }
.field input {
  width:100%; background:var(--surf2); border:1px solid var(--border); border-radius:10px;
  padding:11px 14px; color:var(--text); font-size:14px; outline:none; transition:.2s;
}
.field input:focus { border-color:var(--gold); }
.btn-primary {
  width:100%; background:var(--gold); color:#0D0D0D; border:none; border-radius:10px;
  padding:13px; font-size:15px; font-weight:700; cursor:pointer; margin-top:8px; transition:.2s;
}
.btn-primary:hover { background:#c49a30; }
.btn-primary:disabled { opacity:.5; cursor:not-allowed; }
.error-msg { background:rgba(233,69,96,.12); border:1px solid rgba(233,69,96,.4); border-radius:8px;
  padding:10px 14px; color:var(--red); font-size:13px; margin-top:14px; display:none; }

/* ─── SHELL ──────────────────────────────────────────────── */
#app { display:none; flex-direction:column; min-height:100vh; }

header {
  background:var(--surf); border-bottom:1px solid var(--border);
  padding:0 24px; height:56px; display:flex; align-items:center; justify-content:space-between;
  position:sticky; top:0; z-index:10;
}
header .brand { color:var(--gold); font-weight:800; font-size:17px; display:flex; align-items:center; gap:8px; }
header .brand span { color:var(--muted); font-weight:400; font-size:13px; }
.btn-logout {
  background:transparent; border:1px solid var(--border); border-radius:8px;
  color:var(--muted); padding:7px 14px; font-size:13px; cursor:pointer; transition:.2s;
}
.btn-logout:hover { border-color:var(--red); color:var(--red); }

nav {
  background:var(--surf); border-bottom:1px solid var(--border);
  padding:0 24px; display:flex; gap:4px;
}
.nav-tab {
  padding:13px 18px; font-size:14px; font-weight:600; color:var(--muted);
  cursor:pointer; border-bottom:2px solid transparent; transition:.2s;
  background:none; border-top:none; border-left:none; border-right:none;
}
.nav-tab:hover { color:var(--text); }
.nav-tab.active { color:var(--gold); border-bottom-color:var(--gold); }
.badge {
  display:inline-block; background:var(--red); color:#fff;
  border-radius:10px; font-size:10px; font-weight:700;
  padding:1px 6px; margin-left:5px; vertical-align:middle;
}

main { padding:24px; flex:1; max-width:1200px; width:100%; margin:0 auto; }

.tab-panel { display:none; }
.tab-panel.active { display:block; }

/* ─── STATS ──────────────────────────────────────────────── */
.stats-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:14px; margin-bottom:28px; }
.stat-card {
  background:var(--surf); border:1px solid var(--border); border-radius:14px;
  padding:20px; transition:.2s;
}
.stat-card:hover { border-color:var(--gold); }
.stat-card .icon { font-size:22px; margin-bottom:10px; }
.stat-card .val  { font-size:32px; font-weight:800; color:var(--gold); line-height:1; }
.stat-card .lbl  { font-size:12px; color:var(--muted); margin-top:4px; }
.stat-card.red .val { color:var(--red); }
.stat-card.green .val { color:var(--green); }

/* ─── TABLE ──────────────────────────────────────────────── */
.section-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; gap:12px; flex-wrap:wrap; }
.section-title  { font-size:16px; font-weight:700; }
.search-input {
  background:var(--surf2); border:1px solid var(--border); border-radius:9px;
  padding:8px 13px; color:var(--text); font-size:13px; outline:none; width:220px; transition:.2s;
}
.search-input:focus { border-color:var(--gold); }

.table-wrap { overflow-x:auto; }
table { width:100%; border-collapse:collapse; }
thead th {
  text-align:left; padding:10px 14px; font-size:11px; font-weight:700;
  color:var(--muted); text-transform:uppercase; letter-spacing:.5px;
  border-bottom:1px solid var(--border); background:var(--surf);
}
tbody tr { border-bottom:1px solid var(--border); transition:.15s; }
tbody tr:hover { background:var(--surf2); }
tbody td { padding:12px 14px; font-size:13px; }
.chip {
  display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700;
}
.chip.active  { background:rgba(76,175,129,.15); color:var(--green); border:1px solid rgba(76,175,129,.3); }
.chip.inactive{ background:rgba(233,69,96,.12);  color:var(--red);   border:1px solid rgba(233,69,96,.3); }
.chip.admin   { background:var(--gold-dim);       color:var(--gold);  border:1px solid rgba(212,168,67,.3); }
.chip.type-feedback   { background:rgba(74,158,255,.12); color:var(--blue);  border:1px solid rgba(74,158,255,.3); }
.chip.type-bug        { background:rgba(233,69,96,.12);  color:var(--red);   border:1px solid rgba(233,69,96,.3); }
.chip.type-suggestion { background:rgba(76,175,129,.15); color:var(--green); border:1px solid rgba(76,175,129,.3); }

.btn-sm {
  padding:5px 12px; border-radius:7px; font-size:12px; font-weight:700;
  cursor:pointer; border:none; transition:.2s;
}
.btn-sm.deactivate { background:rgba(233,69,96,.15); color:var(--red); }
.btn-sm.deactivate:hover { background:var(--red); color:#fff; }
.btn-sm.activate   { background:rgba(76,175,129,.15); color:var(--green); }
.btn-sm.activate:hover   { background:var(--green); color:#fff; }
.btn-sm.mark-read    { background:var(--surf2); color:var(--muted); border:1px solid var(--border); }
.btn-sm.mark-read:hover  { border-color:var(--gold); color:var(--gold); }
.btn-sm.mark-unread  { background:rgba(212,168,67,.12); color:var(--gold); border:1px solid rgba(212,168,67,.3); }
.btn-sm.mark-unread:hover { background:var(--gold); color:#0D0D0D; }
.btn-sm.delete       { background:rgba(233,69,96,.12); color:var(--red); border:1px solid rgba(233,69,96,.3); }
.btn-sm.delete:hover { background:var(--red); color:#fff; }
.btn-sm:disabled   { opacity:.4; cursor:not-allowed; }

/* ─── PAGINATION ──────────────────────────────────────────── */
.pagination { display:flex; align-items:center; justify-content:flex-end; gap:8px; margin-top:16px; }
.pagination span { font-size:13px; color:var(--muted); }
.btn-page {
  background:var(--surf2); border:1px solid var(--border); border-radius:7px;
  color:var(--text); padding:6px 14px; font-size:13px; cursor:pointer; transition:.2s;
}
.btn-page:hover:not(:disabled) { border-color:var(--gold); color:var(--gold); }
.btn-page:disabled { opacity:.4; cursor:not-allowed; }

/* ─── FEEDBACK CARDS ──────────────────────────────────────── */
.feedback-filters { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
.filter-btn {
  padding:6px 14px; border-radius:20px; font-size:12px; font-weight:600; cursor:pointer;
  background:var(--surf2); border:1px solid var(--border); color:var(--muted); transition:.2s;
}
.filter-btn.active { background:var(--gold-dim); border-color:rgba(212,168,67,.4); color:var(--gold); }
.fb-card {
  background:var(--surf); border:1px solid var(--border); border-radius:12px;
  padding:16px 18px; margin-bottom:10px; display:flex; gap:14px; align-items:flex-start;
  transition:.2s;
}
.fb-card.unread { border-left:3px solid var(--gold); }
.fb-card .fb-meta { flex:1; min-width:0; }
.fb-card .fb-header { display:flex; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap; }
.fb-card .fb-user   { font-weight:700; font-size:13px; }
.fb-card .fb-date   { font-size:11px; color:var(--muted); }
.fb-card .fb-text   { font-size:13px; color:#ccc; line-height:1.5; }
.fb-card .fb-action { flex-shrink:0; padding-top:2px; display:flex; flex-direction:column; gap:5px; align-items:flex-end; }

/* ─── EMPTY / LOADING ─────────────────────────────────────── */
.empty { text-align:center; padding:48px 0; color:var(--muted); font-size:14px; }
.spinner {
  display:inline-block; width:20px; height:20px;
  border:2px solid var(--border); border-top-color:var(--gold);
  border-radius:50%; animation:spin .7s linear infinite;
}
@keyframes spin { to { transform:rotate(360deg); } }
.loading-row td { text-align:center; padding:32px; }

/* ─── TOASTS ──────────────────────────────────────────────── */
#toast-container { position:fixed; bottom:24px; right:24px; z-index:9999; display:flex; flex-direction:column-reverse; gap:8px; pointer-events:none; }
.toast {
  padding:11px 16px; border-radius:10px; font-size:13px; font-weight:600;
  color:#fff; box-shadow:0 4px 20px rgba(0,0,0,.6); max-width:300px;
  animation:toastIn .2s ease; pointer-events:none;
}
.toast.success { background:var(--green); }
.toast.error   { background:var(--red);   }
.toast.info    { background:var(--blue);  }
@keyframes toastIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:none; } }
</style>
</head>
<body>

<!-- ═══ LOGIN ═══════════════════════════════════════════════ -->
<div id="login-screen">
  <div class="login-card">
    <h1>⚔️ One Piece TCG</h1>
    <p>Panel de administración — solo admins</p>
    <div class="field"><label>Usuario o Email</label>
      <input id="l-user" type="text" placeholder="tu_usuario" autocomplete="username">
    </div>
    <div class="field"><label>Contraseña</label>
      <input id="l-pass" type="password" placeholder="••••••••" autocomplete="current-password">
    </div>
    <button class="btn-primary" id="l-btn" onclick="doLogin()">Iniciar sesión</button>
    <div class="error-msg" id="l-err"></div>
  </div>
</div>

<!-- ═══ APP SHELL ════════════════════════════════════════════ -->
<div id="app">
  <header>
    <div class="brand">⚔️ One Piece TCG <span>Admin</span></div>
    <button class="btn-logout" onclick="doLogout()">Cerrar sesión</button>
  </header>

  <nav>
    <button class="nav-tab active" onclick="switchTab('stats',this)">📊 Resumen</button>
    <button class="nav-tab" onclick="switchTab('users',this)">👥 Usuarios</button>
    <button class="nav-tab" onclick="switchTab('feedback',this)">
      💬 Mensajes<span class="badge" id="unread-badge" style="display:none">0</span>
    </button>
  </nav>

  <main>

    <!-- ── STATS ──────────────────────────────────────────── -->
    <div id="tab-stats" class="tab-panel active">
      <div class="stats-grid" id="stats-grid">
        <div class="stat-card"><div class="icon">👤</div><div class="val" id="s-total">—</div><div class="lbl">Total usuarios</div></div>
        <div class="stat-card green"><div class="icon">✅</div><div class="val" id="s-active">—</div><div class="lbl">Usuarios activos</div></div>
        <div class="stat-card" style="border-color:rgba(212,168,67,.3)"><div class="icon">⭐</div><div class="val" id="s-premium" style="color:var(--gold)">—</div><div class="lbl">Usuarios Premium</div></div>
        <div class="stat-card"><div class="icon">🃏</div><div class="val" id="s-cards">—</div><div class="lbl">Cartas registradas</div></div>
        <div class="stat-card red"><div class="icon">💬</div><div class="val" id="s-unread">—</div><div class="lbl">Mensajes sin leer</div></div>
        <div class="stat-card"><div class="icon">📨</div><div class="val" id="s-total-fb">—</div><div class="lbl">Total mensajes</div></div>
      </div>
      <p style="color:var(--muted);font-size:12px">Se actualiza automáticamente cada 30 segundos.</p>
    </div>

    <!-- ── USUARIOS ───────────────────────────────────────── -->
    <div id="tab-users" class="tab-panel">
      <div class="section-header">
        <div class="section-title">Usuarios registrados</div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="btn-sm" id="reload-users-btn"
            style="background:var(--surf2);color:var(--muted);border:1px solid var(--border)"
            onclick="loadUsers()">↻ Recargar</button>
          <input class="search-input" id="user-search" type="text" placeholder="🔍  Buscar usuario o email…" oninput="filterUsers()">
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Usuario</th><th>Email</th><th>Registrado</th><th>Estado</th><th>Plan</th><th>Acciones</th>
            </tr>
          </thead>
          <tbody id="users-tbody">
            <tr class="loading-row"><td colspan="7"><span class="spinner"></span></td></tr>
          </tbody>
        </table>
      </div>
      <div class="pagination">
        <button class="btn-page" id="u-prev" onclick="usersPage(-1)" disabled>← Anterior</button>
        <span id="u-page-info">Página 1</span>
        <button class="btn-page" id="u-next" onclick="usersPage(1)">Siguiente →</button>
      </div>
    </div>

    <!-- ── FEEDBACK ───────────────────────────────────────── -->
    <div id="tab-feedback" class="tab-panel">
      <div class="section-header">
        <div class="section-title">Mensajes y reportes</div>
      </div>
      <div class="feedback-filters">
        <button class="filter-btn active" id="fb-filter-all" onclick="setFbFilter(false,this)">Todos</button>
        <button class="filter-btn" id="fb-filter-unread" onclick="setFbFilter(true,this)">Solo no leídos</button>
      </div>
      <div id="feedback-list"><div class="empty"><span class="spinner"></span></div></div>
      <div class="pagination">
        <button class="btn-page" id="f-prev" onclick="fbPage(-1)" disabled>← Anterior</button>
        <span id="f-page-info">Página 1</span>
        <button class="btn-page" id="f-next" onclick="fbPage(1)">Siguiente →</button>
      </div>
    </div>

  </main>
</div>

<!-- Toast container -->
<div id="toast-container"></div>

<script>
// ─── State ────────────────────────────────────────────────────────────────────
let TOKEN = localStorage.getItem('admin_token') || '';
let usersData = [], usersFiltered = [], usersPage_ = 1;
const USERS_PER_PAGE = 50;
let fbPage_ = 1, fbUnreadOnly = false;
let statsInterval = null;

// ─── Boot ─────────────────────────────────────────────────────────────────────
(async () => {
  if (TOKEN) {
    const ok = await tryShowApp();
    if (!ok) { TOKEN = ''; localStorage.removeItem('admin_token'); }
  }
})();

// ─── Auth ─────────────────────────────────────────────────────────────────────
async function doLogin() {
  const user = document.getElementById('l-user').value.trim();
  const pass = document.getElementById('l-pass').value;
  const btn  = document.getElementById('l-btn');
  const err  = document.getElementById('l-err');
  if (!user || !pass) { showErr('Completa todos los campos.'); return; }

  btn.disabled = true; btn.textContent = 'Entrando…';
  err.style.display = 'none';

  try {
    const res = await fetch('/auth/login', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({email_or_username: user, password: pass})
    });
    if (!res.ok) {
      const d = await res.json();
      showErr(d.detail || 'Credenciales incorrectas.');
      return;
    }
    const data = await res.json();
    TOKEN = data.access_token;

    // Verifica que sea admin intentando cargar stats
    const check = await fetch('/admin/stats', { headers: authHeader() });
    if (check.status === 403) { showErr('Tu cuenta no tiene permisos de administrador.'); TOKEN=''; return; }
    if (!check.ok) { showErr('Error al verificar permisos.'); TOKEN=''; return; }

    localStorage.setItem('admin_token', TOKEN);
    showApp();
  } catch {
    showErr('No se pudo conectar al servidor.');
  } finally {
    btn.disabled = false; btn.textContent = 'Iniciar sesión';
  }
}

async function tryShowApp() {
  const check = await fetch('/admin/stats', { headers: authHeader() }).catch(() => null);
  if (!check || !check.ok) return false;
  showApp();
  return true;
}

function doLogout() {
  TOKEN = ''; localStorage.removeItem('admin_token');
  clearInterval(statsInterval);
  document.getElementById('app').style.display = 'none';
  document.getElementById('login-screen').style.display = 'flex';
}

function showApp() {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app').style.display = 'flex';
  loadStats();
  loadUsers();
  loadFeedback();
  statsInterval = setInterval(loadStats, 30000);
}

function showErr(msg) {
  const e = document.getElementById('l-err');
  e.textContent = msg; e.style.display = 'block';
}

function authHeader() { return { 'Authorization': 'Bearer ' + TOKEN }; }

// ─── Tabs ─────────────────────────────────────────────────────────────────────
function switchTab(name, el) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  el.classList.add('active');
  // Refresca datos al entrar a cada tab para que siempre estén actualizados
  if (name === 'users')    loadUsers();
  if (name === 'feedback') { fbPage_ = 1; loadFeedback(); }
}

// ─── Stats ────────────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const res = await fetch('/admin/stats', { headers: authHeader() });
    if (res.status === 401) { doLogout(); return; }
    const d = await res.json();
    document.getElementById('s-total').textContent    = d.total_users.toLocaleString();
    document.getElementById('s-active').textContent   = d.active_users.toLocaleString();
    document.getElementById('s-premium').textContent  = d.premium_users.toLocaleString();
    document.getElementById('s-cards').textContent    = d.total_cards_registered.toLocaleString();
    document.getElementById('s-unread').textContent   = d.unread_feedback.toLocaleString();
    document.getElementById('s-total-fb').textContent = d.total_feedback.toLocaleString();
    const badge = document.getElementById('unread-badge');
    if (d.unread_feedback > 0) { badge.textContent = d.unread_feedback; badge.style.display=''; }
    else badge.style.display = 'none';
  } catch {}
}

// ─── Users ────────────────────────────────────────────────────────────────────
async function loadUsers() {
  const btn = document.getElementById('reload-users-btn');
  if (btn) { btn.disabled = true; btn.textContent = '…'; }
  document.getElementById('users-tbody').innerHTML =
    '<tr class="loading-row"><td colspan="7"><span class="spinner"></span></td></tr>';
  try {
    const res = await fetch('/admin/users?limit=500', { headers: authHeader() });
    if (res.status === 401) { doLogout(); return; }
    if (!res.ok) throw new Error('HTTP ' + res.status);
    usersData = await res.json();
    usersFiltered = [...usersData];
    usersPage_ = 1;
    renderUsers();
  } catch (e) {
    document.getElementById('users-tbody').innerHTML =
      `<tr class="loading-row"><td colspan="7" style="color:var(--red)">Error al cargar usuarios: ${e.message}</td></tr>`;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '↻ Recargar'; }
  }
}

function filterUsers() {
  const q = document.getElementById('user-search').value.toLowerCase();
  usersFiltered = usersData.filter(u =>
    u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
  );
  usersPage_ = 1;
  renderUsers();
}

function usersPage(delta) {
  const maxPage = Math.ceil(usersFiltered.length / USERS_PER_PAGE);
  usersPage_ = Math.max(1, Math.min(usersPage_ + delta, maxPage));
  renderUsers();
}

function renderUsers() {
  const tbody = document.getElementById('users-tbody');
  const start = (usersPage_ - 1) * USERS_PER_PAGE;
  const slice = usersFiltered.slice(start, start + USERS_PER_PAGE);
  const maxPage = Math.ceil(usersFiltered.length / USERS_PER_PAGE) || 1;

  document.getElementById('u-page-info').textContent =
    `Página ${usersPage_} de ${maxPage} · ${usersFiltered.length} usuarios`;
  document.getElementById('u-prev').disabled = usersPage_ <= 1;
  document.getElementById('u-next').disabled = usersPage_ >= maxPage;

  if (!slice.length) {
    tbody.innerHTML = '<tr class="loading-row"><td colspan="7" class="empty">No hay usuarios.</td></tr>';
    return;
  }

  tbody.innerHTML = slice.map(u => `
    <tr id="user-row-${u.id}">
      <td style="color:var(--muted)">${u.id}</td>
      <td>
        <strong>${esc(u.username)}</strong>
        ${u.is_admin ? '<span class="chip admin">admin</span>' : ''}
      </td>
      <td style="color:var(--muted)">${esc(u.email)}</td>
      <td style="color:var(--muted)">${fmtDate(u.created_at)}</td>
      <td><span class="chip ${u.is_active ? 'active' : 'inactive'}">${u.is_active ? 'Activo' : 'Inactivo'}</span></td>
      <td>
        ${u.is_premium
          ? `<span class="chip" style="background:rgba(212,168,67,.15);color:var(--gold);border:1px solid rgba(212,168,67,.35)">⭐ Premium</span>`
          : `<span class="chip" style="background:var(--surf2);color:var(--muted);border:1px solid var(--border)">Free</span>`
        }
      </td>
      <td style="display:flex;gap:6px;flex-wrap:wrap">
        ${u.is_admin ? '<span style="color:var(--muted);font-size:12px">—</span>' : `
          ${u.is_active
            ? `<button class="btn-sm deactivate" onclick="toggleUser(${u.id},false,this)">Desactivar</button>`
            : `<button class="btn-sm activate"   onclick="toggleUser(${u.id},true,this)">Activar</button>`
          }
          ${u.is_premium
            ? `<button class="btn-sm" style="background:rgba(212,168,67,.12);color:var(--gold)" onclick="setPlan(${u.id},false,this)">→ Free</button>`
            : `<button class="btn-sm" style="background:rgba(212,168,67,.12);color:var(--gold)" onclick="setPlan(${u.id},true,this)">→ Premium</button>`
          }
        `}
      </td>
    </tr>
  `).join('');
}

async function toggleUser(id, active, btn) {
  // Deshabilitar toda la fila durante la operación
  const row = document.getElementById('user-row-' + id);
  const rowBtns = row ? row.querySelectorAll('button') : [btn];
  rowBtns.forEach(b => b.disabled = true);
  try {
    const res = await fetch(`/admin/users/${id}`, {
      method: 'PATCH',
      headers: { ...authHeader(), 'Content-Type':'application/json' },
      body: JSON.stringify({ is_active: active })
    });
    if (res.status === 401) { doLogout(); return; }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error del servidor');
    }
    // Actualizar estado local
    const u = usersData.find(u => u.id === id);
    if (u) u.is_active = active;
    // usersFiltered comparte referencias con usersData — ya está actualizado
    renderUsers();
    loadStats();
    showToast(active ? '✓ Cuenta activada' : '✓ Cuenta desactivada');
  } catch (e) {
    showToast(e.message || 'Error al cambiar el estado.', 'error');
    rowBtns.forEach(b => b.disabled = false);
  }
}

async function setPlan(id, isPremium, btn) {
  const row = document.getElementById('user-row-' + id);
  const rowBtns = row ? row.querySelectorAll('button') : [btn];
  rowBtns.forEach(b => b.disabled = true);
  try {
    const res = await fetch(`/admin/users/${id}/plan`, {
      method: 'PATCH',
      headers: { ...authHeader(), 'Content-Type':'application/json' },
      body: JSON.stringify({ is_premium: isPremium })
    });
    if (res.status === 401) { doLogout(); return; }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error del servidor');
    }
    const u = usersData.find(u => u.id === id);
    if (u) u.is_premium = isPremium;
    renderUsers();
    loadStats();
    showToast(isPremium ? '⭐ Plan Premium activado' : '✓ Cambiado a plan Free');
  } catch (e) {
    showToast(e.message || 'Error al cambiar el plan.', 'error');
    rowBtns.forEach(b => b.disabled = false);
  }
}

// ─── Toast notifications ──────────────────────────────────────────────────────
function showToast(msg, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  // Auto-remove after 3 s
  setTimeout(() => {
    toast.style.transition = 'opacity .3s';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 320);
  }, 3000);
}

// ─── Feedback ─────────────────────────────────────────────────────────────────
async function loadFeedback() {
  document.getElementById('feedback-list').innerHTML =
    '<div class="empty"><span class="spinner"></span></div>';
  try {
    const url = `/admin/feedback?limit=20&page=${fbPage_}` + (fbUnreadOnly ? '&unread_only=true' : '');
    const res = await fetch(url, { headers: authHeader() });
    if (res.status === 401) { doLogout(); return; }
    const items = await res.json();
    renderFeedback(items);
  } catch {
    document.getElementById('feedback-list').innerHTML =
      '<div class="empty" style="color:var(--red)">Error al cargar mensajes.</div>';
  }
}

function setFbFilter(unreadOnly, btn) {
  fbUnreadOnly = unreadOnly; fbPage_ = 1;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadFeedback();
}

function fbPage(delta) {
  fbPage_ = Math.max(1, fbPage_ + delta);
  loadFeedback();
}

function renderFeedback(items) {
  const list = document.getElementById('feedback-list');
  document.getElementById('f-page-info').textContent = `Página ${fbPage_}`;
  document.getElementById('f-prev').disabled = fbPage_ <= 1;
  document.getElementById('f-next').disabled = items.length < 20;

  if (!items.length) {
    list.innerHTML = '<div class="empty">No hay mensajes.</div>';
    return;
  }

  const typeLabels = { feedback:'💬 Comentario', bug:'🐛 Error/Bug', suggestion:'💡 Sugerencia' };
  const typeCls    = { feedback:'type-feedback', bug:'type-bug', suggestion:'type-suggestion' };

  list.innerHTML = items.map(fb => `
    <div class="fb-card ${fb.is_read ? '' : 'unread'}" id="fb-${fb.id}">
      <div class="fb-meta">
        <div class="fb-header">
          <span class="chip ${typeCls[fb.type] || 'type-feedback'}">${typeLabels[fb.type] || fb.type}</span>
          <span class="fb-user">${fb.username ? esc(fb.username) : '<em style="color:var(--muted)">anónimo</em>'}</span>
          <span class="fb-date">${fmtDateFull(fb.created_at)}</span>
          ${!fb.is_read ? '<span class="fb-new" style="font-size:11px;color:var(--gold);font-weight:700">● Nuevo</span>' : ''}
        </div>
        <div class="fb-text">${esc(fb.message)}</div>
      </div>
      <div class="fb-action">
        ${!fb.is_read
          ? `<button class="btn-sm mark-read" onclick="markRead(${fb.id},this)">Marcar leído</button>`
          : `<button class="btn-sm mark-unread" onclick="markUnread(${fb.id},this)">Marcar no leído</button>`
        }
        <button class="btn-sm delete" onclick="deleteFeedback(${fb.id},this)">Eliminar</button>
      </div>
    </div>
  `).join('');
}

async function markRead(id, btn) {
  btn.disabled = true;
  try {
    const res = await fetch(`/admin/feedback/${id}/read`, {
      method: 'PATCH', headers: authHeader()
    });
    if (!res.ok) throw new Error();
    const card = document.getElementById('fb-' + id);
    if (card) {
      card.classList.remove('unread');
      // Quitar badge "● Nuevo"
      card.querySelectorAll('.fb-header span').forEach(s => {
        if (s.textContent.includes('Nuevo')) s.remove();
      });
      const action = card.querySelector('.fb-action');
      action.innerHTML = `
        <button class="btn-sm mark-unread" onclick="markUnread(${id},this)">Marcar no leído</button>
        <button class="btn-sm delete" onclick="deleteFeedback(${id},this)">Eliminar</button>
      `;
    }
    loadStats();
  } catch {
    btn.disabled = false;
    alert('Error al marcar como leído.');
  }
}

async function markUnread(id, btn) {
  btn.disabled = true;
  try {
    const res = await fetch(`/admin/feedback/${id}/unread`, {
      method: 'PATCH', headers: authHeader()
    });
    if (!res.ok) throw new Error();
    const card = document.getElementById('fb-' + id);
    if (card) {
      card.classList.add('unread');
      // Añadir badge "● Nuevo" si no existe
      const header = card.querySelector('.fb-header');
      if (!header.querySelector('.fb-new')) {
        const badge = document.createElement('span');
        badge.className = 'fb-new';
        badge.style.cssText = 'font-size:11px;color:var(--gold);font-weight:700';
        badge.textContent = '● Nuevo';
        header.appendChild(badge);
      }
      const action = card.querySelector('.fb-action');
      action.innerHTML = `
        <button class="btn-sm mark-read" onclick="markRead(${id},this)">Marcar leído</button>
        <button class="btn-sm delete" onclick="deleteFeedback(${id},this)">Eliminar</button>
      `;
    }
    loadStats();
  } catch {
    btn.disabled = false;
    alert('Error al marcar como no leído.');
  }
}

async function deleteFeedback(id, btn) {
  if (!confirm('¿Eliminar este mensaje permanentemente? Esta acción no se puede deshacer.')) return;
  btn.disabled = true;
  try {
    const res = await fetch(`/admin/feedback/${id}`, {
      method: 'DELETE', headers: authHeader()
    });
    if (!res.ok) throw new Error();
    const card = document.getElementById('fb-' + id);
    if (card) {
      card.style.opacity = '0';
      card.style.transition = 'opacity .25s';
      setTimeout(() => card.remove(), 260);
    }
    loadStats();
  } catch {
    btn.disabled = false;
    alert('Error al eliminar el mensaje.');
  }
}

// ─── Enter en login ────────────────────────────────────────────────────────────
document.getElementById('l-pass').addEventListener('keydown', e => {
  if (e.key === 'Enter') doLogin();
});
document.getElementById('l-user').addEventListener('keydown', e => {
  if (e.key === 'Enter') document.getElementById('l-pass').focus();
});

// ─── Utils ────────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function fmtDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('es-CL', {day:'2-digit',month:'short',year:'numeric'});
}
function fmtDateFull(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'})
       + ' ' + d.toLocaleTimeString('es-CL',{hour:'2-digit',minute:'2-digit'});
}
</script>
</body>
</html>"""


@router.get("/admin", include_in_schema=False)
async def admin_panel():
    return HTMLResponse(_HTML_FALLBACK)

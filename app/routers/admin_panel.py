from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["admin-panel"])

# ─────────────────────────────────────────────────────────────────────────────
# Nakama Cards — Admin Dashboard v2
# Tabs: Resumen · Usuarios · TCG Stats · Mensajes · Logs · Sistema
# ─────────────────────────────────────────────────────────────────────────────

_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin — Nakama Cards</title>
<style>
:root {
  --bg:     #0A0A0F;
  --surf:   #13131A;
  --surf2:  #1C1C26;
  --surf3:  #232330;
  --border: #2A2A3A;
  --gold:   #D4A843;
  --gold2:  #FFD700;
  --gold-d: rgba(212,168,67,.12);
  --text:   #F0F0F0;
  --muted:  #6B6B80;
  --muted2: #9090A0;
  --red:    #E94560;
  --green:  #3EBF7E;
  --blue:   #4A9EFF;
  --purple: #A06EE0;
  --orange: #F09040;
  --radius: 14px;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;font-size:14px}
a{color:var(--gold);text-decoration:none}

/* ── SCROLLBAR ─────────────────────────────────────────── */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}

/* ── LOGIN ─────────────────────────────────────────────── */
#login-screen{display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px;background:radial-gradient(ellipse at 50% 0%,rgba(212,168,67,.06),transparent 70%)}
.login-card{background:var(--surf);border:1px solid var(--border);border-radius:20px;padding:44px 40px;width:100%;max-width:400px;box-shadow:0 20px 60px rgba(0,0,0,.5)}
.login-logo{font-size:36px;margin-bottom:10px;text-align:center}
.login-card h1{color:var(--gold);font-size:20px;font-weight:800;text-align:center;margin-bottom:4px}
.login-card p{color:var(--muted);font-size:13px;text-align:center;margin-bottom:30px}
.field{margin-bottom:16px}
.field label{display:block;color:var(--muted2);font-size:11px;font-weight:700;margin-bottom:7px;text-transform:uppercase;letter-spacing:.6px}
.field input{width:100%;background:var(--surf2);border:1.5px solid var(--border);border-radius:10px;padding:11px 14px;color:var(--text);font-size:14px;outline:none;transition:.2s}
.field input:focus{border-color:var(--gold)}
.btn-primary{width:100%;background:linear-gradient(135deg,var(--gold),#c49a30);color:#0A0A0F;border:none;border-radius:10px;padding:13px;font-size:15px;font-weight:800;cursor:pointer;margin-top:6px;transition:.2s;letter-spacing:.3px}
.btn-primary:hover{opacity:.92}
.btn-primary:disabled{opacity:.45;cursor:not-allowed}
.error-msg{background:rgba(233,69,96,.1);border:1.5px solid rgba(233,69,96,.35);border-radius:9px;padding:10px 14px;color:var(--red);font-size:13px;margin-top:14px;display:none}

/* ── SHELL ─────────────────────────────────────────────── */
#app{display:none;flex-direction:column;min-height:100vh}
header{background:var(--surf);border-bottom:1px solid var(--border);padding:0 28px;height:58px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.brand{display:flex;align-items:center;gap:10px}
.brand-icon{font-size:22px}
.brand-name{color:var(--gold);font-weight:800;font-size:17px}
.brand-tag{color:var(--muted);font-size:12px;background:var(--surf2);border:1px solid var(--border);border-radius:6px;padding:2px 8px;margin-left:4px}
.header-right{display:flex;align-items:center;gap:12px}
.admin-name{color:var(--muted2);font-size:13px}
.btn-logout{background:transparent;border:1.5px solid var(--border);border-radius:8px;color:var(--muted);padding:7px 14px;font-size:13px;cursor:pointer;transition:.2s}
.btn-logout:hover{border-color:var(--red);color:var(--red)}

/* ── NAV ───────────────────────────────────────────────── */
nav{background:var(--surf);border-bottom:1px solid var(--border);padding:0 28px;display:flex;gap:2px;overflow-x:auto}
.nav-tab{padding:14px 18px;font-size:13px;font-weight:600;color:var(--muted);cursor:pointer;border:none;border-bottom:2.5px solid transparent;background:none;transition:.2s;white-space:nowrap;display:flex;align-items:center;gap:7px}
.nav-tab:hover{color:var(--text)}
.nav-tab.active{color:var(--gold);border-bottom-color:var(--gold)}
.badge{background:var(--red);color:#fff;border-radius:10px;font-size:10px;font-weight:700;padding:1px 6px;line-height:1.4}

/* ── MAIN ──────────────────────────────────────────────── */
main{padding:26px;flex:1;max-width:1280px;width:100%;margin:0 auto}
.tab-panel{display:none;animation:fadeIn .2s ease}
.tab-panel.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}

/* ── SECTION ───────────────────────────────────────────── */
.section-title{font-size:15px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.section-title::before{content:'';display:block;width:3px;height:16px;background:var(--gold);border-radius:2px}
.section-divider{height:1px;background:var(--border);margin:28px 0}

/* ── STAT GRID ─────────────────────────────────────────── */
.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(165px,1fr));gap:12px;margin-bottom:28px}
.stat-card{background:var(--surf);border:1.5px solid var(--border);border-radius:var(--radius);padding:18px;transition:.2s;position:relative;overflow:hidden}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--border);border-radius:var(--radius) var(--radius) 0 0}
.stat-card.c-gold::before{background:linear-gradient(90deg,var(--gold),#c49a30)}
.stat-card.c-green::before{background:var(--green)}
.stat-card.c-red::before{background:var(--red)}
.stat-card.c-blue::before{background:var(--blue)}
.stat-card.c-purple::before{background:var(--purple)}
.stat-card.c-orange::before{background:var(--orange)}
.stat-card:hover{border-color:rgba(212,168,67,.4);transform:translateY(-1px)}
.sc-icon{font-size:20px;margin-bottom:10px;opacity:.9}
.sc-val{font-size:30px;font-weight:800;line-height:1;margin-bottom:4px}
.sc-lbl{font-size:11px;color:var(--muted);font-weight:500;letter-spacing:.3px}
.sc-sub{font-size:10px;color:var(--muted);margin-top:6px;padding-top:6px;border-top:1px solid var(--border)}
.c-gold .sc-val{color:var(--gold)}
.c-green .sc-val{color:var(--green)}
.c-red .sc-val{color:var(--red)}
.c-blue .sc-val{color:var(--blue)}
.c-purple .sc-val{color:var(--purple)}
.c-orange .sc-val{color:var(--orange)}

/* ── TWO-COL GRID ──────────────────────────────────────── */
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.three-col{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
@media(max-width:900px){.two-col,.three-col{grid-template-columns:1fr}}

/* ── PANEL CARD ────────────────────────────────────────── */
.panel{background:var(--surf);border:1.5px solid var(--border);border-radius:var(--radius);padding:20px}
.panel-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.panel-title{font-size:13px;font-weight:700;color:var(--muted2)}

/* ── BAR CHART ─────────────────────────────────────────── */
.bar-list{display:flex;flex-direction:column;gap:10px}
.bar-item{display:flex;align-items:center;gap:10px}
.bar-label{font-size:12px;color:var(--muted2);width:80px;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-label.wide{width:130px}
.bar-track{flex:1;background:var(--surf3);border-radius:4px;height:7px;overflow:hidden}
.bar-fill{height:100%;border-radius:4px;transition:width .6s ease}
.bar-val{font-size:12px;color:var(--text);font-weight:700;width:52px;text-align:right;flex-shrink:0}

/* ── COLOR DOTS ────────────────────────────────────────── */
.color-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0;display:inline-block}

/* ── TABLE ─────────────────────────────────────────────── */
.section-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;gap:12px;flex-wrap:wrap}
.search-input{background:var(--surf2);border:1.5px solid var(--border);border-radius:9px;padding:8px 13px;color:var(--text);font-size:13px;outline:none;width:220px;transition:.2s}
.search-input:focus{border-color:var(--gold)}
.filter-row{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.filter-chip{padding:5px 13px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;background:var(--surf2);border:1.5px solid var(--border);color:var(--muted);transition:.2s}
.filter-chip:hover{color:var(--text);border-color:var(--muted)}
.filter-chip.active{background:var(--gold-d);border-color:rgba(212,168,67,.45);color:var(--gold)}
.table-wrap{overflow-x:auto;border-radius:10px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse}
thead th{text-align:left;padding:10px 14px;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);background:var(--surf2)}
tbody tr{border-bottom:1px solid var(--border);transition:.15s}
tbody tr:last-child{border-bottom:none}
tbody tr:hover{background:var(--surf2)}
tbody td{padding:11px 14px;font-size:13px;vertical-align:middle}
.chip{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
.chip.active  {background:rgba(62,191,126,.14);color:var(--green);border:1px solid rgba(62,191,126,.3)}
.chip.inactive{background:rgba(233,69,96,.12);color:var(--red);border:1px solid rgba(233,69,96,.3)}
.chip.admin   {background:var(--gold-d);color:var(--gold);border:1px solid rgba(212,168,67,.3)}
.chip.premium {background:rgba(212,168,67,.15);color:var(--gold);border:1px solid rgba(212,168,67,.35)}
.chip.free    {background:var(--surf2);color:var(--muted);border:1px solid var(--border)}
.chip.type-feedback  {background:rgba(74,158,255,.12);color:var(--blue);border:1px solid rgba(74,158,255,.3)}
.chip.type-bug       {background:rgba(233,69,96,.12);color:var(--red);border:1px solid rgba(233,69,96,.3)}
.chip.type-suggestion{background:rgba(62,191,126,.12);color:var(--green);border:1px solid rgba(62,191,126,.3)}
.btn-sm{padding:5px 11px;border-radius:7px;font-size:11px;font-weight:700;cursor:pointer;border:none;transition:.2s;white-space:nowrap}
.btn-sm.ban   {background:rgba(233,69,96,.14);color:var(--red)}
.btn-sm.ban:hover{background:var(--red);color:#fff}
.btn-sm.unban {background:rgba(62,191,126,.14);color:var(--green)}
.btn-sm.unban:hover{background:var(--green);color:#fff}
.btn-sm.to-prem{background:rgba(212,168,67,.12);color:var(--gold);border:1px solid rgba(212,168,67,.3)}
.btn-sm.to-prem:hover{background:var(--gold);color:#0A0A0F}
.btn-sm.to-free{background:var(--surf2);color:var(--muted);border:1px solid var(--border)}
.btn-sm.to-free:hover{border-color:var(--gold);color:var(--gold)}
.btn-sm.mark-read {background:var(--surf2);color:var(--muted);border:1px solid var(--border)}
.btn-sm.mark-read:hover{border-color:var(--gold);color:var(--gold)}
.btn-sm.mark-unread{background:rgba(212,168,67,.1);color:var(--gold);border:1px solid rgba(212,168,67,.3)}
.btn-sm.mark-unread:hover{background:var(--gold);color:#0A0A0F}
.btn-sm.del  {background:rgba(233,69,96,.1);color:var(--red);border:1px solid rgba(233,69,96,.3)}
.btn-sm.del:hover{background:var(--red);color:#fff}
.btn-sm:disabled{opacity:.35;cursor:not-allowed}
.btn-icon{background:transparent;border:none;cursor:pointer;font-size:16px;padding:3px;opacity:.6;transition:.15s}
.btn-icon:hover{opacity:1}

/* ── PAGINATION ─────────────────────────────────────────── */
.pagination{display:flex;align-items:center;justify-content:flex-end;gap:8px;margin-top:14px}
.pagination span{font-size:12px;color:var(--muted)}
.btn-page{background:var(--surf2);border:1.5px solid var(--border);border-radius:7px;color:var(--text);padding:6px 14px;font-size:12px;cursor:pointer;transition:.2s}
.btn-page:hover:not(:disabled){border-color:var(--gold);color:var(--gold)}
.btn-page:disabled{opacity:.35;cursor:not-allowed}

/* ── FEEDBACK CARDS ─────────────────────────────────────── */
.fb-card{background:var(--surf);border:1.5px solid var(--border);border-radius:12px;padding:16px 18px;margin-bottom:10px;display:flex;gap:14px;align-items:flex-start;transition:.2s}
.fb-card.unread{border-left:3px solid var(--gold)}
.fb-meta{flex:1;min-width:0}
.fb-header{display:flex;align-items:center;gap:8px;margin-bottom:7px;flex-wrap:wrap}
.fb-user{font-weight:700;font-size:13px}
.fb-date{font-size:11px;color:var(--muted)}
.fb-text{font-size:13px;color:#bbb;line-height:1.6}
.fb-actions{flex-shrink:0;display:flex;flex-direction:column;gap:5px;align-items:flex-end}
.new-dot{font-size:10px;color:var(--gold);font-weight:700}

/* ── AUDIT LOG ──────────────────────────────────────────── */
.action-pill{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10px;font-weight:700;letter-spacing:.3px}
.action-login-ok  {background:rgba(62,191,126,.14);color:var(--green);border:1px solid rgba(62,191,126,.3)}
.action-login-fail{background:rgba(233,69,96,.12);color:var(--red);border:1px solid rgba(233,69,96,.3)}
.action-register  {background:rgba(74,158,255,.12);color:var(--blue);border:1px solid rgba(74,158,255,.3)}
.action-delete    {background:rgba(233,69,96,.12);color:var(--red);border:1px solid rgba(233,69,96,.3)}
.action-admin     {background:rgba(212,168,67,.12);color:var(--gold);border:1px solid rgba(212,168,67,.3)}
.action-security  {background:rgba(240,144,64,.12);color:var(--orange);border:1px solid rgba(240,144,64,.3)}
.action-default   {background:var(--surf2);color:var(--muted);border:1px solid var(--border)}

/* ── SYSTEM ─────────────────────────────────────────────── */
.status-row{display:flex;align-items:center;gap:10px;padding:12px 0;border-bottom:1px solid var(--border)}
.status-row:last-child{border-bottom:none}
.status-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.status-dot.ok{background:var(--green);box-shadow:0 0 6px rgba(62,191,126,.5)}
.status-dot.warn{background:var(--orange)}
.status-dot.err{background:var(--red)}
.status-label{flex:1;font-size:13px;color:var(--muted2)}
.status-val{font-size:13px;font-weight:700}
.metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.metric-item{background:var(--surf2);border-radius:10px;padding:12px 14px}
.metric-val{font-size:22px;font-weight:800;margin-bottom:2px}
.metric-lbl{font-size:11px;color:var(--muted)}

/* ── EMPTY / LOADING ─────────────────────────────────────── */
.empty{text-align:center;padding:48px 0;color:var(--muted);font-size:14px}
.spinner{display:inline-block;width:18px;height:18px;border:2px solid var(--border);border-top-color:var(--gold);border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-row td{text-align:center;padding:32px}
.loading-inline{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:13px}

/* ── TOASTS ─────────────────────────────────────────────── */
#toast-container{position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column-reverse;gap:8px;pointer-events:none}
.toast{padding:11px 16px;border-radius:10px;font-size:13px;font-weight:600;color:#fff;box-shadow:0 4px 24px rgba(0,0,0,.6);max-width:320px;animation:toastIn .2s ease;pointer-events:none}
.toast.success{background:var(--green)}
.toast.error{background:var(--red)}
.toast.info{background:var(--blue)}
@keyframes toastIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}

/* ── REFRESH INDICATOR ──────────────────────────────────── */
.refresh-row{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:11px;margin-top:6px}
#refresh-dot{width:7px;height:7px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:.6}50%{opacity:1}}
</style>
</head>
<body>

<!-- ═══ LOGIN ════════════════════════════════════════════════ -->
<div id="login-screen">
  <div class="login-card">
    <div class="login-logo">⚔️</div>
    <h1>Nakama Cards</h1>
    <p>Panel de administración — solo admins</p>
    <div class="field">
      <label>Usuario o Email</label>
      <input id="l-user" type="text" placeholder="tu_usuario" autocomplete="username">
    </div>
    <div class="field">
      <label>Contraseña</label>
      <input id="l-pass" type="password" placeholder="••••••••" autocomplete="current-password">
    </div>
    <button class="btn-primary" id="l-btn" onclick="doLogin()">Iniciar sesión</button>
    <div class="error-msg" id="l-err"></div>
  </div>
</div>

<!-- ═══ APP SHELL ════════════════════════════════════════════ -->
<div id="app">
  <header>
    <div class="brand">
      <span class="brand-icon">⚔️</span>
      <span class="brand-name">Nakama Cards</span>
      <span class="brand-tag">Admin</span>
    </div>
    <div class="header-right">
      <span class="admin-name" id="admin-name"></span>
      <button class="btn-logout" onclick="doLogout()">Cerrar sesión</button>
    </div>
  </header>

  <nav>
    <button class="nav-tab active" onclick="switchTab('stats',this)">📊 Resumen</button>
    <button class="nav-tab" onclick="switchTab('users',this)">👥 Usuarios</button>
    <button class="nav-tab" onclick="switchTab('tcg',this)">🃏 TCG Stats</button>
    <button class="nav-tab" onclick="switchTab('feedback',this)">
      💬 Mensajes<span class="badge" id="unread-badge" style="display:none">0</span>
    </button>
    <button class="nav-tab" onclick="switchTab('logs',this)">📋 Logs</button>
    <button class="nav-tab" onclick="switchTab('system',this)">⚙️ Sistema</button>
  </nav>

  <main>

    <!-- ════ TAB: RESUMEN ════════════════════════════════════ -->
    <div id="tab-stats" class="tab-panel active">

      <!-- Row 1: Usuarios -->
      <div class="section-title">Usuarios</div>
      <div class="stat-grid" id="stats-users-grid">
        <div class="stat-card"><div class="sc-icon">👤</div><div class="sc-val" id="s-total">—</div><div class="sc-lbl">Total usuarios</div></div>
        <div class="stat-card c-green"><div class="sc-icon">✅</div><div class="sc-val" id="s-active">—</div><div class="sc-lbl">Usuarios activos</div></div>
        <div class="stat-card c-blue"><div class="sc-icon">🆕</div><div class="sc-val" id="s-today">—</div><div class="sc-lbl">Nuevos hoy</div></div>
        <div class="stat-card c-gold"><div class="sc-icon">⭐</div><div class="sc-val" id="s-premium">—</div><div class="sc-lbl">Premium</div><div class="sc-sub" id="s-conversion">Conversión: —%</div></div>
        <div class="stat-card"><div class="sc-icon">🆓</div><div class="sc-val" id="s-free">—</div><div class="sc-lbl">Plan Free</div></div>
        <div class="stat-card c-red"><div class="sc-icon">🚫</div><div class="sc-val" id="s-banned">—</div><div class="sc-lbl">Baneados</div></div>
      </div>

      <!-- Row 2: Contenido & Mensajes -->
      <div class="section-title">Contenido</div>
      <div class="stat-grid">
        <div class="stat-card c-purple"><div class="sc-icon">🃏</div><div class="sc-val" id="s-cards">—</div><div class="sc-lbl">Cartas en colecciones</div></div>
        <div class="stat-card c-orange"><div class="sc-icon">📁</div><div class="sc-val" id="s-folders">—</div><div class="sc-lbl">Carpetas creadas</div></div>
        <div class="stat-card c-red"><div class="sc-icon">📨</div><div class="sc-val" id="s-unread">—</div><div class="sc-lbl">Mensajes sin leer</div></div>
        <div class="stat-card"><div class="sc-icon">💬</div><div class="sc-val" id="s-total-fb">—</div><div class="sc-lbl">Total mensajes</div></div>
      </div>

      <!-- Row 3: Monetización -->
      <div class="section-title">Monetización</div>
      <div class="two-col">
        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">DISTRIBUCIÓN DE PLAN</span>
          </div>
          <div id="plan-chart" class="bar-list">
            <div class="loading-inline"><span class="spinner"></span> Cargando...</div>
          </div>
        </div>
        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">MÉTRICAS PREMIUM</span>
          </div>
          <div class="metric-grid">
            <div class="metric-item">
              <div class="metric-val c-gold" id="m-conv">—</div>
              <div class="metric-lbl">Tasa de conversión</div>
            </div>
            <div class="metric-item">
              <div class="metric-val" id="m-prem-count">—</div>
              <div class="metric-lbl">Usuarios Premium</div>
            </div>
            <div class="metric-item">
              <div class="metric-val c-green" id="m-today">—</div>
              <div class="metric-lbl">Registros hoy</div>
            </div>
            <div class="metric-item">
              <div class="metric-val c-orange" id="m-banned">—</div>
              <div class="metric-lbl">Cuentas inactivas</div>
            </div>
          </div>
          <p style="color:var(--muted);font-size:10px;margin-top:12px">* Los ingresos estimados requieren integración con pasarela de pago.</p>
        </div>
      </div>

      <div class="refresh-row">
        <span id="refresh-dot"></span>
        <span id="refresh-label">Actualizando automáticamente cada 30 s.</span>
      </div>
    </div>

    <!-- ════ TAB: USUARIOS ════════════════════════════════════ -->
    <div id="tab-users" class="tab-panel">
      <div class="section-header">
        <div class="section-title" style="margin-bottom:0">Usuarios registrados</div>
        <div style="display:flex;gap:8px;align-items:center">
          <button class="btn-sm" id="reload-users-btn"
            style="background:var(--surf2);color:var(--muted);border:1.5px solid var(--border);font-size:12px;padding:6px 13px"
            onclick="loadUsers()">↻ Recargar</button>
          <input class="search-input" id="user-search" type="text" placeholder="🔍 Buscar usuario o email…" oninput="filterUsers()">
        </div>
      </div>
      <div class="filter-row" id="user-filters">
        <button class="filter-chip active" onclick="setUserFilter('all',this)">Todos</button>
        <button class="filter-chip" onclick="setUserFilter('active',this)">Activos</button>
        <button class="filter-chip" onclick="setUserFilter('inactive',this)">Inactivos</button>
        <button class="filter-chip" onclick="setUserFilter('premium',this)">Premium ⭐</button>
        <button class="filter-chip" onclick="setUserFilter('free',this)">Free</button>
        <button class="filter-chip" onclick="setUserFilter('admin',this)">Admins</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Usuario</th><th>Email</th><th>Registrado</th>
              <th>Estado</th><th>Plan</th><th>Acciones</th>
            </tr>
          </thead>
          <tbody id="users-tbody">
            <tr class="loading-row"><td colspan="7"><span class="spinner"></span></td></tr>
          </tbody>
        </table>
      </div>
      <div class="pagination">
        <button class="btn-page" id="u-prev" onclick="usersPageDelta(-1)" disabled>← Anterior</button>
        <span id="u-page-info">Página 1</span>
        <button class="btn-page" id="u-next" onclick="usersPageDelta(1)">Siguiente →</button>
      </div>
    </div>

    <!-- ════ TAB: TCG STATS ══════════════════════════════════ -->
    <div id="tab-tcg" class="tab-panel">
      <div class="section-header">
        <div class="section-title" style="margin-bottom:0">Estadísticas TCG</div>
        <button class="btn-sm" style="background:var(--surf2);color:var(--muted);border:1.5px solid var(--border)"
          onclick="loadTCG()">↻ Recargar</button>
      </div>

      <div class="two-col" style="margin-bottom:16px">
        <!-- Top Cartas -->
        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">🃏 TOP 10 CARTAS MÁS USADAS</span>
          </div>
          <div id="tcg-top-cards" class="bar-list">
            <div class="loading-inline"><span class="spinner"></span> Cargando...</div>
          </div>
        </div>
        <!-- Top Líderes -->
        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">👑 TOP 5 LÍDERES MÁS USADOS</span>
          </div>
          <div id="tcg-leaders" class="bar-list">
            <div class="loading-inline"><span class="spinner"></span> Cargando...</div>
          </div>
        </div>
      </div>

      <div class="two-col">
        <!-- Por Color -->
        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">🎨 DISTRIBUCIÓN POR COLOR</span>
          </div>
          <div id="tcg-colors" class="bar-list">
            <div class="loading-inline"><span class="spinner"></span> Cargando...</div>
          </div>
        </div>
        <!-- Por Set -->
        <div class="panel">
          <div class="panel-header">
            <span class="panel-title">📦 SETS MÁS POPULARES</span>
          </div>
          <div id="tcg-sets" class="bar-list">
            <div class="loading-inline"><span class="spinner"></span> Cargando...</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ════ TAB: MENSAJES ════════════════════════════════════ -->
    <div id="tab-feedback" class="tab-panel">
      <div class="section-header">
        <div class="section-title" style="margin-bottom:0">Mensajes y reportes</div>
      </div>
      <div class="filter-row">
        <button class="filter-chip active" onclick="setFbFilter(false,this)">Todos</button>
        <button class="filter-chip" onclick="setFbFilter(true,this)">Solo no leídos</button>
      </div>
      <div id="feedback-list"><div class="empty"><span class="spinner"></span></div></div>
      <div class="pagination">
        <button class="btn-page" id="f-prev" onclick="fbPageDelta(-1)" disabled>← Anterior</button>
        <span id="f-page-info">Página 1</span>
        <button class="btn-page" id="f-next" onclick="fbPageDelta(1)">Siguiente →</button>
      </div>
    </div>

    <!-- ════ TAB: LOGS ════════════════════════════════════════ -->
    <div id="tab-logs" class="tab-panel">
      <div class="section-header">
        <div class="section-title" style="margin-bottom:0">Registro de auditoría</div>
        <div style="display:flex;gap:8px;align-items:center">
          <input class="search-input" id="log-user-id" type="number" placeholder="Filtrar por User ID" style="width:170px" oninput="loadLogs()">
          <button class="btn-sm" style="background:var(--surf2);color:var(--muted);border:1.5px solid var(--border)" onclick="loadLogs()">↻ Recargar</button>
        </div>
      </div>
      <div class="filter-row" id="log-filters">
        <button class="filter-chip active" onclick="setLogFilter('',this)">Todos</button>
        <button class="filter-chip" onclick="setLogFilter('USER_LOGIN_SUCCESS',this)">Login OK</button>
        <button class="filter-chip" onclick="setLogFilter('USER_LOGIN_FAIL',this)">Login Fail</button>
        <button class="filter-chip" onclick="setLogFilter('USER_REGISTER',this)">Registro</button>
        <button class="filter-chip" onclick="setLogFilter('USER_DELETE',this)">Eliminación</button>
        <button class="filter-chip" onclick="setLogFilter('ADMIN_BAN_USER',this)">Admin: Ban</button>
        <button class="filter-chip" onclick="setLogFilter('ADMIN_SET_PREMIUM',this)">Admin: Premium</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Timestamp</th><th>Acción</th><th>Actor</th><th>Objetivo</th><th>IP</th><th>Resultado</th><th>Detalles</th></tr>
          </thead>
          <tbody id="logs-tbody">
            <tr class="loading-row"><td colspan="7"><span class="spinner"></span></td></tr>
          </tbody>
        </table>
      </div>
      <div class="pagination">
        <button class="btn-page" id="log-prev" onclick="logsPageDelta(-1)" disabled>← Anterior</button>
        <span id="log-page-info">Página 1</span>
        <button class="btn-page" id="log-next" onclick="logsPageDelta(1)">Siguiente →</button>
      </div>
    </div>

    <!-- ════ TAB: SISTEMA ════════════════════════════════════ -->
    <div id="tab-system" class="tab-panel">
      <div class="section-header">
        <div class="section-title" style="margin-bottom:0">Estado del sistema</div>
        <button class="btn-sm" style="background:var(--surf2);color:var(--muted);border:1.5px solid var(--border)"
          onclick="loadSystem()">↻ Actualizar</button>
      </div>

      <div class="two-col">
        <!-- Estado -->
        <div class="panel">
          <div class="panel-header"><span class="panel-title">⚡ ESTADO DE SERVICIOS</span></div>
          <div id="system-status">
            <div class="loading-inline"><span class="spinner"></span> Comprobando...</div>
          </div>
        </div>
        <!-- Actividad 24h -->
        <div class="panel">
          <div class="panel-header"><span class="panel-title">📈 ACTIVIDAD ÚLTIMAS 24 H</span></div>
          <div id="system-24h">
            <div class="loading-inline"><span class="spinner"></span> Cargando...</div>
          </div>
        </div>
      </div>

      <div style="margin-top:16px" class="panel">
        <div class="panel-header"><span class="panel-title">ℹ️ INFORMACIÓN DEL SERVIDOR</span></div>
        <div id="system-info" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-top:4px">
          <div class="loading-inline"><span class="spinner"></span> Cargando...</div>
        </div>
      </div>
    </div>

  </main>
</div>

<div id="toast-container"></div>

<script>
'use strict';

// ─── Constants ─────────────────────────────────────────────────────────────
const API = '';          // Same origin
const USERS_PER_PAGE = 50;
const LOGS_PER_PAGE  = 50;
const REFRESH_MS     = 30_000;

// ─── Color map for TCG ──────────────────────────────────────────────────────
const COLOR_MAP = {
  'Red':    '#E74C3C', 'Rojo':   '#E74C3C',
  'Blue':   '#3498DB', 'Azul':   '#3498DB',
  'Green':  '#2ECC71', 'Verde':  '#2ECC71',
  'Purple': '#9B59B6', 'Morado': '#9B59B6',
  'Black':  '#95A5A6', 'Negro':  '#95A5A6',
  'Yellow': '#F1C40F', 'Amarillo':'#F1C40F',
  'Multi':  '#E67E22', 'Multicolor':'#E67E22',
};
const colorOf = c => COLOR_MAP[c] || '#D4A843';

// ─── State ──────────────────────────────────────────────────────────────────
let TOKEN = localStorage.getItem('admin_token') || '';
let usersData = [], usersFiltered = [], userFilter = 'all', usersPage_ = 1;
let fbPage_ = 1, fbUnreadOnly = false;
let logsPage_ = 1, logActionFilter = '', logUserId = '';
let refreshTimer = null;

// ─── Boot ───────────────────────────────────────────────────────────────────
(async () => {
  if (TOKEN) { const ok = await tryShowApp(); if (!ok) clearToken(); }
})();

// ─── Auth ───────────────────────────────────────────────────────────────────
async function doLogin() {
  const user = $('l-user').value.trim();
  const pass = $('l-pass').value;
  const btn  = $('l-btn');
  if (!user || !pass) { showErr('Completa todos los campos.'); return; }
  btn.disabled = true; btn.textContent = 'Entrando…';
  $('l-err').style.display = 'none';
  try {
    const res = await apiFetch('/auth/login', 'POST', {email_or_username:user, password:pass});
    if (!res.ok) { const d = await res.json(); showErr(d.detail||'Credenciales incorrectas.'); return; }
    const data = await res.json();
    TOKEN = data.access_token;
    const check = await apiFetch('/admin/stats');
    if (check.status === 403) { showErr('Sin permisos de administrador.'); TOKEN=''; return; }
    if (!check.ok) { showErr('Error al verificar permisos.'); TOKEN=''; return; }
    localStorage.setItem('admin_token', TOKEN);
    const adminUser = data.user;
    if (adminUser) $('admin-name').textContent = adminUser.username || '';
    showApp();
  } catch { showErr('No se pudo conectar al servidor.'); }
  finally { btn.disabled=false; btn.textContent='Iniciar sesión'; }
}

async function tryShowApp() {
  try {
    const r = await apiFetch('/admin/stats');
    if (!r.ok) return false;
    showApp(); return true;
  } catch { return false; }
}

function doLogout() {
  clearToken();
  clearInterval(refreshTimer);
  $('app').style.display = 'none';
  $('login-screen').style.display = 'flex';
}

function clearToken() { TOKEN=''; localStorage.removeItem('admin_token'); }
function showErr(m) { const e=$('l-err'); e.textContent=m; e.style.display='block'; }

function showApp() {
  $('login-screen').style.display = 'none';
  $('app').style.display = 'flex';
  loadAll();
  refreshTimer = setInterval(loadAll, REFRESH_MS);
}

function loadAll() {
  loadStats();
  const badge = $('unread-badge');
  apiFetch('/admin/stats').then(r=>r.json()).then(d=>{
    if (d.unread_feedback > 0) { badge.textContent=d.unread_feedback; badge.style.display=''; }
    else badge.style.display='none';
  }).catch(()=>{});
}

// ─── Tabs ───────────────────────────────────────────────────────────────────
function switchTab(name, el) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
  $('tab-'+name).classList.add('active');
  el.classList.add('active');
  if (name === 'users')    loadUsers();
  if (name === 'tcg')      loadTCG();
  if (name === 'feedback') { fbPage_=1; loadFeedback(); }
  if (name === 'logs')     { logsPage_=1; loadLogs(); }
  if (name === 'system')   loadSystem();
}

// ─── Stats ──────────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const r = await apiFetch('/admin/stats');
    if (r.status===401) { doLogout(); return; }
    const d = await r.json();

    setText('s-total',   fmt(d.total_users));
    setText('s-active',  fmt(d.active_users));
    setText('s-today',   fmt(d.new_users_today));
    setText('s-premium', fmt(d.premium_users));
    setText('s-free',    fmt(d.free_users));
    setText('s-banned',  fmt(d.banned_users));
    setText('s-conversion', `Conversión: ${d.premium_conversion_rate}%`);
    setText('s-cards',   fmt(d.total_cards_registered));
    setText('s-folders', fmt(d.total_folders));
    setText('s-unread',  fmt(d.unread_feedback));
    setText('s-total-fb',fmt(d.total_feedback));

    // Métricas premium
    setText('m-conv',        `${d.premium_conversion_rate}%`);
    setText('m-prem-count',  fmt(d.premium_users));
    setText('m-today',       `+${fmt(d.new_users_today)}`);
    setText('m-banned',      fmt(d.banned_users));

    // Gráfico distribución plan
    if (d.total_users > 0) {
      const pPct = Math.round(d.premium_users/d.total_users*100);
      const fPct = 100 - pPct;
      $('plan-chart').innerHTML = `
        ${barItem('⭐ Premium', d.premium_users, d.total_users, '#D4A843')}
        ${barItem('🆓 Free',    d.free_users,    d.total_users, '#4A9EFF')}
        ${barItem('🚫 Inactivos',d.banned_users, d.total_users, '#E94560')}
      `;
    }

    $('refresh-label').textContent = 'Actualizado: ' + new Date().toLocaleTimeString('es-CL');
  } catch {}
}

// ─── TCG Stats ──────────────────────────────────────────────────────────────
async function loadTCG() {
  ['tcg-top-cards','tcg-leaders','tcg-colors','tcg-sets'].forEach(id =>
    $(id).innerHTML = '<div class="loading-inline"><span class="spinner"></span> Cargando...</div>'
  );
  try {
    const r = await apiFetch('/admin/tcg-stats');
    if (r.status===401) { doLogout(); return; }
    if (!r.ok) { $(('tcg-top-cards')).innerHTML = '<div class="empty" style="color:var(--red)">Error al cargar.</div>'; return; }
    const d = await r.json();

    // Top Cards
    if (d.top_cards?.length) {
      const max = d.top_cards[0].total || 1;
      $('tcg-top-cards').innerHTML = d.top_cards.map(c => `
        <div class="bar-item">
          <span class="bar-label wide" title="${esc(c.card_set_code)}">${esc(c.card_set_code)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.round(c.total/max*100)}%;background:${colorOf(c.color||'')}"></div></div>
          <span class="bar-val">${fmt(c.total)}</span>
        </div>
      `).join('');
    } else { $('tcg-top-cards').innerHTML = '<div class="empty" style="padding:20px 0">Sin datos</div>'; }

    // Leaders
    if (d.top_leaders?.length) {
      const max = d.top_leaders[0].total || 1;
      $('tcg-leaders').innerHTML = d.top_leaders.map(c => `
        <div class="bar-item">
          <span class="bar-label wide" title="${esc(c.name||c.card_set_code)}">${esc(c.name||c.card_set_code)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.round(c.total/max*100)}%;background:${colorOf(c.color||'')}"></div></div>
          <span class="bar-val">${fmt(c.total)}</span>
        </div>
      `).join('');
    } else { $('tcg-leaders').innerHTML = '<div class="empty" style="padding:20px 0">Sin datos</div>'; }

    // Colors
    if (d.by_color?.length) {
      const max = d.by_color[0].total || 1;
      $('tcg-colors').innerHTML = d.by_color.map(c => `
        <div class="bar-item">
          <span class="bar-label" style="display:flex;align-items:center;gap:6px">
            <span class="color-dot" style="background:${colorOf(c.color)}"></span>
            ${esc(c.color)}
          </span>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.round(c.total/max*100)}%;background:${colorOf(c.color)}"></div></div>
          <span class="bar-val">${fmt(c.total)}</span>
        </div>
      `).join('');
    } else { $('tcg-colors').innerHTML = '<div class="empty" style="padding:20px 0">Sin datos</div>'; }

    // Sets
    if (d.by_set?.length) {
      const max = d.by_set[0].total || 1;
      $('tcg-sets').innerHTML = d.by_set.map(s => `
        <div class="bar-item">
          <span class="bar-label">${esc(s.set_prefix)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.round(s.total/max*100)}%;background:var(--purple)"></div></div>
          <span class="bar-val">${fmt(s.total)}</span>
        </div>
      `).join('');
    } else { $('tcg-sets').innerHTML = '<div class="empty" style="padding:20px 0">Sin datos</div>'; }

  } catch(e) {
    ['tcg-top-cards','tcg-leaders','tcg-colors','tcg-sets'].forEach(id =>
      $(id).innerHTML = `<div class="empty" style="color:var(--red);padding:16px 0">Error: ${e.message}</div>`
    );
  }
}

// ─── Users ──────────────────────────────────────────────────────────────────
let userFilterFn = u => true;

async function loadUsers() {
  const btn = $('reload-users-btn');
  if (btn) { btn.disabled=true; btn.textContent='…'; }
  $('users-tbody').innerHTML = '<tr class="loading-row"><td colspan="7"><span class="spinner"></span></td></tr>';
  try {
    const r = await apiFetch('/admin/users?limit=500');
    if (r.status===401) { doLogout(); return; }
    if (!r.ok) throw new Error('HTTP '+r.status);
    usersData = await r.json();
    applyUserFilter(userFilter);
  } catch(e) {
    $('users-tbody').innerHTML = `<tr class="loading-row"><td colspan="7" style="color:var(--red)">Error: ${e.message}</td></tr>`;
  } finally {
    if (btn) { btn.disabled=false; btn.textContent='↻ Recargar'; }
  }
}

function setUserFilter(filter, el) {
  userFilter = filter;
  document.querySelectorAll('#user-filters .filter-chip').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  applyUserFilter(filter);
}

function applyUserFilter(filter) {
  const q = ($('user-search')?.value||'').toLowerCase();
  usersFiltered = usersData.filter(u => {
    const matchQ = !q || u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
    let matchF = true;
    if (filter==='active')   matchF = u.is_active;
    if (filter==='inactive') matchF = !u.is_active;
    if (filter==='premium')  matchF = u.is_premium;
    if (filter==='free')     matchF = !u.is_premium && u.is_active;
    if (filter==='admin')    matchF = u.is_admin;
    return matchQ && matchF;
  });
  usersPage_ = 1;
  renderUsers();
}

function filterUsers() { applyUserFilter(userFilter); }

function usersPageDelta(d) {
  const max = Math.ceil(usersFiltered.length/USERS_PER_PAGE)||1;
  usersPage_ = Math.max(1, Math.min(usersPage_+d, max));
  renderUsers();
}

function renderUsers() {
  const tbody = $('users-tbody');
  const start = (usersPage_-1)*USERS_PER_PAGE;
  const slice = usersFiltered.slice(start, start+USERS_PER_PAGE);
  const maxPage = Math.ceil(usersFiltered.length/USERS_PER_PAGE)||1;
  $('u-page-info').textContent = `Página ${usersPage_} de ${maxPage} · ${usersFiltered.length} usuarios`;
  $('u-prev').disabled = usersPage_<=1;
  $('u-next').disabled = usersPage_>=maxPage;
  if (!slice.length) { tbody.innerHTML='<tr class="loading-row"><td colspan="7" class="empty">Sin resultados.</td></tr>'; return; }
  tbody.innerHTML = slice.map(u => `
    <tr id="ur-${u.id}">
      <td style="color:var(--muted);font-size:12px">${u.id}</td>
      <td>
        <strong>${esc(u.username)}</strong>
        ${u.is_admin?'<span class="chip admin" style="margin-left:5px">admin</span>':''}
      </td>
      <td style="color:var(--muted)">${esc(u.email)}</td>
      <td style="color:var(--muted);font-size:12px">${fmtDate(u.created_at)}</td>
      <td><span class="chip ${u.is_active?'active':'inactive'}">${u.is_active?'Activo':'Inactivo'}</span></td>
      <td>
        ${u.is_premium
          ?'<span class="chip premium">⭐ Premium</span>'
          :'<span class="chip free">Free</span>'}
      </td>
      <td style="display:flex;gap:6px;flex-wrap:wrap">
        ${u.is_admin ? '<span style="color:var(--muted);font-size:11px">—</span>' : `
          ${u.is_active
            ?`<button class="btn-sm ban"   onclick="toggleUser(${u.id},false,this)">Banear</button>`
            :`<button class="btn-sm unban" onclick="toggleUser(${u.id},true,this)">Activar</button>`}
          ${u.is_premium
            ?`<button class="btn-sm to-free"  onclick="setPlan(${u.id},false,this)">→ Free</button>`
            :`<button class="btn-sm to-prem"  onclick="setPlan(${u.id},true,this)">→ Premium</button>`}
        `}
      </td>
    </tr>`).join('');
}

async function toggleUser(id, active, btn) {
  const row = $('ur-'+id);
  const btns = row ? row.querySelectorAll('button') : [btn];
  btns.forEach(b=>b.disabled=true);
  try {
    const r = await apiFetch(`/admin/users/${id}`, 'PATCH', {is_active:active});
    if (r.status===401) { doLogout(); return; }
    if (!r.ok) { const e=await r.json().catch(()=>({})); throw new Error(e.detail||'Error'); }
    const u = usersData.find(u=>u.id===id);
    if (u) u.is_active = active;
    applyUserFilter(userFilter);
    loadStats();
    showToast(active?'✓ Cuenta activada':'✓ Cuenta desactivada');
  } catch(e) { showToast(e.message,'error'); btns.forEach(b=>b.disabled=false); }
}

async function setPlan(id, isPremium, btn) {
  const row = $('ur-'+id);
  const btns = row ? row.querySelectorAll('button') : [btn];
  btns.forEach(b=>b.disabled=true);
  try {
    const r = await apiFetch(`/admin/users/${id}/plan`, 'PATCH', {is_premium:isPremium});
    if (r.status===401) { doLogout(); return; }
    if (!r.ok) { const e=await r.json().catch(()=>({})); throw new Error(e.detail||'Error'); }
    const u = usersData.find(u=>u.id===id);
    if (u) u.is_premium = isPremium;
    applyUserFilter(userFilter);
    loadStats();
    showToast(isPremium?'⭐ Premium activado':'✓ Cambiado a Free');
  } catch(e) { showToast(e.message,'error'); btns.forEach(b=>b.disabled=false); }
}

// ─── Feedback ───────────────────────────────────────────────────────────────
async function loadFeedback() {
  $('feedback-list').innerHTML = '<div class="empty"><span class="spinner"></span></div>';
  try {
    const url = `/admin/feedback?limit=20&page=${fbPage_}${fbUnreadOnly?'&unread_only=true':''}`;
    const r = await apiFetch(url);
    if (r.status===401) { doLogout(); return; }
    renderFeedback(await r.json());
  } catch { $('feedback-list').innerHTML='<div class="empty" style="color:var(--red)">Error al cargar.</div>'; }
}

function setFbFilter(unreadOnly, btn) {
  fbUnreadOnly=unreadOnly; fbPage_=1;
  document.querySelectorAll('#tab-feedback .filter-chip').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  loadFeedback();
}

function fbPageDelta(d) { fbPage_=Math.max(1,fbPage_+d); loadFeedback(); }

function renderFeedback(items) {
  $('f-page-info').textContent = `Página ${fbPage_}`;
  $('f-prev').disabled = fbPage_<=1;
  $('f-next').disabled = items.length<20;
  if (!items.length) { $('feedback-list').innerHTML='<div class="empty">No hay mensajes.</div>'; return; }
  const typeLbl = {feedback:'💬 Comentario',bug:'🐛 Error/Bug',suggestion:'💡 Sugerencia'};
  const typeCls = {feedback:'type-feedback',bug:'type-bug',suggestion:'type-suggestion'};
  $('feedback-list').innerHTML = items.map(fb=>`
    <div class="fb-card ${fb.is_read?'':'unread'}" id="fb-${fb.id}">
      <div class="fb-meta">
        <div class="fb-header">
          <span class="chip ${typeCls[fb.type]||'type-feedback'}">${typeLbl[fb.type]||fb.type}</span>
          <span class="fb-user">${fb.username?esc(fb.username):'<em style="color:var(--muted)">anónimo</em>'}</span>
          <span class="fb-date">${fmtDateFull(fb.created_at)}</span>
          ${!fb.is_read?'<span class="new-dot">● Nuevo</span>':''}
        </div>
        <div class="fb-text">${esc(fb.message)}</div>
      </div>
      <div class="fb-actions">
        ${!fb.is_read
          ?`<button class="btn-sm mark-read"   onclick="markRead(${fb.id},this)">Marcar leído</button>`
          :`<button class="btn-sm mark-unread" onclick="markUnread(${fb.id},this)">No leído</button>`}
        <button class="btn-sm del" onclick="delFeedback(${fb.id},this)">Eliminar</button>
      </div>
    </div>`).join('');
}

async function markRead(id, btn) {
  btn.disabled=true;
  const r = await apiFetch(`/admin/feedback/${id}/read`,'PATCH');
  if (r.ok) { loadFeedback(); loadStats(); } else btn.disabled=false;
}

async function markUnread(id, btn) {
  btn.disabled=true;
  const r = await apiFetch(`/admin/feedback/${id}/unread`,'PATCH');
  if (r.ok) { loadFeedback(); loadStats(); } else btn.disabled=false;
}

async function delFeedback(id, btn) {
  if (!confirm('¿Eliminar este mensaje? No se puede deshacer.')) return;
  btn.disabled=true;
  const r = await apiFetch(`/admin/feedback/${id}`,'DELETE');
  if (r.ok) {
    const card=$('fb-'+id);
    if (card) { card.style.opacity='0'; card.style.transition='opacity .2s'; setTimeout(()=>card.remove(),220); }
    loadStats();
  } else { btn.disabled=false; showToast('Error al eliminar.','error'); }
}

// ─── Audit Logs ─────────────────────────────────────────────────────────────
async function loadLogs() {
  $('logs-tbody').innerHTML='<tr class="loading-row"><td colspan="7"><span class="spinner"></span></td></tr>';
  try {
    let url = `/admin/audit-logs?limit=${LOGS_PER_PAGE}&page=${logsPage_}`;
    if (logActionFilter) url += `&action=${encodeURIComponent(logActionFilter)}`;
    const uid = $('log-user-id')?.value;
    if (uid) url += `&user_id=${uid}`;
    const r = await apiFetch(url);
    if (r.status===401) { doLogout(); return; }
    const rows = await r.json();
    renderLogs(rows);
  } catch(e) {
    $('logs-tbody').innerHTML=`<tr class="loading-row"><td colspan="7" style="color:var(--red)">Error: ${e.message}</td></tr>`;
  }
}

function setLogFilter(action, btn) {
  logActionFilter=action; logsPage_=1;
  document.querySelectorAll('#log-filters .filter-chip').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  loadLogs();
}

function logsPageDelta(d) { logsPage_=Math.max(1,logsPage_+d); loadLogs(); }

function renderLogs(rows) {
  $('log-page-info').textContent=`Página ${logsPage_}`;
  $('log-prev').disabled=logsPage_<=1;
  $('log-next').disabled=rows.length<LOGS_PER_PAGE;
  if (!rows.length) { $('logs-tbody').innerHTML='<tr class="loading-row"><td colspan="7" class="empty">Sin registros.</td></tr>'; return; }

  const pill = action => {
    const a = action||'';
    if (a==='USER_LOGIN_SUCCESS') return `<span class="action-pill action-login-ok">${a}</span>`;
    if (a.includes('FAIL')||a.includes('LOCKED')) return `<span class="action-pill action-login-fail">${a}</span>`;
    if (a==='USER_REGISTER') return `<span class="action-pill action-register">${a}</span>`;
    if (a==='USER_DELETE')   return `<span class="action-pill action-delete">${a}</span>`;
    if (a.startsWith('ADMIN')) return `<span class="action-pill action-admin">${a}</span>`;
    if (a==='RATE_LIMIT_HIT') return `<span class="action-pill action-security">${a}</span>`;
    return `<span class="action-pill action-default">${a}</span>`;
  };
  const okIcon = ok => ok ? '<span style="color:var(--green)">✓</span>' : '<span style="color:var(--red)">✗</span>';

  $('logs-tbody').innerHTML = rows.map(r=>`
    <tr>
      <td style="font-size:11px;color:var(--muted);white-space:nowrap">${fmtDateFull(r.timestamp)}</td>
      <td>${pill(r.action)}</td>
      <td style="font-size:12px;color:var(--muted2)">${r.actor_user_id||'—'}</td>
      <td style="font-size:12px;color:var(--muted2)">${r.target_user_id||'—'}</td>
      <td style="font-size:11px;color:var(--muted);font-family:monospace">${esc(r.ip_address||'—')}</td>
      <td>${okIcon(r.success)}</td>
      <td style="font-size:11px;color:var(--muted);max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
          title="${esc(r.details||'')}">${esc(r.details||'—')}</td>
    </tr>`).join('');
}

// ─── System ─────────────────────────────────────────────────────────────────
async function loadSystem() {
  $('system-status').innerHTML='<div class="loading-inline"><span class="spinner"></span> Comprobando...</div>';
  $('system-24h').innerHTML='<div class="loading-inline"><span class="spinner"></span> Cargando...</div>';
  $('system-info').innerHTML='<div class="loading-inline"><span class="spinner"></span> Cargando...</div>';

  const t0 = performance.now();
  try {
    const r = await apiFetch('/admin/system');
    const latency = Math.round(performance.now()-t0);
    if (r.status===401) { doLogout(); return; }
    if (!r.ok) throw new Error('HTTP '+r.status);
    const d = await r.json();

    const statusDot = cls => `<span class="status-dot ${cls}"></span>`;
    const latCls = latency<200?'ok':latency<800?'warn':'err';

    $('system-status').innerHTML = `
      <div class="status-row">
        ${statusDot('ok')}<span class="status-label">API Server</span>
        <span class="status-val" style="color:var(--green)">Operacional</span>
      </div>
      <div class="status-row">
        ${statusDot('ok')}<span class="status-label">Base de datos</span>
        <span class="status-val" style="color:var(--green)">Conectada</span>
      </div>
      <div class="status-row">
        ${statusDot(latCls)}<span class="status-label">Latencia API</span>
        <span class="status-val" style="color:var(--${latCls==='ok'?'green':latCls==='warn'?'orange':'red'})">${latency} ms</span>
      </div>
    `;

    const h24 = d.last_24h || {};
    $('system-24h').innerHTML = `
      <div class="status-row">
        <span class="status-label">🔐 Logins fallidos</span>
        <span class="status-val" style="color:${h24.login_failures>50?'var(--red)':'var(--muted2)'}">${fmt(h24.login_failures||0)}</span>
      </div>
      <div class="status-row">
        <span class="status-label">🔒 Bloqueos por intentos</span>
        <span class="status-val" style="color:${h24.lockouts>10?'var(--red)':'var(--muted2)'}">${fmt(h24.lockouts||0)}</span>
      </div>
      <div class="status-row">
        <span class="status-label">⚡ Rate limit alcanzado</span>
        <span class="status-val" style="color:${h24.rate_limit_hits>20?'var(--orange)':'var(--muted2)'}">${fmt(h24.rate_limit_hits||0)}</span>
      </div>
      <div class="status-row">
        <span class="status-label">🆕 Registros nuevos</span>
        <span class="status-val" style="color:var(--green)">${fmt(h24.registrations||0)}</span>
      </div>
      <div class="status-row">
        <span class="status-label">🗑️ Cuentas eliminadas</span>
        <span class="status-val" style="color:var(--muted2)">${fmt(h24.account_deletions||0)}</span>
      </div>
    `;

    const ts = d.server_timestamp ? new Date(d.server_timestamp).toLocaleString('es-CL') : '—';
    $('system-info').innerHTML = `
      <div class="metric-item">
        <div class="metric-val c-green" style="font-size:14px">● ${esc(d.status||'operational')}</div>
        <div class="metric-lbl">Estado del servidor</div>
      </div>
      <div class="metric-item">
        <div class="metric-val" style="font-size:14px">${latency} ms</div>
        <div class="metric-lbl">Latencia API</div>
      </div>
      <div class="metric-item" style="grid-column:1/-1">
        <div class="metric-val" style="font-size:12px;font-weight:600">${ts}</div>
        <div class="metric-lbl">Hora del servidor (UTC)</div>
      </div>
    `;
  } catch(e) {
    $('system-status').innerHTML=`<div class="empty" style="color:var(--red);padding:16px 0">Error: ${e.message}</div>`;
    $('system-24h').innerHTML='';
    $('system-info').innerHTML='';
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function apiFetch(url, method='GET', body=null) {
  const opts = { method, headers:{ 'Authorization':'Bearer '+TOKEN } };
  if (body) { opts.headers['Content-Type']='application/json'; opts.body=JSON.stringify(body); }
  return fetch(API+url, opts);
}

function barItem(label, val, total, color) {
  const pct = total>0 ? Math.round(val/total*100) : 0;
  return `<div class="bar-item">
    <span class="bar-label" style="width:110px">${esc(label)}</span>
    <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div>
    <span class="bar-val">${fmt(val)} <span style="color:var(--muted);font-size:10px">${pct}%</span></span>
  </div>`;
}

function $(id) { return document.getElementById(id); }
function setText(id, val) { const e=$(id); if (e) e.textContent=val; }
function fmt(n) { return (n??0).toLocaleString('es-CL'); }
function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'});
}
function fmtDateFull(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('es-CL',{day:'2-digit',month:'short',year:'numeric'})
       + ' ' + d.toLocaleTimeString('es-CL',{hour:'2-digit',minute:'2-digit'});
}

function showToast(msg, type='success') {
  const c = $('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => {
    t.style.transition = 'opacity .25s';
    t.style.opacity = '0';
    setTimeout(() => t.remove(), 260);
  }, 3000);
}

// ─── Keyboard ────────────────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.target.id==='l-pass' && e.key==='Enter') doLogin();
  if (e.target.id==='l-user' && e.key==='Enter') $('l-pass').focus();
});
</script>
</body>
</html>"""


@router.get("/admin", include_in_schema=False)
async def admin_panel():
    return HTMLResponse(_HTML)

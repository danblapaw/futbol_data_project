"""
PASO 7 — Generar Explorador HTML completo desde futbol.db
===========================================================
Lee tu base de datos y genera un HTML interactivo con:
  - Lista de todos los equipos con buscador
  - Estadísticas de cada equipo por temporada
  - Listado de todos los partidos con filtros
  - Modal de detalle al pinchar en cada partido
  - Tabla de ligas por temporada

Ejecutar:
    python scripts/07_generar_explorador.py

Resultado:
    data_clean/explorador.html  ← abre en Chrome
"""

import sqlite3, json, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "db", "futbol.db")
OUT_PATH = os.path.join(BASE_DIR, "data_clean", "explorador.html")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def extraer(db):
    print(f"📂 Leyendo {db}...")
    with sqlite3.connect(db) as conn:

        matches_raw = conn.execute("""
            SELECT id,fecha,liga,temporada,
                   equipo_local,equipo_visitante,
                   goles_local,goles_visitante,
                   corners_local,corners_visitante,
                   total_goles,total_corners,
                   ambos_marcan,over_2_5
            FROM partidos ORDER BY fecha DESC
        """).fetchall()
        matches = [{"id":r[0],"fecha":r[1],"liga":r[2],"temporada":r[3],
                    "local":r[4],"visit":r[5],"gl":r[6],"gv":r[7],
                    "cl":r[8],"cv":r[9],"tg":r[10],"tc":r[11],
                    "btts":r[12],"ov25":r[13]} for r in matches_raw]

        teams_raw = conn.execute("""
            SELECT equipo,liga,
                SUM(n) p,
                ROUND(SUM(gf)*1.0/SUM(n),2) mgf,
                ROUND(SUM(gc)*1.0/SUM(n),2) mgc,
                ROUND(SUM(ov)*100.0/SUM(n),1) ov25,
                ROUND(SUM(btts)*100.0/SUM(n),1) btts,
                ROUND(SUM(corn)*1.0/SUM(n),1) mcorn,
                SUM(wins) w, SUM(draws) d, SUM(losses) l
            FROM (
                SELECT equipo_local equipo,liga,COUNT(*) n,
                    SUM(goles_local) gf,SUM(goles_visitante) gc,
                    SUM(over_2_5) ov,SUM(ambos_marcan) btts,SUM(corners_local) corn,
                    SUM(CASE WHEN goles_local>goles_visitante THEN 1 ELSE 0 END) wins,
                    SUM(CASE WHEN goles_local=goles_visitante THEN 1 ELSE 0 END) draws,
                    SUM(CASE WHEN goles_local<goles_visitante THEN 1 ELSE 0 END) losses
                FROM partidos GROUP BY equipo_local,liga
                UNION ALL
                SELECT equipo_visitante,liga,COUNT(*),
                    SUM(goles_visitante),SUM(goles_local),
                    SUM(over_2_5),SUM(ambos_marcan),SUM(corners_visitante),
                    SUM(CASE WHEN goles_visitante>goles_local THEN 1 ELSE 0 END),
                    SUM(CASE WHEN goles_local=goles_visitante THEN 1 ELSE 0 END),
                    SUM(CASE WHEN goles_visitante<goles_local THEN 1 ELSE 0 END)
                FROM partidos GROUP BY equipo_visitante,liga
            ) GROUP BY equipo,liga ORDER BY liga,equipo
        """).fetchall()
        teams = [{"name":r[0],"liga":r[1],"p":r[2],"mgf":r[3],"mgc":r[4],
                  "ov25":r[5],"btts":r[6],"mcorn":r[7],"w":r[8],"d":r[9],"l":r[10]}
                 for r in teams_raw]

        lt_raw = conn.execute("""
            SELECT liga,temporada,COUNT(*) p,
                ROUND(AVG(total_goles),2) goles,
                ROUND(AVG(over_2_5)*100,1) ov25,
                ROUND(AVG(ambos_marcan)*100,1) btts,
                ROUND(AVG(total_corners),1) corners,
                ROUND(AVG(CASE WHEN goles_local>goles_visitante THEN 1.0 ELSE 0 END)*100,1) local,
                ROUND(AVG(CASE WHEN goles_local=goles_visitante THEN 1.0 ELSE 0 END)*100,1) empate,
                ROUND(AVG(CASE WHEN goles_local<goles_visitante THEN 1.0 ELSE 0 END)*100,1) visit
            FROM partidos GROUP BY liga,temporada ORDER BY liga,temporada
        """).fetchall()
        lt_stats = [{"liga":r[0],"temp":r[1],"p":r[2],"goles":r[3],
                     "ov25":r[4],"btts":r[5],"corners":r[6],
                     "local":r[7],"empate":r[8],"visit":r[9]} for r in lt_raw]

    print(f"✅ {len(matches):,} partidos | {len(teams)} equipos | {len(lt_stats)} liga-temporadas")
    return {"matches": matches, "teams": teams, "lt_stats": lt_stats}


def generar_html(data):
    data_js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    # Read the template HTML (the explorer template)
    # The actual HTML is embedded below as a Python string
    return EXPLORER_TEMPLATE.replace('__DATA_PLACEHOLDER__', data_js)


# ── The full HTML template is in football_explorer.html at project root.
# ── We re-generate it inline here so this script is fully self-contained.
EXPLORER_TEMPLATE = open(
    os.path.join(BASE_DIR, "football_explorer.html"), encoding="utf-8"
).read() if os.path.exists(
    os.path.join(BASE_DIR, "football_explorer.html")
) else None


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró: {DB_PATH}")
        print("   Ejecuta primero los scripts 01 al 04.")
        return

    data    = extraer(DB_PATH)
    data_js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    # We regenerate directly instead of using template replacement
    # to avoid any fragile string matching
    generate_standalone(data_js)


def generate_standalone(data_js):
    """Generates the complete self-contained HTML with data injected."""
    
    html = '''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Football Explorer</title>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#07090d;--bg2:#0c1118;--bg3:#111820;--card:#0f1820;--card2:#131f2a;
  --border:#1a2a38;--border2:#243447;
  --green:#00e676;--green2:#00c853;--gdim:rgba(0,230,118,0.09);--gglow:rgba(0,230,118,0.2);
  --cyan:#29d9f5;--amber:#ffb300;--red:#ff5252;
  --text:#ddeaf5;--text2:#7a9bb5;--text3:#3d5870;
  --fh:"Barlow Condensed",sans-serif;--fb:"Barlow",sans-serif;--fm:"JetBrains Mono",monospace;
}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--text);font-family:var(--fb);display:flex;flex-direction:column}
#topbar{flex-shrink:0;height:54px;padding:0 24px;border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,rgba(0,230,118,.04) 0%,transparent 100%);
  display:flex;align-items:center;gap:18px;z-index:100}
.logo-icon{width:34px;height:34px;background:var(--green);border-radius:7px;
  display:flex;align-items:center;justify-content:center;font-size:17px;
  box-shadow:0 0 18px var(--gglow);flex-shrink:0}
#topbar h1{font-family:var(--fh);font-size:20px;font-weight:900;letter-spacing:.07em;
  text-transform:uppercase;color:#fff;white-space:nowrap}
#topbar h1 span{color:var(--green)}
.tpills{display:flex;gap:6px;flex-wrap:wrap}
.tpill{font-family:var(--fm);font-size:10px;padding:4px 10px;border-radius:20px;
  border:1px solid var(--border2);color:var(--text2);background:var(--card);letter-spacing:.03em}
.tpill.g{border-color:rgba(0,230,118,.35);color:var(--green);background:var(--gdim)}
#layout{flex:1;display:flex;overflow:hidden}
#sidebar{width:260px;flex-shrink:0;border-right:1px solid var(--border);
  display:flex;flex-direction:column;overflow:hidden;background:var(--bg2)}
#content{flex:1;overflow-y:auto;padding:24px 28px 40px}
#search-wrap{padding:12px 14px;border-bottom:1px solid var(--border);flex-shrink:0}
#search{width:100%;padding:8px 12px;background:var(--card);border:1px solid var(--border2);
  border-radius:7px;color:var(--text);font-family:var(--fm);font-size:12px;outline:none;transition:border-color .2s}
#search:focus{border-color:rgba(0,230,118,.5);box-shadow:0 0 0 3px rgba(0,230,118,.08)}
#search::placeholder{color:var(--text3)}
#nav-list{flex:1;overflow-y:auto;padding-bottom:16px}
#nav-list::-webkit-scrollbar{width:4px}
#nav-list::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px}
.nav-group-label{padding:10px 14px 4px;font-family:var(--fh);font-size:10px;font-weight:700;
  letter-spacing:.12em;text-transform:uppercase;color:var(--text3);
  border-top:1px solid var(--border);margin-top:4px}
.nav-group-label:first-child{border-top:none;margin-top:0}
.nav-item{display:flex;align-items:center;gap:8px;padding:7px 14px;cursor:pointer;
  transition:background .15s;border-left:2px solid transparent}
.nav-item:hover{background:rgba(0,230,118,.04);border-left-color:rgba(0,230,118,.3)}
.nav-item.active{background:var(--gdim);border-left-color:var(--green)}
.ni-name{font-family:var(--fh);font-size:13px;font-weight:600;color:var(--text);
  flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nav-item.active .ni-name{color:var(--green)}
.ni-badge{font-family:var(--fm);font-size:9px;color:var(--text3);flex-shrink:0}
.panel{display:none}.panel.active{display:block}
.page-hdr{margin-bottom:22px}
.page-hdr h2{font-family:var(--fh);font-size:28px;font-weight:900;letter-spacing:.04em;color:#fff;line-height:1}
.page-hdr .sub{font-family:var(--fm);font-size:11px;color:var(--text3);margin-top:5px;letter-spacing:.04em}
.league-tag{display:inline-block;font-family:var(--fh);font-size:11px;font-weight:700;
  letter-spacing:.1em;text-transform:uppercase;padding:3px 10px;border-radius:20px;
  border:1px solid var(--border2);color:var(--text2);background:var(--card);margin-bottom:8px}
.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:22px}
.stat-grid-5{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:22px}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:9px;
  padding:16px 18px;transition:border-color .2s,transform .15s}
.stat-card:hover{border-color:var(--border2);transform:translateY(-1px)}
.sc-val{font-family:var(--fh);font-size:34px;font-weight:900;line-height:1;color:#fff}
.sc-val .u{font-size:16px;color:var(--green);font-weight:700}
.sc-val .p{font-size:18px;color:var(--text2)}
.sc-label{font-family:var(--fh);font-size:11px;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;color:var(--text2);margin-top:4px}
.sc-sub{font-family:var(--fm);font-size:9px;color:var(--text3);margin-top:3px}
.wdl-wrap{margin-bottom:22px}
.wdl-label{font-family:var(--fh);font-size:10px;font-weight:700;letter-spacing:.15em;
  text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.wdl-bar{display:flex;height:36px;border-radius:7px;overflow:hidden}
.wdl-seg{display:flex;align-items:center;justify-content:center;
  font-family:var(--fh);font-size:12px;font-weight:800}
.wdl-seg.w{background:var(--green);color:#07090d}
.wdl-seg.d{background:#14222e;color:var(--text2);border-left:1px solid var(--border2);border-right:1px solid var(--border2)}
.wdl-seg.l{background:#120e1a;color:var(--red)}
.wdl-legend{display:flex;gap:14px;margin-top:7px;font-family:var(--fm);font-size:10px;color:var(--text3)}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px;vertical-align:middle}
.section-title{font-family:var(--fh);font-size:12px;font-weight:700;letter-spacing:.15em;
  text-transform:uppercase;color:var(--text3);margin-bottom:12px;display:flex;align-items:center;gap:8px}
.section-title::before{content:"";display:block;width:14px;height:2px;background:var(--green)}
.tbl-wrap{border:1px solid var(--border);border-radius:9px;overflow:hidden;margin-bottom:24px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{font-family:var(--fh);font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;
  color:var(--text3);padding:9px 12px;text-align:left;border-bottom:1px solid var(--border);
  background:var(--card2);white-space:nowrap}
th.r,td.r{text-align:right}th.c,td.c{text-align:center}
tbody tr{border-bottom:1px solid rgba(26,42,56,.5);transition:background .12s;cursor:pointer}
tbody tr:hover{background:rgba(0,230,118,.04)}
tbody tr:last-child{border-bottom:none}
td{padding:9px 12px;color:var(--text)}
td.mono{font-family:var(--fm);font-size:11px;color:var(--text2)}
td.bold{font-family:var(--fh);font-size:13px;font-weight:700;color:#fff}
td.green{color:var(--green)!important}td.cyan{color:var(--cyan)!important}
td.amber{color:var(--amber)!important}td.red{color:var(--red)!important}td.dim{color:var(--text3)!important}
.badge{display:inline-flex;align-items:center;justify-content:center;
  font-family:var(--fm);font-size:9px;font-weight:600;padding:2px 7px;border-radius:4px;white-space:nowrap}
.badge.ov{background:rgba(0,230,118,.14);color:var(--green);border:1px solid rgba(0,230,118,.3)}
.badge.un{background:rgba(255,82,82,.1);color:var(--red);border:1px solid rgba(255,82,82,.25)}
.badge.yes{background:rgba(41,217,245,.1);color:var(--cyan);border:1px solid rgba(41,217,245,.25)}
.badge.no{background:rgba(26,42,56,.8);color:var(--text3);border:1px solid var(--border)}
.badge.w{background:rgba(0,230,118,.12);color:var(--green);border:1px solid rgba(0,230,118,.25)}
.badge.d{background:rgba(255,179,0,.1);color:var(--amber);border:1px solid rgba(255,179,0,.2)}
.badge.l{background:rgba(255,82,82,.1);color:var(--red);border:1px solid rgba(255,82,82,.2)}
#modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.75);
  z-index:1000;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
#modal-overlay.show{display:flex}
#modal{background:var(--card);border:1px solid var(--border2);border-radius:12px;
  width:560px;max-width:95vw;padding:28px;position:relative;animation:popIn .2s ease}
@keyframes popIn{from{opacity:0;transform:scale(.95)}to{opacity:1;transform:scale(1)}}
#modal-close{position:absolute;top:14px;right:16px;background:none;border:none;
  color:var(--text3);font-size:20px;cursor:pointer;transition:color .15s;line-height:1}
#modal-close:hover{color:var(--text)}
.modal-date{font-family:var(--fm);font-size:10px;color:var(--text3);margin-bottom:6px;letter-spacing:.05em}
.modal-liga{font-family:var(--fh);font-size:11px;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--text2);margin-bottom:16px}
.modal-scoreboard{display:flex;align-items:center;justify-content:center;margin-bottom:22px}
.modal-team{flex:1;text-align:center}
.modal-team-name{font-family:var(--fh);font-size:18px;font-weight:800;letter-spacing:.03em;color:#fff;margin-bottom:4px}
.modal-team-role{font-family:var(--fm);font-size:9px;color:var(--text3);letter-spacing:.06em}
.modal-score{font-family:var(--fh);font-size:56px;font-weight:900;letter-spacing:-.02em;color:#fff;padding:0 20px;line-height:1}
.modal-score .dash{color:var(--text3);font-size:36px;padding:0 6px}
.modal-stats-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:18px}
.mstat{background:var(--card2);border:1px solid var(--border);border-radius:7px;padding:12px;text-align:center}
.mstat-val{font-family:var(--fh);font-size:22px;font-weight:900;color:#fff;line-height:1}
.mstat-label{font-family:var(--fm);font-size:9px;color:var(--text3);margin-top:3px;letter-spacing:.04em}
.modal-badges{display:flex;gap:8px;justify-content:center;flex-wrap:wrap}
.filter-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.fselect{padding:6px 12px;background:var(--card2);border:1px solid var(--border2);
  border-radius:6px;color:var(--text2);font-family:var(--fm);font-size:11px;outline:none;cursor:pointer}
.fselect:focus{border-color:rgba(0,230,118,.4)}
.pbar-wrap{display:flex;align-items:center;gap:6px;min-width:90px}
.pbar-track{flex:1;height:3px;background:var(--border);border-radius:2px;overflow:hidden}
.pbar-fill{height:100%;border-radius:2px;background:var(--green)}
.pbar-fill.c{background:var(--cyan)}.pbar-fill.a{background:var(--amber)}
.pbar-val{font-family:var(--fm);font-size:10px;color:var(--text);min-width:32px;text-align:right}
#content::-webkit-scrollbar{width:5px}
#content::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}
@media(max-width:680px){#sidebar{display:none}.stat-grid,.stat-grid-5{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<div id="topbar">
  <div class="logo-icon">⚽</div>
  <h1>Football <span>Explorer</span></h1>
  <div class="tpills">
    <span class="tpill g">● DATOS REALES</span>
    <span class="tpill" id="tp-total"></span>
    <span class="tpill" id="tp-teams"></span>
    <span class="tpill" id="tp-ligas"></span>
    <span class="tpill" id="tp-temps"></span>
  </div>
</div>
<div id="layout">
  <div id="sidebar">
    <div id="search-wrap">
      <input id="search" type="text" placeholder="🔍  Buscar equipo..." oninput="filterNav(this.value)">
    </div>
    <div id="nav-list"></div>
  </div>
  <div id="content">
    <div class="panel active" id="panel-home">
      <div class="page-hdr">
        <h2>Ligas por Temporada</h2>
        <div class="sub">ESTADÍSTICAS MEDIAS · TODAS LAS COMPETICIONES</div>
      </div>
      <div class="filter-row">
        <select class="fselect" id="lt-filter-liga" onchange="renderLT()"><option value="">Todas las ligas</option></select>
        <select class="fselect" id="lt-filter-temp" onchange="renderLT()"><option value="">Todas las temporadas</option></select>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>Liga</th><th>Temporada</th><th class="r">Partidos</th>
            <th>Media Goles</th><th>Over 2.5</th><th>BTTS</th><th>Corners</th>
            <th>V.Local</th><th>Empate</th><th>V.Visit.</th>
          </tr></thead>
          <tbody id="lt-tbody"></tbody>
        </table>
      </div>
    </div>
    <div class="panel" id="panel-team"><div id="team-content"></div></div>
    <div class="panel" id="panel-matches">
      <div class="page-hdr">
        <h2>Todos los Partidos</h2>
        <div class="sub" id="matches-sub"></div>
      </div>
      <div class="filter-row">
        <select class="fselect" id="m-liga" onchange="renderMatches()"><option value="">Todas las ligas</option></select>
        <select class="fselect" id="m-temp" onchange="renderMatches()"><option value="">Todas las temporadas</option></select>
        <select class="fselect" id="m-team" onchange="renderMatches()"><option value="">Todos los equipos</option></select>
        <select class="fselect" id="m-ov" onchange="renderMatches()">
          <option value="">Over/Under: todos</option>
          <option value="1">Solo Over 2.5</option>
          <option value="0">Solo Under 2.5</option>
        </select>
        <select class="fselect" id="m-btts" onchange="renderMatches()">
          <option value="">BTTS: todos</option>
          <option value="1">Solo BTTS Sí</option>
          <option value="0">Solo BTTS No</option>
        </select>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>Fecha</th><th>Liga</th><th>Temp.</th>
            <th>Local</th><th class="c">Resultado</th><th>Visitante</th>
            <th class="r">Goles</th><th class="r">Corners</th>
            <th class="c">OV2.5</th><th class="c">BTTS</th>
          </tr></thead>
          <tbody id="matches-tbody"></tbody>
        </table>
      </div>
      <div id="matches-pagination" style="display:flex;gap:8px;align-items:center;margin-top:12px;font-family:var(--fm);font-size:11px;color:var(--text3)"></div>
    </div>
  </div>
</div>
<div id="modal-overlay" onclick="closeModal(event)">
  <div id="modal">
    <button id="modal-close" onclick="closeModal()">✕</button>
    <div id="modal-body"></div>
  </div>
</div>
<script>
const RAW = ''' + data_js + ''';

const teamIndex={};RAW.teams.forEach(t=>{teamIndex[t.name]=t});
const matchesByTeam={};
RAW.matches.forEach(m=>{
  [m.local,m.visit].forEach(n=>{if(!matchesByTeam[n])matchesByTeam[n]=[];matchesByTeam[n].push(m)});
});
const matchById={};RAW.matches.forEach(m=>{matchById[m.id]=m});
const ligas=[...new Set(RAW.teams.map(t=>t.liga))].sort();
const temps=[...new Set(RAW.matches.map(m=>m.temporada))].sort();
const allTeams=RAW.teams.map(t=>t.name).sort();

document.getElementById('tp-total').textContent=RAW.matches.length.toLocaleString('es-ES')+' partidos';
document.getElementById('tp-teams').textContent=RAW.teams.length+' equipos';
document.getElementById('tp-ligas').textContent=ligas.length+' ligas';
document.getElementById('tp-temps').textContent=temps.length+' temporadas';

function buildNav(){
  let h='';
  h+=`<div class="nav-item active" data-panel="home" onclick="navClick(this,'home')"><span class="ni-name">📊 Ligas por Temporada</span></div>`;
  h+=`<div class="nav-item" data-panel="matches" onclick="navClick(this,'matches')"><span class="ni-name">⚽ Todos los Partidos</span><span class="ni-badge">${RAW.matches.length.toLocaleString()}</span></div>`;
  ligas.forEach(liga=>{
    const ts=RAW.teams.filter(t=>t.liga===liga);
    h+=`<div class="nav-group-label">${liga}</div>`;
    ts.forEach(t=>{
      const esc=t.name.replace(/\\/g,'\\\\').replace(/'/g,"\\'");
      h+=`<div class="nav-item" data-team="${t.name}" data-panel="team" onclick="navClick(this,'team','${esc}')"><span class="ni-name">${t.name}</span><span class="ni-badge">${t.p}p</span></div>`;
    });
  });
  document.getElementById('nav-list').innerHTML=h;
}
buildNav();

function filterNav(q){
  q=q.toLowerCase().trim();
  document.querySelectorAll('#nav-list .nav-item').forEach(el=>{
    const n=(el.dataset.team||'').toLowerCase();
    el.style.display=(!q||n.includes(q))?'':'none';
  });
  document.querySelectorAll('.nav-group-label').forEach(g=>{
    let next=g.nextElementSibling,vis=false;
    while(next&&!next.classList.contains('nav-group-label')){
      if(next.style.display!=='none')vis=true;
      next=next.nextElementSibling;
    }
    g.style.display=vis?'':'none';
  });
}

function navClick(el,panel,teamName){
  document.querySelectorAll('.nav-item').forEach(i=>i.classList.remove('active'));
  el.classList.add('active');
  showPanel(panel,teamName);
}
function showPanel(panel,teamName){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('panel-'+panel).classList.add('active');
  if(panel==='team'&&teamName)renderTeam(teamName);
  if(panel==='matches')renderMatches();
  if(panel==='home')renderLT();
}

function populateFilters(){
  const ltL=document.getElementById('lt-filter-liga');
  const ltT=document.getElementById('lt-filter-temp');
  ligas.forEach(l=>{ltL.innerHTML+=`<option value="${l}">${l}</option>`;});
  temps.forEach(t=>{ltT.innerHTML+=`<option value="${t}">${t}</option>`;});
  const mL=document.getElementById('m-liga'),mT=document.getElementById('m-temp'),mTm=document.getElementById('m-team');
  ligas.forEach(l=>{mL.innerHTML+=`<option value="${l}">${l}</option>`;});
  temps.forEach(t=>{mT.innerHTML+=`<option value="${t}">${t}</option>`;});
  allTeams.forEach(t=>{mTm.innerHTML+=`<option value="${t}">${t}</option>`;});
}
populateFilters();

function pbar(val,max,cls=''){
  const w=Math.round((val/max)*100);
  return `<div class="pbar-wrap"><div class="pbar-track"><div class="pbar-fill ${cls}" style="width:${w}%"></div></div><span class="pbar-val">${val}%</span></div>`;
}

function renderLT(){
  const fL=document.getElementById('lt-filter-liga').value;
  const fT=document.getElementById('lt-filter-temp').value;
  let rows=RAW.lt_stats.filter(r=>(!fL||r.liga===fL)&&(!fT||r.temp===fT));
  const mOv=Math.max(...rows.map(r=>r.ov25)),mBt=Math.max(...rows.map(r=>r.btts));
  const mG=Math.max(...rows.map(r=>r.goles)),mC=Math.max(...rows.map(r=>r.corners));
  document.getElementById('lt-tbody').innerHTML=rows.map(r=>`
    <tr>
      <td class="bold">${r.liga}</td><td class="mono">${r.temp}</td>
      <td class="mono r">${r.p}</td>
      <td>${pbar(r.goles,mG,'a')}</td><td>${pbar(r.ov25,mOv)}</td>
      <td>${pbar(r.btts,mBt,'c')}</td><td>${pbar(r.corners,mC,'')}</td>
      <td class="mono green">${r.local}%</td>
      <td class="mono">${r.empate}%</td>
      <td class="mono cyan">${r.visit}%</td>
    </tr>`).join('');
}
renderLT();

function renderTeam(name){
  const t=teamIndex[name];if(!t)return;
  const ms=matchesByTeam[name]||[];
  const wP=Math.round(t.w/t.p*100),dP=Math.round(t.d/t.p*100),lP=100-wP-dP;
  const byTemp={};
  ms.forEach(m=>{
    const k=m.temporada;
    if(!byTemp[k])byTemp[k]={p:0,gf:0,gc:0,ov:0,btts:0,w:0,d:0,l:0};
    const s=byTemp[k],h=m.local===name;
    s.p++;s.gf+=h?m.gl:m.gv;s.gc+=h?m.gv:m.gl;s.ov+=m.ov25;s.btts+=m.btts;
    const gf=h?m.gl:m.gv,gc=h?m.gv:m.gl;
    if(gf>gc)s.w++;else if(gf===gc)s.d++;else s.l++;
  });
  const tempRows=Object.entries(byTemp).sort((a,b)=>a[0].localeCompare(b[0])).map(([temp,s])=>{
    const res=s.w>s.l?'<span class="badge w">BUENA</span>':s.w<s.l?'<span class="badge l">MALA</span>':'<span class="badge d">MEDIA</span>';
    const esc=name.replace(/\\\\/g,'\\\\\\\\').replace(/'/g,"\\\\'");
    return `<tr onclick="openTeamMatches('${esc}','${temp}')">
      <td class="mono">${temp}</td><td class="mono r">${s.p}</td>
      <td class="mono green">${s.w}</td><td class="mono amber">${s.d}</td><td class="mono red">${s.l}</td>
      <td class="mono">${(s.gf/s.p).toFixed(2)}</td><td class="mono">${(s.gc/s.p).toFixed(2)}</td>
      <td class="mono">${((s.ov/s.p)*100).toFixed(1)}%</td>
      <td class="mono">${((s.btts/s.p)*100).toFixed(1)}%</td><td>${res}</td></tr>`;
  }).join('');
  const recent=[...ms].sort((a,b)=>b.fecha.localeCompare(a.fecha)).slice(0,20);
  const matchRows=recent.map(m=>{
    const h=m.local===name,gf=h?m.gl:m.gv,gc=h?m.gv:m.gl,opp=h?m.visit:m.local;
    const rc=gf>gc?'w':gf===gc?'d':'l',rl=gf>gc?'V':gf===gc?'E':'D';
    return `<tr onclick="openMatch(${m.id})">
      <td class="mono">${m.fecha}</td><td class="mono dim">${m.temporada}</td>
      <td class="bold">${h?name:'<span style="color:var(--text2)">'+name+'</span>'}</td>
      <td class="mono dim c">${h?'vs':'en'}</td>
      <td class="bold">${!h?name:'<span style="color:var(--text2)">'+opp+'</span>'}</td>
      <td class="mono c"><span class="badge ${rc}">${rl} ${gf}–${gc}</span></td>
      <td class="mono r">${m.tg}</td><td class="mono r">${m.tc}</td>
      <td class="c">${m.ov25?'<span class="badge ov">OV</span>':'<span class="badge un">UN</span>'}</td>
      <td class="c">${m.btts?'<span class="badge yes">SÍ</span>':'<span class="badge no">NO</span>'}</td>
    </tr>`;
  }).join('');
  document.getElementById('team-content').innerHTML=`
    <div class="page-hdr">
      <div class="league-tag">${t.liga}</div>
      <h2>${name}</h2>
      <div class="sub">${t.p} PARTIDOS · ${temps[0]} → ${temps[temps.length-1]}</div>
    </div>
    <div class="stat-grid-5">
      <div class="stat-card"><div class="sc-val">${t.mgf}<span class="u"> gol</span></div><div class="sc-label">Goles anotados/p</div><div class="sc-sub">Media por partido</div></div>
      <div class="stat-card"><div class="sc-val">${t.mgc}<span class="u"> gc</span></div><div class="sc-label">Goles recibidos/p</div><div class="sc-sub">Media por partido</div></div>
      <div class="stat-card"><div class="sc-val">${t.ov25}<span class="p">%</span></div><div class="sc-label">Over 2.5</div><div class="sc-sub">Con este equipo</div></div>
      <div class="stat-card"><div class="sc-val">${t.btts}<span class="p">%</span></div><div class="sc-label">BTTS</div><div class="sc-sub">Ambos marcan</div></div>
      <div class="stat-card"><div class="sc-val">${t.mcorn}<span class="u"> c</span></div><div class="sc-label">Corners/p</div><div class="sc-sub">Media del equipo</div></div>
    </div>
    <div class="wdl-wrap">
      <div class="wdl-label">Victorias / Empates / Derrotas</div>
      <div class="wdl-bar">
        <div class="wdl-seg w" style="flex:${t.w}">${t.w} V (${wP}%)</div>
        <div class="wdl-seg d" style="flex:${t.d}">${t.d} E</div>
        <div class="wdl-seg l" style="flex:${t.l}">${t.l} D (${lP}%)</div>
      </div>
      <div class="wdl-legend">
        <span><span class="dot" style="background:var(--green)"></span>${t.w} victorias</span>
        <span><span class="dot" style="background:var(--text3)"></span>${t.d} empates</span>
        <span><span class="dot" style="background:var(--red)"></span>${t.l} derrotas</span>
      </div>
    </div>
    <div class="section-title">Por Temporada <span style="font-weight:400;font-size:10px;margin-left:6px;color:var(--text3)">— clic para ver partidos de esa temporada</span></div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Temporada</th><th class="r">P</th><th class="r">V</th><th class="r">E</th><th class="r">D</th><th>Goles/p</th><th>GC/p</th><th>Over 2.5</th><th>BTTS</th><th>Forma</th></tr></thead>
      <tbody>${tempRows}</tbody>
    </table></div>
    <div class="section-title">Últimos 20 Partidos <span style="font-weight:400;font-size:10px;margin-left:6px;color:var(--text3)">— clic para ver detalle</span></div>
    <div class="tbl-wrap"><table>
      <thead><tr><th>Fecha</th><th>Temp.</th><th>Local</th><th class="c"></th><th>Visitante</th><th class="c">Resultado</th><th class="r">Goles</th><th class="r">Corners</th><th class="c">OV2.5</th><th class="c">BTTS</th></tr></thead>
      <tbody>${matchRows}</tbody>
    </table></div>`;
}

function openTeamMatches(team,temp){
  document.querySelectorAll('.nav-item').forEach(i=>i.classList.remove('active'));
  document.querySelector('[data-panel="matches"]').classList.add('active');
  document.getElementById('m-team').value=team;
  document.getElementById('m-temp').value=temp;
  document.getElementById('m-liga').value='';
  document.getElementById('m-ov').value='';
  document.getElementById('m-btts').value='';
  showPanel('matches');
}

let matchPage=0;const PS=50;
function renderMatches(){matchPage=0;renderMatchesPage();}
function renderMatchesPage(){
  const fL=document.getElementById('m-liga').value;
  const fT=document.getElementById('m-temp').value;
  const fTm=document.getElementById('m-team').value;
  const fOv=document.getElementById('m-ov').value;
  const fBt=document.getElementById('m-btts').value;
  let rows=RAW.matches.filter(m=>
    (!fL||m.liga===fL)&&(!fT||m.temporada===fT)&&
    (!fTm||m.local===fTm||m.visit===fTm)&&
    (fOv===''||m.ov25===parseInt(fOv))&&
    (fBt===''||m.btts===parseInt(fBt))
  );
  document.getElementById('matches-sub').textContent=
    `${rows.length.toLocaleString('es-ES')} PARTIDOS · `+(fL||'TODAS LAS LIGAS')+' · '+(fT||'TODAS LAS TEMPORADAS');
  const total=rows.length,tp=Math.ceil(total/PS),start=matchPage*PS;
  document.getElementById('matches-tbody').innerHTML=rows.slice(start,start+PS).map(m=>{
    return `<tr onclick="openMatch(${m.id})">
      <td class="mono">${m.fecha}</td><td class="mono dim">${m.liga}</td>
      <td class="mono dim">${m.temporada}</td>
      <td class="bold">${m.local}</td>
      <td class="mono c"><b>${m.gl} – ${m.gv}</b></td>
      <td class="bold" style="color:var(--text2)">${m.visit}</td>
      <td class="mono r">${m.tg}</td><td class="mono r">${m.tc}</td>
      <td class="c">${m.ov25?'<span class="badge ov">OV</span>':'<span class="badge un">UN</span>'}</td>
      <td class="c">${m.btts?'<span class="badge yes">SÍ</span>':'<span class="badge no">NO</span>'}</td>
    </tr>`;
  }).join('');
  const pg=document.getElementById('matches-pagination');
  if(tp<=1){pg.innerHTML='';return;}
  let b=`<span>${(start+1).toLocaleString()}–${Math.min(start+PS,total).toLocaleString()} de ${total.toLocaleString()}</span>`;
  const btnStyle='padding:5px 12px;background:var(--card2);border:1px solid var(--border2);border-radius:5px;color:var(--text2);cursor:pointer;font-family:var(--fm);font-size:11px';
  if(matchPage>0)b+=`<button style="${btnStyle}" onclick="matchPage--;renderMatchesPage()">← Anterior</button>`;
  if(matchPage<tp-1)b+=`<button style="${btnStyle}" onclick="matchPage++;renderMatchesPage()">Siguiente →</button>`;
  b+=`<span>Página ${matchPage+1}/${tp}</span>`;
  pg.innerHTML=b;
}

function openMatch(id){
  const m=matchById[id];if(!m)return;
  const res=m.gl>m.gv?'Victoria Local':m.gl===m.gv?'Empate':'Victoria Visitante';
  const rc=m.gl>m.gv?'var(--green)':m.gl===m.gv?'var(--amber)':'var(--cyan)';
  document.getElementById('modal-body').innerHTML=`
    <div class="modal-date">${m.fecha} · ${m.temporada}</div>
    <div class="modal-liga">${m.liga}</div>
    <div class="modal-scoreboard">
      <div class="modal-team"><div class="modal-team-name">${m.local}</div><div class="modal-team-role">LOCAL</div></div>
      <div class="modal-score">${m.gl}<span class="dash">–</span>${m.gv}</div>
      <div class="modal-team"><div class="modal-team-name">${m.visit}</div><div class="modal-team-role">VISITANTE</div></div>
    </div>
    <div style="text-align:center;margin-bottom:18px">
      <span style="font-family:var(--fh);font-size:14px;font-weight:700;color:${rc};letter-spacing:.06em;text-transform:uppercase">${res}</span>
    </div>
    <div class="modal-stats-grid">
      <div class="mstat"><div class="mstat-val" style="color:var(--green)">${m.tg}</div><div class="mstat-label">Total Goles</div></div>
      <div class="mstat"><div class="mstat-val">${m.cl} – ${m.cv}</div><div class="mstat-label">Corners L – V</div></div>
      <div class="mstat"><div class="mstat-val">${m.tc}</div><div class="mstat-label">Total Corners</div></div>
      <div class="mstat"><div class="mstat-val">${m.gl}</div><div class="mstat-label">Goles ${m.local}</div></div>
      <div class="mstat"><div class="mstat-val">${m.gv}</div><div class="mstat-label">Goles ${m.visit}</div></div>
      <div class="mstat"><div class="mstat-val" style="font-size:16px">${m.liga.split(' ')[0]}</div><div class="mstat-label">Liga</div></div>
    </div>
    <div class="modal-badges">
      ${m.ov25?'<span class="badge ov" style="font-size:11px;padding:5px 14px">✓ Over 2.5</span>':'<span class="badge un" style="font-size:11px;padding:5px 14px">✗ Under 2.5</span>'}
      ${m.btts?'<span class="badge yes" style="font-size:11px;padding:5px 14px">✓ Ambos Marcan</span>':'<span class="badge no" style="font-size:11px;padding:5px 14px">✗ No Ambos Marcan</span>'}
      ${m.tg>=4?'<span class="badge ov" style="font-size:11px;padding:5px 14px">Over 3.5</span>':''}
      ${m.tg>=5?'<span class="badge ov" style="font-size:11px;padding:5px 14px">Over 4.5</span>':''}
      ${m.tc>=10?'<span class="badge yes" style="font-size:11px;padding:5px 14px">Over 9.5 Corn.</span>':''}
    </div>`;
  document.getElementById('modal-overlay').classList.add('show');
}
function closeModal(e){
  if(e&&e.target!==document.getElementById('modal-overlay'))return;
  document.getElementById('modal-overlay').classList.remove('show');
}
document.getElementById('modal-close').onclick=()=>document.getElementById('modal-overlay').classList.remove('show');
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('modal-overlay').classList.remove('show')});
</script>
</body>
</html>'''

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    size = os.path.getsize(OUT_PATH) / 1024
    print(f"\n✅ Explorador generado: {OUT_PATH}")
    print(f"   Tamaño: {size:.0f} KB")
    print(f"\n🌐 Abre en Chrome: data_clean/explorador.html")


if __name__ == "__main__":
    main()

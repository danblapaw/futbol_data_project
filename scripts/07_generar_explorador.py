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
OUT_PATH = os.path.join(BASE_DIR, "football_explorer.html")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

# ── Filtros del explorador ────────────────────────────────────────────────────
TEMPORADA = "2025-26"

LIGAS = [
    # Europa
    "La Liga",              "Segunda Division",
    "Premier League",       "Championship",         "League One",       "League Two",   "Conference",
    "Bundesliga",           "Bundesliga 2",
    "Serie A",              "Serie B",
    "Ligue 1",              "Ligue 2",
    "Primeira Liga",
    "First Division A",
    "Eredivisie",
    "Super Lig",
    "Super League Greece",
    "Scottish Premiership", "Scottish Championship","Scottish League One","Scottish League Two",
    # Resto del mundo
    "Liga Profesional ARG", "Bundesliga AUT",       "Brasileirao",
    "Chinese Super League", "Danish Superliga",     "Veikkausliiga",
    "League of Ireland",    "J1 League",            "Liga MX",
    "Eliteserien",          "Ekstraklasa",          "Romanian Superliga",
    "Russian Premier League","Allsvenskan",         "Swiss Super League",
    "MLS",
]

_PH = ",".join("?" * len(LIGAS))   # placeholders SQLite: ?,?,?,...


def extraer(db):
    print(f"📂 Leyendo {db}...")
    params_base = [TEMPORADA] + LIGAS

    with sqlite3.connect(db) as conn:

        matches_raw = conn.execute(f"""
            SELECT id,fecha,liga,temporada,
                   equipo_local,equipo_visitante,
                   goles_local,goles_visitante,
                   corners_local,corners_visitante,
                   amarillas_local,amarillas_visitante,
                   rojas_local,rojas_visitante,
                   total_goles,total_corners,
                   total_amarillas,total_rojas,
                   ambos_marcan,over_2_5
            FROM partidos
            WHERE temporada=? AND liga IN ({_PH})
            ORDER BY fecha DESC
        """, params_base).fetchall()
        matches = [{"id":r[0],"fecha":r[1],"liga":r[2],"temporada":r[3],
                    "local":r[4],"visit":r[5],"gl":r[6],"gv":r[7],
                    "cl":r[8],"cv":r[9],"al":r[10],"av":r[11],
                    "rl":r[12],"rv":r[13],"tg":r[14],"tc":r[15],
                    "ta":r[16],"tr":r[17],"btts":r[18],"ov25":r[19]} for r in matches_raw]

        teams_raw = conn.execute(f"""
            SELECT equipo,liga,
                SUM(n) p,
                ROUND(SUM(gf)*1.0/SUM(n),2) mgf,
                ROUND(SUM(gc)*1.0/SUM(n),2) mgc,
                ROUND(SUM(ov)*100.0/SUM(n),1) ov25,
                ROUND(SUM(btts)*100.0/SUM(n),1) btts,
                ROUND(SUM(corn)*1.0/SUM(n),1) mcorn,
                SUM(wins) w, SUM(draws) d, SUM(losses) l,
                SUM(gf) tgf, SUM(gc) tgc,
                ROUND(SUM(ama)*1.0/SUM(n),1) mam,
                ROUND(SUM(roj)*1.0/SUM(n),2) mro
            FROM (
                SELECT equipo_local equipo,liga,COUNT(*) n,
                    SUM(goles_local) gf,SUM(goles_visitante) gc,
                    SUM(over_2_5) ov,SUM(ambos_marcan) btts,SUM(corners_local) corn,
                    SUM(CASE WHEN goles_local>goles_visitante THEN 1 ELSE 0 END) wins,
                    SUM(CASE WHEN goles_local=goles_visitante THEN 1 ELSE 0 END) draws,
                    SUM(CASE WHEN goles_local<goles_visitante THEN 1 ELSE 0 END) losses,
                    SUM(amarillas_local) ama, SUM(rojas_local) roj
                FROM partidos WHERE temporada=? AND liga IN ({_PH})
                GROUP BY equipo_local,liga
                UNION ALL
                SELECT equipo_visitante,liga,COUNT(*),
                    SUM(goles_visitante),SUM(goles_local),
                    SUM(over_2_5),SUM(ambos_marcan),SUM(corners_visitante),
                    SUM(CASE WHEN goles_visitante>goles_local THEN 1 ELSE 0 END),
                    SUM(CASE WHEN goles_local=goles_visitante THEN 1 ELSE 0 END),
                    SUM(CASE WHEN goles_visitante<goles_local THEN 1 ELSE 0 END),
                    SUM(amarillas_visitante), SUM(rojas_visitante)
                FROM partidos WHERE temporada=? AND liga IN ({_PH})
                GROUP BY equipo_visitante,liga
            ) GROUP BY equipo,liga ORDER BY liga,equipo
        """, params_base + params_base).fetchall()
        teams = [{"name":r[0],"liga":r[1],"p":r[2],"mgf":r[3],"mgc":r[4],
                  "ov25":r[5],"btts":r[6],"mcorn":r[7],"w":r[8],"d":r[9],"l":r[10],
                  "tgf":r[11],"tgc":r[12],"mam":r[13],"mro":r[14]}
                 for r in teams_raw]

        lt_raw = conn.execute(f"""
            SELECT liga,temporada,COUNT(*) p,
                ROUND(AVG(total_goles),2) goles,
                ROUND(AVG(over_2_5)*100,1) ov25,
                ROUND(AVG(ambos_marcan)*100,1) btts,
                ROUND(AVG(total_corners),1) corners,
                ROUND(AVG(CASE WHEN goles_local>goles_visitante THEN 1.0 ELSE 0 END)*100,1) local,
                ROUND(AVG(CASE WHEN goles_local=goles_visitante THEN 1.0 ELSE 0 END)*100,1) empate,
                ROUND(AVG(CASE WHEN goles_local<goles_visitante THEN 1.0 ELSE 0 END)*100,1) visit,
                ROUND(AVG(total_amarillas),1) amarillas,
                ROUND(AVG(total_rojas),2) rojas
            FROM partidos
            WHERE temporada=? AND liga IN ({_PH})
            GROUP BY liga,temporada ORDER BY liga
        """, params_base).fetchall()
        lt_stats = [{"liga":r[0],"temp":r[1],"p":r[2],"goles":r[3],
                     "ov25":r[4],"btts":r[5],"corners":r[6],
                     "local":r[7],"empate":r[8],"visit":r[9],
                     "amarillas":r[10],"rojas":r[11]} for r in lt_raw]

    print(f"✅ {len(matches):,} partidos | {len(teams)} equipos | {len(lt_stats)} ligas")
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
  border-top:1px solid var(--border);margin-top:4px;cursor:pointer;
  display:flex;align-items:center;justify-content:space-between;user-select:none}
.nav-group-label:first-child{border-top:none;margin-top:0}
.nav-group-label:hover{color:var(--text2)}
.liga-arrow{font-size:9px;transition:transform .2s;flex-shrink:0;opacity:.6}
.nav-group-label.expanded .liga-arrow{transform:rotate(90deg)}
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
.stat-grid-7{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;margin-bottom:22px}
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
            <th class="r">Amarillas/p</th><th class="r">Rojas/p</th>
            <th>V.Local</th><th>Empate</th><th>V.Visit.</th>
          </tr></thead>
          <tbody id="lt-tbody"></tbody>
        </table>
      </div>
    </div>
    <div class="panel" id="panel-team"><div id="team-content"></div></div>
    <div class="panel" id="panel-standings">
      <div class="page-hdr">
        <h2>Clasificación</h2>
        <div class="sub" id="standings-sub">TABLA DE POSICIONES · 2025-26</div>
      </div>
      <div class="filter-row">
        <select class="fselect" id="s-liga" onchange="renderStandings()"><option value="">Selecciona una liga</option></select>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th class="r">Pos</th><th>Equipo</th>
            <th class="r">PJ</th><th class="r">G</th><th class="r">E</th><th class="r">D</th>
            <th class="r">GF</th><th class="r">GC</th><th class="r">DG</th><th class="r">Pts</th>
            <th class="r">Forma</th>
          </tr></thead>
          <tbody id="standings-tbody"></tbody>
        </table>
      </div>
    </div>
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
            <th class="r">Amar.</th><th class="r">Rojas</th>
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

function ligaId(liga){return'liga-'+liga.replace(/[^a-z0-9]/gi,'_')}

function buildNav(activeTeam){
  let h='';
  h+=`<div class="nav-item active" data-panel="home" onclick="navClick(this,'home')"><span class="ni-name">📊 Ligas por Temporada</span></div>`;
  h+=`<div class="nav-item" data-panel="standings" onclick="navClick(this,'standings')"><span class="ni-name">🏆 Clasificación</span></div>`;
  h+=`<div class="nav-item" data-panel="matches" onclick="navClick(this,'matches')"><span class="ni-name">⚽ Todos los Partidos</span><span class="ni-badge">${RAW.matches.length.toLocaleString()}</span></div>`;
  ligas.forEach(liga=>{
    const ts=RAW.teams.filter(t=>t.liga===liga);
    const activeLiga=activeTeam&&ts.some(t=>t.name===activeTeam);
    const id=ligaId(liga);
    h+=`<div class="nav-group-label${activeLiga?' expanded':''}" data-liga="${liga}" onclick="toggleLiga(this)"><span>${liga}</span><span class="liga-arrow">▸</span></div>`;
    h+=`<div class="nav-liga-teams" id="${id}" style="${activeLiga?'':'display:none'}">`;
    ts.forEach(t=>{
      const esc=t.name.replace(/\\\\/g,'\\\\\\\\').replace(/'/g,"\\\\'");
      h+=`<div class="nav-item" data-team="${t.name}" data-liga="${liga}" data-panel="team" onclick="navClick(this,'team','${esc}')"><span class="ni-name">${t.name}</span><span class="ni-badge">${t.p}p</span></div>`;
    });
    h+=`</div>`;
  });
  document.getElementById('nav-list').innerHTML=h;
}
buildNav();

function toggleLiga(el){
  const id=ligaId(el.dataset.liga);
  const container=document.getElementById(id);
  const open=container.style.display!=='none';
  container.style.display=open?'none':'block';
  el.classList.toggle('expanded',!open);
}

function filterNav(q){
  q=q.toLowerCase().trim();
  if(q){
    document.querySelectorAll('#nav-list .nav-item[data-team]').forEach(el=>{
      const n=(el.dataset.team||'').toLowerCase();
      el.style.display=n.includes(q)?'':'none';
    });
    document.querySelectorAll('.nav-group-label[data-liga]').forEach(g=>{
      const id=ligaId(g.dataset.liga);
      const container=document.getElementById(id);
      const hasVis=[...container.querySelectorAll('.nav-item')].some(i=>i.style.display!=='none');
      g.style.display=hasVis?'':'none';
      container.style.display=hasVis?'block':'none';
      g.classList.toggle('expanded',hasVis);
    });
  } else {
    document.querySelectorAll('#nav-list .nav-item[data-team]').forEach(el=>el.style.display='');
    document.querySelectorAll('.nav-group-label[data-liga]').forEach(g=>{
      g.style.display='';
      const id=ligaId(g.dataset.liga);
      const container=document.getElementById(id);
      container.style.display=g.classList.contains('expanded')?'block':'none';
    });
  }
}

function navClick(el,panel,teamName){
  document.querySelectorAll('.nav-item').forEach(i=>i.classList.remove('active'));
  el.classList.add('active');
  if(el.dataset.liga){
    const header=document.querySelector(`.nav-group-label[data-liga="${el.dataset.liga}"]`);
    const id=ligaId(el.dataset.liga);
    const container=document.getElementById(id);
    if(container&&container.style.display==='none'){
      container.style.display='block';
      if(header)header.classList.add('expanded');
    }
  }
  showPanel(panel,teamName);
}
function showPanel(panel,teamName){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('panel-'+panel).classList.add('active');
  if(panel==='team'&&teamName)renderTeam(teamName);
  if(panel==='matches')renderMatches();
  if(panel==='home')renderLT();
  if(panel==='standings')renderStandings();
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
  const sL=document.getElementById('s-liga');
  ligas.forEach(l=>{sL.innerHTML+=`<option value="${l}">${l}</option>`;});
}
populateFilters();

function pbar(val,max,cls='',pct=true){
  const w=Math.round((val/max)*100);
  return `<div class="pbar-wrap"><div class="pbar-track"><div class="pbar-fill ${cls}" style="width:${w}%"></div></div><span class="pbar-val">${val}${pct?'%':''}</span></div>`;
}

function renderLT(){
  const fL=document.getElementById('lt-filter-liga').value;
  const fT=document.getElementById('lt-filter-temp').value;
  let rows=RAW.lt_stats.filter(r=>(!fL||r.liga===fL)&&(!fT||r.temp===fT));
  const mOv=Math.max(...rows.map(r=>r.ov25)),mBt=Math.max(...rows.map(r=>r.btts));
  const mG=Math.max(...rows.map(r=>r.goles)),mC=Math.max(...rows.map(r=>r.corners));
  const mAm=Math.max(...rows.map(r=>r.amarillas||0));
  document.getElementById('lt-tbody').innerHTML=rows.map(r=>`
    <tr>
      <td class="bold">${r.liga}</td><td class="mono">${r.temp}</td>
      <td class="mono r">${r.p}</td>
      <td>${pbar(r.goles,mG,'a',false)}</td><td>${pbar(r.ov25,mOv)}</td>
      <td>${pbar(r.btts,mBt,'c')}</td><td>${r.corners>0?pbar(r.corners,mC,'',false):'<span style="color:var(--text3)">—</span>'}</td>
      <td class="mono amber r">${r.amarillas>0?r.amarillas:'<span style="color:var(--text3)">—</span>'}</td>
      <td class="mono red r">${r.rojas>0?r.rojas:'<span style="color:var(--text3)">—</span>'}</td>
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
      <td class="bold">${h?name:'<span style="color:var(--text2)">'+opp+'</span>'}</td>
      <td class="mono dim c">${h?'vs':'en'}</td>
      <td class="bold">${!h?name:'<span style="color:var(--text2)">'+opp+'</span>'}</td>
      <td class="mono c"><span class="badge ${rc}">${rl} ${gf}–${gc}</span></td>
      <td class="mono r">${m.tg}</td>
      <td class="mono r dim">${m.tc>0?m.tc:'—'}</td>
      <td class="mono amber r">${m.ta>0?(h?m.al:m.av):'—'}</td>
      <td class="mono red r">${m.tr>0?(h?m.rl:m.rv):'—'}</td>
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
    <div class="stat-grid-7">
      <div class="stat-card"><div class="sc-val">${t.mgf}<span class="u"> gol</span></div><div class="sc-label">Goles anotados/p</div><div class="sc-sub">Media por partido</div></div>
      <div class="stat-card"><div class="sc-val">${t.mgc}<span class="u"> gc</span></div><div class="sc-label">Goles recibidos/p</div><div class="sc-sub">Media por partido</div></div>
      <div class="stat-card"><div class="sc-val">${t.ov25}<span class="p">%</span></div><div class="sc-label">Over 2.5</div><div class="sc-sub">Con este equipo</div></div>
      <div class="stat-card"><div class="sc-val">${t.btts}<span class="p">%</span></div><div class="sc-label">BTTS</div><div class="sc-sub">Ambos marcan</div></div>
      <div class="stat-card"><div class="sc-val">${t.mcorn}<span class="u"> c</span></div><div class="sc-label">Corners/p</div><div class="sc-sub">Media del equipo</div></div>
      <div class="stat-card"><div class="sc-val" style="color:var(--amber)">${t.mam||0}<span class="u"> 🟨</span></div><div class="sc-label">Amarillas/p</div><div class="sc-sub">Media del equipo</div></div>
      <div class="stat-card"><div class="sc-val" style="color:var(--red)">${t.mro||0}<span class="u"> 🟥</span></div><div class="sc-label">Rojas/p</div><div class="sc-sub">Media del equipo</div></div>
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
      <thead><tr><th>Fecha</th><th>Temp.</th><th>Local</th><th class="c"></th><th>Visitante</th><th class="c">Resultado</th><th class="r">Goles</th><th class="r">Corners</th><th class="r">🟨</th><th class="r">🟥</th><th class="c">OV2.5</th><th class="c">BTTS</th></tr></thead>
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
      <td class="mono r">${m.tg}</td>
      <td class="mono r dim">${m.tc>0?m.tc:'—'}</td>
      <td class="mono amber r">${m.ta>0?m.ta:'—'}</td><td class="mono red r">${m.tr>0?m.tr:'—'}</td>
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
      <div class="mstat"><div class="mstat-val">${m.tc>0?m.cl+' – '+m.cv:'—'}</div><div class="mstat-label">Corners L – V</div></div>
      <div class="mstat"><div class="mstat-val">${m.tc>0?m.tc:'—'}</div><div class="mstat-label">Total Corners</div></div>
      <div class="mstat"><div class="mstat-val" style="color:var(--amber)">${m.ta>0?m.al+' – '+m.av:'—'}</div><div class="mstat-label">🟨 Amarillas L – V</div></div>
      <div class="mstat"><div class="mstat-val" style="color:var(--amber)">${m.ta>0?m.ta:'—'}</div><div class="mstat-label">Total Amarillas</div></div>
      <div class="mstat"><div class="mstat-val" style="color:var(--red)">${m.ta>0||m.tr>0?m.rl+' – '+m.rv:'—'}</div><div class="mstat-label">🟥 Rojas L – V</div></div>
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
// Zonas: ucl/uel/uecl=competiciones europeas, promo=ascenso directo, pp=playoff ascenso
//        rp=playoff descenso, rel=descenso directo. Negativos=desde el final.
const ZONES={
  // ── INGLATERRA ────────────────────────────────────────────
  "Premier League":        {ucl:[1,2,3,4],uel:[5],uecl:[6],rel:[-3,-2,-1]},
  "Championship":          {promo:[1,2],pp:[3,4,5,6],rel:[-3,-2,-1]},
  "League One":            {promo:[1,2],pp:[3,4,5,6],rel:[-4,-3,-2,-1]},
  "League Two":            {promo:[1,2,3],pp:[4,5,6,7],rel:[-1]},
  "Conference":            {promo:[1,2],pp:[3,4,5,6,7],rel:[-2,-1]},
  // ── ESPAÑA ────────────────────────────────────────────────
  "La Liga":               {ucl:[1,2,3,4],uel:[5,6],uecl:[7],rel:[-3,-2,-1]},
  "Segunda Division":      {promo:[1,2],pp:[3,4,5,6],rel:[-4,-3,-2,-1]},
  // ── ALEMANIA ──────────────────────────────────────────────
  "Bundesliga":            {ucl:[1,2,3,4],uel:[5],uecl:[6],rp:[-3],rel:[-2,-1]},
  "Bundesliga 2":          {promo:[1,2],pp:[3],rel:[-3,-2,-1]},
  // ── ITALIA ────────────────────────────────────────────────
  "Serie A":               {ucl:[1,2,3,4],uel:[5,6],uecl:[7],rel:[-3,-2,-1]},
  "Serie B":               {promo:[1,2],pp:[3,4,5,6,7,8],rel:[-4,-3,-2,-1]},
  // ── FRANCIA ───────────────────────────────────────────────
  "Ligue 1":               {ucl:[1,2,3],uel:[4],uecl:[5],rp:[-3],rel:[-2,-1]},
  "Ligue 2":               {promo:[1,2],pp:[3],rel:[-3,-2,-1]},
  // ── OTROS EUROPA ──────────────────────────────────────────
  "Eredivisie":            {ucl:[1],uel:[2,3],uecl:[4],rp:[-3,-2],rel:[-1]},
  "Primeira Liga":         {ucl:[1,2],uel:[3],uecl:[4,5],rp:[-3],rel:[-2,-1]},
  "Scottish Premiership":  {ucl:[1],uel:[2],uecl:[3],rp:[-2],rel:[-1]},
  "Scottish Championship": {promo:[1],pp:[2],rel:[-2,-1]},
  "Scottish League One":   {promo:[1],pp:[2],rel:[-2,-1]},
  "Scottish League Two":   {promo:[1],pp:[2]},
  "First Division A":      {ucl:[1],uel:[2],uecl:[3],rp:[-3,-2],rel:[-1]},
  "Super Lig":             {ucl:[1],uel:[2,3],uecl:[4],rel:[-3,-2,-1]},
  "Super League Greece":   {ucl:[1],uel:[2],uecl:[3],rel:[-3,-2,-1]},
  // ── RESTO DEL MUNDO ───────────────────────────────────────
  "Liga Profesional ARG":  {rel:[-3,-2,-1]},
  "Bundesliga AUT":        {ucl:[1],uel:[2],uecl:[3],rp:[-2],rel:[-1]},
  "Brasileirao":           {rel:[-4,-3,-2,-1]},
  "Chinese Super League":  {rel:[-3,-2,-1]},
  "Danish Superliga":      {ucl:[1],uel:[2],uecl:[3],rp:[-3,-2],rel:[-1]},
  "Veikkausliiga":         {rp:[-2],rel:[-1]},
  "League of Ireland":     {rp:[-2],rel:[-1]},
  "J1 League":             {rp:[-3],rel:[-2,-1]},
  "Liga MX":               {},
  "Eliteserien":           {rp:[-3,-2],rel:[-1]},
  "Ekstraklasa":           {ucl:[1],uel:[2],uecl:[3],rel:[-4,-3,-2,-1]},
  "Romanian Superliga":    {rel:[-4,-3,-2,-1]},
  "Russian Premier League":{rp:[-4,-3],rel:[-2,-1]},
  "Allsvenskan":           {rp:[-4,-3],rel:[-2,-1]},
  "Swiss Super League":    {ucl:[1],uel:[2],uecl:[3],rp:[-2],rel:[-1]},
  "MLS":                   {},
};
function getZone(liga,pos,total){
  const z=ZONES[liga]||{};
  const check=v=>v>0?v:(total+v+1);
  if((z.ucl||[]).map(check).includes(pos))return'ucl';
  if((z.uel||[]).map(check).includes(pos))return'uel';
  if((z.uecl||[]).map(check).includes(pos))return'uecl';
  if((z.promo||[]).map(check).includes(pos))return'promo';
  if((z.pp||[]).map(check).includes(pos))return'pp';
  if((z.rp||[]).map(check).includes(pos))return'rp';
  if((z.rel||[]).map(check).includes(pos))return'rel';
  return'';
}
function computeStandings(liga){
  const ms=RAW.matches.filter(m=>m.liga===liga);
  const tbl={};
  ms.forEach(m=>{
    if(!tbl[m.local])tbl[m.local]={p:0,g:0,e:0,d:0,gf:0,gc:0,pts:0,form:[]};
    if(!tbl[m.visit])tbl[m.visit]={p:0,g:0,e:0,d:0,gf:0,gc:0,pts:0,form:[]};
    const h=tbl[m.local],a=tbl[m.visit];
    h.p++;a.p++;h.gf+=m.gl;h.gc+=m.gv;a.gf+=m.gv;a.gc+=m.gl;
    if(m.gl>m.gv){h.g++;h.pts+=3;h.form.push('w');a.d++;a.form.push('l');}
    else if(m.gl===m.gv){h.e++;h.pts++;h.form.push('d');a.e++;a.pts++;a.form.push('d');}
    else{a.g++;a.pts+=3;a.form.push('w');h.d++;h.form.push('l');}
  });
  return Object.entries(tbl)
    .map(([name,s])=>({name,...s,dg:s.gf-s.gc}))
    .sort((a,b)=>b.pts-a.pts||b.dg-a.dg||b.gf-a.gf);
}
const ZONE_STYLE={
  ucl:  'border-left:3px solid #5c6bc0;background:rgba(92,107,192,0.10)',
  uel:  'border-left:3px solid #ef6c00;background:rgba(239,108,0,0.08)',
  uecl: 'border-left:3px solid #26a69a;background:rgba(38,166,154,0.08)',
  promo:'border-left:3px solid var(--green);background:rgba(0,230,118,0.07)',
  pp:   'border-left:3px solid rgba(0,230,118,0.4);background:rgba(0,230,118,0.03)',
  rp:   'border-left:3px solid var(--amber);background:rgba(255,179,0,0.06)',
  rel:  'border-left:3px solid var(--red);background:rgba(255,82,82,0.07)',
  '':   'border-left:3px solid transparent',
};
function renderStandings(){
  const liga=document.getElementById('s-liga').value;
  document.getElementById('standings-sub').textContent=liga?('CLASIFICACIÓN · '+liga+' · 2025-26'):'TABLA DE POSICIONES · 2025-26';
  if(!liga){
    document.getElementById('standings-tbody').innerHTML='<tr><td colspan="11" style="text-align:center;color:var(--text3);padding:24px">Selecciona una liga para ver la clasificación</td></tr>';
    return;
  }
  const rows=computeStandings(liga);
  const total=rows.length;
  const formLabels={'w':'V','d':'E','l':'D'};
  const formCls={'w':'badge w','d':'badge d','l':'badge l'};
  const z=ZONES[liga]||{};
  const hasZones=Object.keys(z).length>0;
  const tbody=rows.map((r,i)=>{
    const pos=i+1;
    const zone=getZone(liga,pos,total);
    const zstyle=ZONE_STYLE[zone]||ZONE_STYLE[''];
    const lastForm=r.form.slice(-5).reverse().map(f=>`<span class="${formCls[f]}" style="padding:1px 5px;font-size:9px">${formLabels[f]}</span>`).join('');
    const champion=pos===1?'<span style="color:#ffd700;margin-right:4px" title="Campeón">★</span>':'';
    const ptsColor=pos===1?'#ffd700':zone==='ucl'?'#7986cb':zone==='uel'?'#ef6c00':zone==='uecl'?'#26a69a':'var(--text)';
    const pts=`<span style="font-family:var(--fh);font-size:17px;font-weight:900;color:${ptsColor}">${r.pts}</span>`;
    return `<tr style="${zstyle}">
      <td class="mono r" style="color:var(--text3)">${pos}</td>
      <td class="bold" style="cursor:pointer" onclick="goTeam('${r.name.replace(/'/g,"\\\\'")}')">${champion}${r.name}</td>
      <td class="mono r">${r.p}</td><td class="mono green r">${r.g}</td>
      <td class="mono r">${r.e}</td><td class="mono red r">${r.d}</td>
      <td class="mono r">${r.gf}</td><td class="mono r">${r.gc}</td>
      <td class="mono r" style="color:${r.dg>0?'var(--green)':r.dg<0?'var(--red)':'var(--text2)'}">
        ${r.dg>0?'+'+r.dg:r.dg}</td>
      <td class="r">${pts}</td>
      <td style="text-align:right">${lastForm}</td>
    </tr>`;
  }).join('');
  // Legend
  const dot=(col)=>`<span style="width:10px;height:10px;background:${col};border-radius:2px;display:inline-block"></span>`;
  const li=(col,txt)=>`<span style="display:inline-flex;align-items:center;gap:5px">${dot(col)}${txt}</span>`;
  let items=[];
  items.push(li('#ffd700','★ Campeón'));
  if(z.ucl&&z.ucl.length)  items.push(li('#5c6bc0','Champions League'));
  if(z.uel&&z.uel.length)  items.push(li('#ef6c00','Europa League'));
  if(z.uecl&&z.uecl.length)items.push(li('#26a69a','Conference League'));
  if(z.promo&&z.promo.length)items.push(li('var(--green)','Ascenso directo'));
  if(z.pp&&z.pp.length)   items.push(li('rgba(0,230,118,0.5)','Playoff ascenso'));
  if(z.rp&&z.rp.length)   items.push(li('var(--amber)','Playoff descenso'));
  if(z.rel&&z.rel.length)  items.push(li('var(--red)','Descenso directo'));
  let legend;
  if(!hasZones){
    legend='<div style="margin-top:10px;font-family:var(--fm);font-size:10px;color:var(--text3)">Esta liga no tiene sistema de ascenso/descenso tradicional</div>';
  } else {
    legend=`<div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:12px;font-family:var(--fm);font-size:10px;color:var(--text2)">${items.join('')}</div>`;
  }
  document.getElementById('standings-tbody').innerHTML=tbody;
  // Insert legend after table
  const wrap=document.getElementById('standings-tbody').closest('.tbl-wrap');
  let leg=wrap.nextElementSibling;
  if(leg&&leg.id==='standings-legend')leg.remove();
  const div=document.createElement('div');div.id='standings-legend';div.innerHTML=legend;
  wrap.insertAdjacentElement('afterend',div);
}
function goTeam(name){
  const el=document.querySelector('[data-team="'+name+'"]');
  if(el){el.click();}
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
    print(f"\n🌐 Abre en Chrome: football_explorer.html")


if __name__ == "__main__":
    main()

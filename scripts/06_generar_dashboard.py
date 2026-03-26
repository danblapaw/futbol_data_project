"""
PASO 6 — Generar Dashboard HTML con Datos Reales
==================================================
Lee tu base de datos futbol.db y genera un archivo HTML
completamente funcional con todos los gráficos y estadísticas.

NO necesita internet, NO necesita librerías externas.
El resultado es un único archivo HTML que puedes abrir en Chrome.

Ejecutar con:
    python scripts/06_generar_dashboard.py

Resultado:
    data_clean/dashboard.html  ← ábrelo en Chrome con doble clic
"""

import sqlite3
import os
import json

# ─────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.path.join(BASE_DIR, "db", "futbol.db")
CLEAN_DIR = os.path.join(BASE_DIR, "data_clean")
OUTPUT    = os.path.join(CLEAN_DIR, "dashboard.html")

os.makedirs(CLEAN_DIR, exist_ok=True)


def extraer_datos(db_path: str) -> dict:
    """
    Lee la base de datos y devuelve todos los datos necesarios para el dashboard.
    """
    print(f"📂 Leyendo: {db_path}")

    with sqlite3.connect(db_path) as conn:

        # ── Totales globales ────────────────────────────────────────────
        t = conn.execute("""
            SELECT
                COUNT(*)                                                                    AS total,
                COUNT(DISTINCT liga)                                                        AS n_ligas,
                COUNT(DISTINCT temporada)                                                   AS n_temps,
                ROUND(AVG(total_goles), 2)                                                  AS media_goles,
                ROUND(AVG(over_2_5) * 100, 1)                                              AS pct_over25,
                ROUND(AVG(ambos_marcan) * 100, 1)                                          AS pct_btts,
                ROUND(AVG(total_corners), 1)                                               AS media_corners,
                ROUND(AVG(CASE WHEN goles_local > goles_visitante THEN 1.0 ELSE 0 END)*100,1) AS pct_local,
                ROUND(AVG(CASE WHEN goles_local = goles_visitante THEN 1.0 ELSE 0 END)*100,1) AS pct_empate,
                ROUND(AVG(CASE WHEN goles_local < goles_visitante THEN 1.0 ELSE 0 END)*100,1) AS pct_visit
            FROM partidos
        """).fetchone()

        total, n_ligas, n_temps = int(t[0]), int(t[1]), int(t[2])
        media_goles, pct_over25, pct_btts = float(t[3]), float(t[4]), float(t[5])
        media_corners = float(t[6])
        pct_local, pct_empate, pct_visit = float(t[7]), float(t[8]), float(t[9])

        # ── Lines over/under ────────────────────────────────────────────
        ln = conn.execute("""
            SELECT
                ROUND(AVG(CASE WHEN total_goles >= 1 THEN 1.0 ELSE 0 END)*100,1),
                ROUND(AVG(CASE WHEN total_goles >= 2 THEN 1.0 ELSE 0 END)*100,1),
                ROUND(AVG(over_2_5)*100,1),
                ROUND(AVG(CASE WHEN total_goles >= 4 THEN 1.0 ELSE 0 END)*100,1),
                ROUND(AVG(CASE WHEN total_goles >= 5 THEN 1.0 ELSE 0 END)*100,1)
            FROM partidos
        """).fetchone()
        lines = [float(x) for x in ln]

        # ── Distribución de goles ───────────────────────────────────────
        rows = conn.execute("""
            SELECT total_goles, COUNT(*) FROM partidos
            WHERE total_goles BETWEEN 0 AND 9
            GROUP BY total_goles ORDER BY total_goles
        """).fetchall()
        goles_dist = [{"g": int(r[0]), "n": int(r[1])} for r in rows]

        # ── Estadísticas por liga ───────────────────────────────────────
        rows = conn.execute("""
            SELECT
                liga, COUNT(*) AS p,
                ROUND(AVG(total_goles),2)          AS goles,
                ROUND(AVG(over_2_5)*100,1)         AS ov25,
                ROUND(AVG(ambos_marcan)*100,1)     AS btts,
                ROUND(AVG(total_corners),1)        AS corn,
                ROUND(AVG(CASE WHEN goles_local > goles_visitante THEN 1.0 ELSE 0 END)*100,1) AS local,
                ROUND(AVG(CASE WHEN goles_local = goles_visitante THEN 1.0 ELSE 0 END)*100,1) AS empate,
                ROUND(AVG(CASE WHEN goles_local < goles_visitante THEN 1.0 ELSE 0 END)*100,1) AS visit
            FROM partidos
            GROUP BY liga
            ORDER BY ov25 DESC
        """).fetchall()
        ligas_data = [
            {"name": r[0], "p": int(r[1]), "goles": float(r[2]),
             "ov25": float(r[3]), "btts": float(r[4]), "corn": float(r[5]),
             "local": float(r[6]), "empate": float(r[7]), "visit": float(r[8])}
            for r in rows
        ]

        # ── Top equipos por goles anotados ──────────────────────────────
        rows = conn.execute("""
            SELECT equipo,
                ROUND(SUM(ga)*1.0/SUM(n),2)    AS goles,
                ROUND(SUM(ov)*100.0/SUM(n),1)  AS ov25,
                SUM(n) AS total
            FROM (
                SELECT equipo_local   AS equipo, SUM(goles_local)     AS ga,
                       SUM(over_2_5) AS ov, COUNT(*) AS n
                FROM partidos GROUP BY equipo_local
                UNION ALL
                SELECT equipo_visitante, SUM(goles_visitante),
                       SUM(over_2_5), COUNT(*)
                FROM partidos GROUP BY equipo_visitante
            )
            GROUP BY equipo
            HAVING total >= 30
            ORDER BY goles DESC
            LIMIT 10
        """).fetchall()
        equipos = [{"name": r[0], "goles": float(r[1]), "ov25": float(r[2])} for r in rows]

        # ── Evolución por temporada ──────────────────────────────────────
        rows = conn.execute("""
            SELECT temporada,
                ROUND(AVG(over_2_5)*100,1)     AS ov25,
                ROUND(AVG(ambos_marcan)*100,1) AS btts,
                ROUND(AVG(total_goles),2)       AS goles
            FROM partidos
            GROUP BY temporada
            ORDER BY temporada
        """).fetchall()
        temporadas = [{"t": r[0], "ov25": float(r[1]), "btts": float(r[2]), "goles": float(r[3])} for r in rows]

    print(f"✅ {total:,} partidos | {n_ligas} ligas | {n_temps} temporadas")
    print(f"   Media goles: {media_goles} | Over 2.5: {pct_over25}% | BTTS: {pct_btts}%")

    return {
        "total": total, "n_ligas": n_ligas, "n_temps": n_temps,
        "media_goles": media_goles, "pct_over25": pct_over25,
        "pct_btts": pct_btts, "media_corners": media_corners,
        "pct_local": pct_local, "pct_empate": pct_empate, "pct_visit": pct_visit,
        "lines": lines, "goles_dist": goles_dist,
        "ligas_data": ligas_data, "equipos": equipos, "temporadas": temporadas,
    }


def generar_html(d: dict) -> str:
    """
    Genera el HTML completo del dashboard con los datos inyectados.
    d = diccionario devuelto por extraer_datos()
    """

    # Formatear goles para el KPI (split en entero + decimal)
    g_split    = f"{d['media_goles']:.2f}".split(".")
    corn_split = f"{d['media_corners']:.1f}".split(".")

    # JSON para inyectar en el JS
    data_js = json.dumps({
        "total":        d["total"],
        "ligas":        d["n_ligas"],
        "temps":        d["n_temps"],
        "media_goles":  d["media_goles"],
        "pct_over25":   d["pct_over25"],
        "pct_btts":     d["pct_btts"],
        "media_corners":d["media_corners"],
        "pct_local":    d["pct_local"],
        "pct_empate":   d["pct_empate"],
        "pct_visit":    d["pct_visit"],
        "lines":        d["lines"],
        "golesDist":    d["goles_dist"],
        "ligas_data":   d["ligas_data"],
        "equipos":      d["equipos"],
        "temporadas":   d["temporadas"],
    }, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Football Analytics Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;400;600;700;800;900&family=Barlow:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#07090d;--bg2:#0c1118;--bg3:#111820;--card:#0f1820;--card2:#131f2a;
  --border:#1a2a38;--border2:#243447;
  --green:#00e676;--green2:#00c853;--gdim:rgba(0,230,118,0.09);--gglow:rgba(0,230,118,0.22);
  --cyan:#29d9f5;--amber:#ffb300;--red:#ff5252;
  --text:#ddeaf5;--text2:#7a9bb5;--text3:#3d5870;
  --fh:'Barlow Condensed',sans-serif;--fb:'Barlow',sans-serif;--fm:'JetBrains Mono',monospace;
}}
body{{background:var(--bg);color:var(--text);font-family:var(--fb);min-height:100vh;overflow-x:hidden}}
body::before{{content:'';position:fixed;inset:0;
  background:repeating-linear-gradient(0deg,transparent,transparent 59px,rgba(0,230,118,.012) 59px,rgba(0,230,118,.012) 60px),
             repeating-linear-gradient(90deg,transparent,transparent 59px,rgba(0,230,118,.007) 59px,rgba(0,230,118,.007) 60px);
  pointer-events:none;z-index:0}}
header{{position:relative;z-index:10;padding:20px 36px;border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,rgba(0,230,118,.05) 0%,transparent 100%);
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
.logo{{display:flex;align-items:center;gap:14px}}
.logo-icon{{width:40px;height:40px;background:var(--green);border-radius:8px;
  display:flex;align-items:center;justify-content:center;font-size:20px;
  box-shadow:0 0 22px var(--gglow);flex-shrink:0}}
.logo h1{{font-family:var(--fh);font-size:24px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#fff;line-height:1}}
.logo h1 span{{color:var(--green)}}
.logo-sub{{font-family:var(--fm);font-size:10px;color:var(--text3);margin-top:3px;letter-spacing:.06em}}
.hpills{{display:flex;gap:7px;flex-wrap:wrap}}
.pill{{font-family:var(--fm);font-size:10px;padding:5px 11px;border-radius:20px;
  border:1px solid var(--border2);color:var(--text2);background:var(--card);letter-spacing:.04em}}
.pill.g{{border-color:rgba(0,230,118,.4);color:var(--green);background:var(--gdim)}}
main{{position:relative;z-index:1;max-width:1380px;margin:0 auto;padding:28px 36px 60px;
  display:flex;flex-direction:column;gap:24px}}
.slabel{{font-family:var(--fh);font-size:10px;font-weight:700;letter-spacing:.2em;
  text-transform:uppercase;color:var(--text3);margin-bottom:12px;display:flex;align-items:center;gap:8px}}
.slabel::before{{content:'';display:block;width:16px;height:2px;background:var(--green)}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:22px}}
.ctitle{{font-family:var(--fh);font-size:13px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--text);margin-bottom:3px}}
.csub{{font-family:var(--fm);font-size:9px;color:var(--text3);letter-spacing:.05em;margin-bottom:18px}}
.kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}
.kpi{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:20px 22px;
  position:relative;overflow:hidden;transition:border-color .2s,transform .2s;cursor:default}}
.kpi:hover{{border-color:var(--border2);transform:translateY(-2px)}}
.kpi::after{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,var(--green),transparent);opacity:0;transition:opacity .2s}}
.kpi:hover::after{{opacity:1}}
.kico{{font-size:18px;margin-bottom:10px;opacity:.7}}
.kval{{font-family:var(--fh);font-size:44px;font-weight:900;line-height:1;color:#fff}}
.kval .u{{font-size:20px;color:var(--green);font-weight:700}}
.kval .p{{font-size:22px;color:var(--text2)}}
.klabel{{font-family:var(--fh);font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text2);margin-top:5px}}
.ksub{{font-family:var(--fm);font-size:10px;color:var(--text3);margin-top:6px}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.g31{{display:grid;grid-template-columns:2fr 1fr;gap:18px}}
.rbar{{display:flex;height:42px;border-radius:7px;overflow:hidden;margin:14px 0 10px}}
.rseg{{display:flex;align-items:center;justify-content:center;
  font-family:var(--fh);font-size:13px;font-weight:800;letter-spacing:.03em;transition:flex .8s}}
.rseg.l{{background:var(--green);color:#07090d}}
.rseg.x{{background:#14222e;color:var(--text2);border-left:1px solid var(--border2);border-right:1px solid var(--border2)}}
.rseg.v{{background:#0d1e2c;color:var(--cyan)}}
.rlegend{{display:flex;gap:16px;font-family:var(--fm);font-size:10px;color:var(--text3)}}
.dot{{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px;vertical-align:middle}}
.ougrid{{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin-top:4px}}
.oucell{{background:var(--card2);border:1px solid var(--border);border-radius:7px;padding:13px 8px;text-align:center}}
.ouline{{font-family:var(--fh);font-size:16px;font-weight:700;color:var(--text2)}}
.oupct{{font-family:var(--fh);font-size:24px;font-weight:900;color:#fff;margin:3px 0}}
.oupct.hi{{color:var(--green)}}.oupct.me{{color:var(--amber)}}.oupct.lo{{color:var(--red)}}
.oulbl{{font-family:var(--fm);font-size:9px;color:var(--text3);letter-spacing:.05em}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{font-family:var(--fh);font-size:9px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;
  color:var(--text3);padding:7px 10px;text-align:left;border-bottom:1px solid var(--border)}}
tbody tr{{border-bottom:1px solid rgba(26,42,56,.5);transition:background .15s}}
tbody tr:hover{{background:rgba(0,230,118,.035)}}
tbody tr:last-child{{border-bottom:none}}
td{{padding:10px 10px;color:var(--text)}}
td.lname{{font-family:var(--fh);font-size:14px;font-weight:700;letter-spacing:.03em;color:#fff}}
td.mono{{font-family:var(--fm);font-size:11px;color:var(--text2)}}
.bwrap{{display:flex;align-items:center;gap:7px}}
.btrack{{flex:1;height:4px;background:var(--bg3);border-radius:2px;overflow:hidden;min-width:60px}}
.bfill{{height:100%;border-radius:2px;background:var(--green)}}
.bfill.c{{background:var(--cyan)}}.bfill.a{{background:var(--amber)}}.bfill.d{{background:var(--text3)}}
.bval{{font-family:var(--fm);font-size:11px;color:var(--text);min-width:36px;text-align:right}}
.teamlist{{display:flex;flex-direction:column;gap:7px}}
.trow{{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:7px;
  background:var(--card2);border:1px solid var(--border);transition:border-color .2s}}
.trow:hover{{border-color:rgba(0,230,118,.2);background:rgba(0,230,118,.03)}}
.trank{{font-family:var(--fm);font-size:10px;color:var(--text3);min-width:16px}}
.tname{{font-family:var(--fh);font-size:13px;font-weight:700;flex:1;color:var(--text);letter-spacing:.02em}}
.tstat{{font-family:var(--fm);font-size:12px;color:var(--green);min-width:34px;text-align:right}}
.tmbar{{width:52px;height:3px;background:var(--bg);border-radius:2px;overflow:hidden}}
.tmfill{{height:100%;background:linear-gradient(90deg,var(--green2),var(--green));border-radius:2px}}
.sgrid{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}}
.scard{{background:var(--card2);border:1px solid var(--border);border-radius:8px;padding:15px 15px 12px}}
.ssea{{font-family:var(--fh);font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--text3);text-transform:uppercase;margin-bottom:7px}}
.sval{{font-family:var(--fh);font-size:30px;font-weight:900;color:#fff;line-height:1}}
.su{{font-family:var(--fm);font-size:10px;color:var(--text3)}}
.ssub{{font-family:var(--fm);font-size:10px;color:var(--text2);margin-top:2px}}
.smbar{{margin-top:9px;height:3px;background:var(--border);border-radius:2px;overflow:hidden}}
.smfill{{height:100%;background:var(--green);border-radius:2px}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:translateY(0)}}}}
.kpi{{animation:fadeUp .45s ease both}}
.kpi:nth-child(1){{animation-delay:.05s}}.kpi:nth-child(2){{animation-delay:.1s}}
.kpi:nth-child(3){{animation-delay:.15s}}.kpi:nth-child(4){{animation-delay:.2s}}
.card{{animation:fadeUp .45s ease .22s both}}
@media(max-width:1080px){{
  main{{padding:20px 20px 48px}}
  .kpi-row{{grid-template-columns:repeat(2,1fr)}}
  .g2,.g31{{grid-template-columns:1fr}}
  .sgrid{{grid-template-columns:repeat(3,1fr)}}
}}
@media(max-width:640px){{
  .kpi-row{{grid-template-columns:1fr 1fr}}
  .sgrid{{grid-template-columns:1fr 1fr}}
  .ougrid{{grid-template-columns:repeat(3,1fr)}}
  header{{flex-direction:column;align-items:flex-start}}
}}
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">⚽</div>
    <div>
      <h1>Football <span>Analytics</span></h1>
      <div class="logo-sub">SISTEMA DE ANÁLISIS ESTADÍSTICO · DATOS HISTÓRICOS</div>
    </div>
  </div>
  <div class="hpills">
    <span class="pill g">● DATOS CARGADOS</span>
    <span class="pill" id="pill-ligas"></span>
    <span class="pill" id="pill-temps"></span>
    <span class="pill" id="pill-total"></span>
  </div>
</header>

<main>
  <div>
    <div class="slabel">Resumen Global</div>
    <div class="kpi-row">
      <div class="kpi"><div class="kico">⚽</div><div class="kval" id="kv-goles"></div><div class="klabel">Goles por partido</div><div class="ksub">Media histórica · todas las ligas</div></div>
      <div class="kpi"><div class="kico">📈</div><div class="kval" id="kv-over"></div><div class="klabel">Over 2.5 goles</div><div class="ksub">Porcentaje global de partidos</div></div>
      <div class="kpi"><div class="kico">🎯</div><div class="kval" id="kv-btts"></div><div class="klabel">Ambos marcan (BTTS)</div><div class="ksub">Both Teams To Score</div></div>
      <div class="kpi"><div class="kico">🚩</div><div class="kval" id="kv-corn"></div><div class="klabel">Corners por partido</div><div class="ksub">Media corners totales</div></div>
    </div>
  </div>

  <div class="g2">
    <div class="card">
      <div class="ctitle">Distribución de Goles por Partido</div>
      <div class="csub">FRECUENCIA RELATIVA · TODAS LAS LIGAS Y TEMPORADAS</div>
      <div id="chartGoles"></div>
    </div>
    <div class="card">
      <div class="ctitle">Resultado Final (1 · X · 2)</div>
      <div class="csub">DISTRIBUCIÓN GLOBAL</div>
      <div class="rbar">
        <div class="rseg l" id="seg-l"></div>
        <div class="rseg x" id="seg-x"></div>
        <div class="rseg v" id="seg-v"></div>
      </div>
      <div class="rlegend">
        <span><span class="dot" style="background:var(--green)"></span>Victoria local</span>
        <span><span class="dot" style="background:var(--text3)"></span>Empate</span>
        <span><span class="dot" style="background:var(--cyan)"></span>Victoria visitante</span>
      </div>
      <div style="margin-top:22px">
        <div class="ctitle">Lines Over / Under</div>
        <div class="csub">PORCENTAJE GLOBAL POR LÍNEA DE APUESTA</div>
        <div class="ougrid" id="ouGrid"></div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="ctitle">Comparativa por Liga</div>
    <div class="csub">ESTADÍSTICAS CLAVE · ORDENADO POR % OVER 2.5</div>
    <table><thead><tr>
      <th>Liga</th><th>Partidos</th><th>Over 2.5</th><th>BTTS</th>
      <th>Media Goles</th><th>Media Corners</th>
      <th>Victoria Local</th><th>Empate</th><th>Victoria Visit.</th>
    </tr></thead><tbody id="leagueTbody"></tbody></table>
  </div>

  <div class="g31">
    <div class="card">
      <div class="ctitle">Over 2.5 &amp; BTTS por Liga</div>
      <div class="csub">COMPARATIVA VISUAL · PRINCIPALES LIGAS EUROPEAS</div>
      <div id="chartLigas"></div>
    </div>
    <div class="card">
      <div class="ctitle">Top Equipos</div>
      <div class="csub">MEDIA GOLES ANOTADOS / PARTIDO</div>
      <div class="teamlist" id="teamList"></div>
    </div>
  </div>

  <div>
    <div class="slabel">Evolución Histórica por Temporada</div>
    <div class="sgrid" id="seasonGrid"></div>
  </div>

  <div class="card">
    <div class="ctitle">Tendencia Over 2.5 &amp; BTTS por Temporada</div>
    <div class="csub">EVOLUCIÓN HISTÓRICA · PORCENTAJE DE PARTIDOS</div>
    <div id="chartTrend"></div>
  </div>
</main>

<footer style="position:relative;z-index:1;text-align:center;padding:16px 36px 28px;
  font-family:var(--fm);font-size:10px;color:var(--text3);border-top:1px solid var(--border);letter-spacing:.06em">
  FOOTBALL ANALYTICS · FUENTE: FOOTBALL-DATA.CO.UK · PYTHON + SQLITE + PANDAS
</footer>

<script>
// ════════════════════════════════════════════════════════════════
//  DATOS REALES — generados automáticamente desde futbol.db
// ════════════════════════════════════════════════════════════════
const D = {data_js};

// ════════════════════════════════════════════════════════════════
//  SVG HELPER — dibuja gráficos sin librerías externas
// ════════════════════════════════════════════════════════════════
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs, parent) {{
  const e = document.createElementNS(NS, tag);
  for (const [k,v] of Object.entries(attrs||{{}})) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}}
function mkSvg(w, h) {{
  return el('svg', {{viewBox:`0 0 ${{w}} ${{h}}`, width:'100%', height:h, xmlns:NS}});
}}

// ── Colores por número de goles
function barColor(g) {{
  if (g <= 1) return 'rgba(255,82,82,0.82)';
  if (g <= 2) return 'rgba(255,179,0,0.82)';
  if (g == 3) return 'rgba(255,220,0,0.75)';
  return 'rgba(0,230,118,0.82)';
}}

// ════════════════════════════════════════════════════════════════
//  GRÁFICO 1 — Distribución de goles (barras verticales)
// ════════════════════════════════════════════════════════════════
function buildGolesChart() {{
  const W=540, H=190, PL=38, PR=8, PT=12, PB=34;
  const cW=W-PL-PR, cH=H-PT-PB;
  const data=D.golesDist;
  const total=data.reduce((s,d)=>s+d.n,0);
  const vals=data.map(d=>(d.n/total)*100);
  const maxV=Math.max(...vals);
  const gap=cW/data.length;
  const barW=gap*0.68;
  const s=mkSvg(W,H);

  // grid lines
  [0,10,20,30].forEach(pct => {{
    if (pct > maxV+3) return;
    const y = PT + cH - (pct/maxV)*cH;
    el('line',{{x1:PL,y1:y,x2:W-PR,y2:y,stroke:'rgba(255,255,255,0.05)',
      'stroke-width':1,'stroke-dasharray':'3 5'}},s);
    el('text',{{x:PL-4,y:y+4,'text-anchor':'end',fill:'#3d5870',
      'font-size':9,'font-family':'JetBrains Mono,monospace'}},s).textContent=pct+'%';
  }});

  data.forEach((d,i) => {{
    const pct=vals[i];
    const barH=(pct/maxV)*cH;
    const x=PL+i*gap+(gap-barW)/2;
    const y=PT+cH-barH;
    const r=el('rect',{{x,y,width:barW,height:barH,fill:barColor(d.g),rx:3}},s);
    r.style.transformOrigin=`${{x+barW/2}}px ${{PT+cH}}px`;
    r.style.transform='scaleY(0)';
    r.style.transition=`transform 0.65s cubic-bezier(0.22,1,0.36,1) ${{i*0.055}}s`;
    setTimeout(()=>{{ r.style.transform='scaleY(1)'; }}, 60);
    el('text',{{x:x+barW/2,y:y-4,'text-anchor':'middle',fill:'rgba(255,255,255,0.55)',
      'font-size':8.5,'font-family':'JetBrains Mono,monospace'}},s).textContent=pct.toFixed(1)+'%';
    el('text',{{x:x+barW/2,y:H-7,'text-anchor':'middle',fill:'#7a9bb5',
      'font-size':10,'font-family':'JetBrains Mono,monospace'}},s).textContent=d.g;
  }});

  el('text',{{x:PL+cW/2,y:H-1,'text-anchor':'middle',fill:'#3d5870',
    'font-size':9,'font-family':'JetBrains Mono,monospace'}},s).textContent='goles en el partido';
  document.getElementById('chartGoles').appendChild(s);
}}

// ════════════════════════════════════════════════════════════════
//  GRÁFICO 2 — Over 2.5 & BTTS por liga (barras horizontales)
// ════════════════════════════════════════════════════════════════
function buildLigasChart() {{
  const ligas=D.ligas_data;
  const W=620, rowH=46, PL=110, PR=56, PT=14, PB=22;
  const H=PT+ligas.length*rowH+PB;
  const cW=W-PL-PR, maxV=95, bH=11;
  const s=mkSvg(W,H);

  // grid vertical
  [70,75,80,85,90,95].forEach(v => {{
    const x=PL+(v/maxV)*cW;
    el('line',{{x1:x,y1:PT,x2:x,y2:H-PB,stroke:'rgba(255,255,255,0.05)',
      'stroke-width':1,'stroke-dasharray':'3 5'}},s);
    el('text',{{x,y:H-PB+12,'text-anchor':'middle',fill:'#3d5870',
      'font-size':9,'font-family':'JetBrains Mono,monospace'}},s).textContent=v+'%';
  }});

  ligas.forEach((lg,i) => {{
    const y=PT+i*rowH;
    el('text',{{x:PL-8,y:y+rowH/2+5,'text-anchor':'end',fill:'#ddeaf5',
      'font-size':11,'font-family':'Barlow Condensed,sans-serif','font-weight':700}},s)
      .textContent=lg.name.replace('Premier League','Premier');

    // Over 2.5
    const r1=el('rect',{{x:PL,y:y+rowH/2-bH-2,width:(lg.ov25/maxV)*cW,height:bH,
      fill:'rgba(0,230,118,0.78)',rx:3}},s);
    r1.style.transformOrigin=`${{PL}}px ${{y+rowH/2}}px`;
    r1.style.transform='scaleX(0)';
    r1.style.transition=`transform 0.65s cubic-bezier(0.22,1,0.36,1) ${{i*0.07}}s`;
    setTimeout(()=>{{ r1.style.transform='scaleX(1)'; }},80);
    el('text',{{x:PL+(lg.ov25/maxV)*cW+5,y:y+rowH/2-2,'text-anchor':'start',fill:'#00e676',
      'font-size':10,'font-family':'JetBrains Mono,monospace','font-weight':700}},s)
      .textContent=lg.ov25+'%';

    // BTTS
    const r2=el('rect',{{x:PL,y:y+rowH/2+2,width:(lg.btts/maxV)*cW,height:bH,
      fill:'rgba(41,217,245,0.55)',rx:3}},s);
    r2.style.transformOrigin=`${{PL}}px ${{y+rowH/2}}px`;
    r2.style.transform='scaleX(0)';
    r2.style.transition=`transform 0.65s cubic-bezier(0.22,1,0.36,1) ${{i*0.07+0.04}}s`;
    setTimeout(()=>{{ r2.style.transform='scaleX(1)'; }},80);
    el('text',{{x:PL+(lg.btts/maxV)*cW+5,y:y+rowH/2+14,'text-anchor':'start',fill:'#29d9f5',
      'font-size':10,'font-family':'JetBrains Mono,monospace'}},s).textContent=lg.btts+'%';
  }});

  // leyenda
  el('rect',{{x:W-PR+4,y:PT+4,width:10,height:4,fill:'rgba(0,230,118,0.78)',rx:2}},s);
  el('text',{{x:W-PR+16,y:PT+9,fill:'#7a9bb5','font-size':9,'font-family':'JetBrains Mono,monospace'}},s).textContent='O2.5';
  el('rect',{{x:W-PR+4,y:PT+16,width:10,height:4,fill:'rgba(41,217,245,0.55)',rx:2}},s);
  el('text',{{x:W-PR+16,y:PT+21,fill:'#7a9bb5','font-size':9,'font-family':'JetBrains Mono,monospace'}},s).textContent='BTTS';

  document.getElementById('chartLigas').appendChild(s);
}}

// ════════════════════════════════════════════════════════════════
//  GRÁFICO 3 — Tendencia por temporada (líneas)
// ════════════════════════════════════════════════════════════════
function buildTrendChart() {{
  const temps=D.temporadas;
  if (!temps || temps.length < 2) return;
  const W=880, H=185, PL=44, PR=20, PT=18, PB=30;
  const cW=W-PL-PR, cH=H-PT-PB;

  // calcular rango dinámico
  const allVals=[...temps.map(t=>t.ov25),...temps.map(t=>t.btts)];
  const dataMin=Math.floor(Math.min(...allVals))-2;
  const dataMax=Math.ceil(Math.max(...allVals))+2;

  function px(i) {{ return PL+(i/(temps.length-1))*cW; }}
  function py(v) {{ return PT+cH-((v-dataMin)/(dataMax-dataMin))*cH; }}

  const s=mkSvg(W,H);

  // grid
  for(let v=dataMin; v<=dataMax; v+=2) {{
    const y=py(v);
    el('line',{{x1:PL,y1:y,x2:W-PR,y2:y,stroke:'rgba(255,255,255,0.05)',
      'stroke-width':1,'stroke-dasharray':'3 5'}},s);
    el('text',{{x:PL-5,y:y+4,'text-anchor':'end',fill:'#3d5870',
      'font-size':9,'font-family':'JetBrains Mono,monospace'}},s).textContent=v+'%';
  }}

  // área
  function area(vals,color) {{
    const pts=vals.map((v,i)=>`${{px(i)}},${{py(v)}}`).join(' ');
    const b=py(dataMin);
    el('polygon',{{points:`${{PL}},${{b}} ${{pts}} ${{px(vals.length-1)}},${{b}}`,
      fill:`rgba(${{color}},0.07)`}},s);
  }}
  area(temps.map(t=>t.ov25),'0,230,118');
  area(temps.map(t=>t.btts),'41,217,245');

  // líneas
  function linia(vals,stroke) {{
    for(let i=0;i<vals.length-1;i++)
      el('line',{{x1:px(i),y1:py(vals[i]),x2:px(i+1),y2:py(vals[i+1]),
        stroke,'stroke-width':2.5,'stroke-linecap':'round'}},s);
  }}
  linia(temps.map(t=>t.ov25),'#00e676');
  linia(temps.map(t=>t.btts),'#29d9f5');

  // puntos y etiquetas
  temps.forEach((t,i) => {{
    el('circle',{{cx:px(i),cy:py(t.ov25),r:4.5,fill:'#00e676',stroke:'#07090d','stroke-width':2}},s);
    el('text',{{x:px(i),y:py(t.ov25)-9,'text-anchor':'middle',fill:'#00e676',
      'font-size':9,'font-family':'JetBrains Mono,monospace'}},s).textContent=t.ov25+'%';
    el('circle',{{cx:px(i),cy:py(t.btts),r:4,fill:'#29d9f5',stroke:'#07090d','stroke-width':2}},s);
    el('text',{{x:px(i),y:H-4,'text-anchor':'middle',fill:'#7a9bb5',
      'font-size':10,'font-family':'Barlow Condensed,sans-serif','font-weight':600,
      'letter-spacing':'0.04em'}},s).textContent=t.t;
  }});

  // leyenda
  el('circle',{{cx:PL+10,cy:PT-4,r:4,fill:'#00e676'}},s);
  el('text',{{x:PL+17,y:PT,fill:'#7a9bb5','font-size':9,'font-family':'JetBrains Mono,monospace'}},s).textContent='Over 2.5';
  el('circle',{{cx:PL+82,cy:PT-4,r:4,fill:'#29d9f5'}},s);
  el('text',{{x:PL+89,y:PT,fill:'#7a9bb5','font-size':9,'font-family':'JetBrains Mono,monospace'}},s).textContent='BTTS';

  document.getElementById('chartTrend').appendChild(s);
}}

// ════════════════════════════════════════════════════════════════
//  INICIALIZAR DOM
// ════════════════════════════════════════════════════════════════
function init() {{
  // KPIs
  const g=D.media_goles.toFixed(2).split('.');
  document.getElementById('kv-goles').innerHTML=`${{g[0]}}<span class="u">.${{g[1]}}</span>`;
  document.getElementById('kv-over').innerHTML=`${{Math.round(D.pct_over25)}}<span class="p">%</span>`;
  document.getElementById('kv-btts').innerHTML=`${{Math.round(D.pct_btts)}}<span class="p">%</span>`;
  const c=D.media_corners.toFixed(1).split('.');
  document.getElementById('kv-corn').innerHTML=`${{c[0]}}<span class="u">.${{c[1]}}</span>`;

  // Pills
  document.getElementById('pill-ligas').textContent=`${{D.ligas}} LIGAS`;
  document.getElementById('pill-temps').textContent=`${{D.temps}} TEMPORADAS`;
  document.getElementById('pill-total').textContent=`${{D.total.toLocaleString('es-ES')}} PARTIDOS`;

  // Resultado 1X2
  const sl=document.getElementById('seg-l');
  const sx=document.getElementById('seg-x');
  const sv=document.getElementById('seg-v');
  sl.style.flex=D.pct_local; sl.textContent=D.pct_local+'%';
  sx.style.flex=D.pct_empate; sx.textContent=D.pct_empate+'%';
  sv.style.flex=D.pct_visit; sv.textContent=D.pct_visit+'%';

  // Over/Under cells
  const lineLabels=['0.5','1.5','2.5','3.5','4.5'];
  document.getElementById('ouGrid').innerHTML=D.lines.map((v,i)=>{{
    const cls=v>=85?'hi':v>=60?'me':'lo';
    return `<div class="oucell"><div class="ouline">${{lineLabels[i]}}</div>
      <div class="oupct ${{cls}}">${{v}}%</div>
      <div class="oulbl">Over ${{lineLabels[i]}}</div></div>`;
  }}).join('');

  // Tabla de ligas
  const maxOv=Math.max(...D.ligas_data.map(l=>l.ov25));
  const maxBt=Math.max(...D.ligas_data.map(l=>l.btts));
  const maxGl=Math.max(...D.ligas_data.map(l=>l.goles));
  const maxCn=Math.max(...D.ligas_data.map(l=>l.corn));
  document.getElementById('leagueTbody').innerHTML=D.ligas_data.map(l=>`
    <tr>
      <td class="lname">${{l.name}}</td>
      <td class="mono">${{l.p.toLocaleString('es-ES')}}</td>
      <td><div class="bwrap"><div class="btrack"><div class="bfill" style="width:${{(l.ov25/maxOv*100).toFixed(0)}}%"></div></div><span class="bval">${{l.ov25}}%</span></div></td>
      <td><div class="bwrap"><div class="btrack"><div class="bfill c" style="width:${{(l.btts/maxBt*100).toFixed(0)}}%"></div></div><span class="bval">${{l.btts}}%</span></div></td>
      <td><div class="bwrap"><div class="btrack"><div class="bfill a" style="width:${{(l.goles/maxGl*100).toFixed(0)}}%"></div></div><span class="bval">${{l.goles}}</span></div></td>
      <td><div class="bwrap"><div class="btrack"><div class="bfill d" style="width:${{(l.corn/maxCn*100).toFixed(0)}}%"></div></div><span class="bval">${{l.corn}}</span></div></td>
      <td class="mono" style="color:var(--green)">${{l.local}}%</td>
      <td class="mono">${{l.empate}}%</td>
      <td class="mono" style="color:var(--cyan)">${{l.visit}}%</td>
    </tr>`).join('');

  // Top equipos
  const maxG2=D.equipos[0].goles;
  document.getElementById('teamList').innerHTML=D.equipos.slice(0,8).map((t,i)=>`
    <div class="trow">
      <span class="trank">${{String(i+1).padStart(2,'0')}}</span>
      <span class="tname">${{t.name}}</span>
      <span class="tstat">${{t.goles}}</span>
      <div class="tmbar"><div class="tmfill" style="width:${{(t.goles/maxG2*100).toFixed(0)}}%"></div></div>
    </div>`).join('');

  // Season cards
  const maxOvT=Math.max(...D.temporadas.map(t=>t.ov25));
  document.getElementById('seasonGrid').innerHTML=D.temporadas.map(t=>`
    <div class="scard">
      <div class="ssea">${{t.t}}</div>
      <div class="sval">${{t.ov25}}<span class="su">%</span></div>
      <div class="ssub">Over 2.5 · ${{t.goles}} goles/p</div>
      <div class="smbar"><div class="smfill" style="width:${{(t.ov25/maxOvT*100).toFixed(0)}}%"></div></div>
    </div>`).join('');

  // SVG Charts
  buildGolesChart();
  buildLigasChart();
  buildTrendChart();
}}

document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>"""

    return html


def main():
    # 1. Verificar DB
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró: {DB_PATH}")
        print("   Ejecuta primero los scripts 01 al 04.")
        return

    # 2. Extraer datos
    datos = extraer_datos(DB_PATH)

    # 3. Generar HTML
    html = generar_html(datos)

    # 4. Guardar
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"\n✅ Dashboard generado: {OUTPUT}")
    print(f"   Tamaño: {size_kb:.0f} KB")
    print(f"\n🌐 Para verlo:")
    print(f"   Abre el Explorador de archivos → carpeta data_clean/")
    print(f"   Haz doble clic en:  dashboard.html")


if __name__ == "__main__":
    main()

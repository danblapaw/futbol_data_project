"""
PASO 5 — Análisis Estadístico
==============================
Calcula estadísticas de fútbol útiles para análisis de apuestas:
- Promedio de goles por equipo (local y visitante)
- Porcentaje de Over 2.5
- Porcentaje de ambos equipos marcan (BTTS)
- Promedio de corners por equipo
- Ranking de equipos más atacantes / defensivos

Ejecutar con:
    python scripts/05_estadisticas.py

Resultados exportados a: data_clean/estadisticas_*.csv
"""

import sqlite3
import pandas as pd
import numpy as np
import os
import logging

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE RUTAS
# ─────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.path.join(BASE_DIR, "db", "futbol.db")
CLEAN_DIR = os.path.join(BASE_DIR, "data_clean")
LOGS_DIR  = os.path.join(BASE_DIR, "logs")

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "estadisticas.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def cargar_datos(liga: str = None, temporada: str = None) -> pd.DataFrame:
    """
    Carga partidos de la base de datos.
    
    Parámetros opcionales para filtrar:
        liga      = ej: "La Liga" (None = todas las ligas)
        temporada = ej: "2023-24" (None = todas las temporadas)
    
    Devuelve un DataFrame con todos los partidos.
    """
    condiciones = []
    params      = []

    if liga:
        condiciones.append("liga = ?")
        params.append(liga)
    if temporada:
        condiciones.append("temporada = ?")
        params.append(temporada)

    # Construimos la cláusula WHERE dinámicamente
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    sql = f"""
        SELECT *
        FROM partidos
        {where}
        ORDER BY fecha
    """

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(sql, conn, params=params)

    log.info(f"📂 Cargados {len(df):,} partidos")
    return df


def estadisticas_generales(df: pd.DataFrame) -> dict:
    """
    Calcula estadísticas globales del conjunto de datos.
    
    Devuelve un diccionario con todos los resultados.
    """
    if df.empty:
        return {}

    stats = {
        "total_partidos"      : len(df),
        "ligas_distintas"     : df["liga"].nunique(),          # nunique = número de valores únicos
        "temporadas_distintas": df["temporada"].nunique(),
        "equipos_distintos"   : pd.concat([df["equipo_local"], df["equipo_visitante"]]).nunique(),

        # Goles
        "media_goles_partido" : round(df["total_goles"].mean(), 3),     # mean() = promedio
        "mediana_goles"       : round(df["total_goles"].median(), 3),   # valor del medio
        "max_goles_partido"   : df["total_goles"].max(),
        "pct_over_0_5"        : round((df["total_goles"] >= 1).mean() * 100, 1),
        "pct_over_1_5"        : round((df["total_goles"] >= 2).mean() * 100, 1),
        "pct_over_2_5"        : round(df["over_2_5"].mean() * 100, 1),
        "pct_over_3_5"        : round((df["total_goles"] >= 4).mean() * 100, 1),
        "pct_over_4_5"        : round((df["total_goles"] >= 5).mean() * 100, 1),

        # Ambos marcan
        "pct_ambos_marcan"    : round(df["ambos_marcan"].mean() * 100, 1),
        "pct_solo_local"      : round(((df["goles_local"] > 0) & (df["goles_visitante"] == 0)).mean() * 100, 1),
        "pct_solo_visitante"  : round(((df["goles_local"] == 0) & (df["goles_visitante"] > 0)).mean() * 100, 1),
        "pct_ninguno_marca"   : round(((df["goles_local"] == 0) & (df["goles_visitante"] == 0)).mean() * 100, 1),

        # Resultado
        "pct_victoria_local"  : round((df["goles_local"] > df["goles_visitante"]).mean() * 100, 1),
        "pct_empate"          : round((df["goles_local"] == df["goles_visitante"]).mean() * 100, 1),
        "pct_victoria_visit"  : round((df["goles_local"] < df["goles_visitante"]).mean() * 100, 1),

        # Corners
        "media_corners_partido": round(df["total_corners"].mean(), 3),
    }

    return stats


def estadisticas_por_liga(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula estadísticas agrupadas por liga.
    
    groupby() agrupa filas que tienen el mismo valor en una columna,
    luego agg() calcula estadísticas para cada grupo.
    """
    if df.empty:
        return pd.DataFrame()

    resultado = df.groupby("liga").agg(
        partidos         = ("id", "count"),
        media_goles      = ("total_goles", "mean"),
        pct_over_2_5     = ("over_2_5", "mean"),
        pct_btts         = ("ambos_marcan", "mean"),
        media_corners    = ("total_corners", "mean"),
        media_gl         = ("goles_local", "mean"),
        media_gv         = ("goles_visitante", "mean"),
    ).reset_index()  # reset_index() convierte el índice del grupo en columna normal

    # Formatear porcentajes (multiplicar por 100 y redondear)
    resultado["pct_over_2_5"]  = (resultado["pct_over_2_5"] * 100).round(1)
    resultado["pct_btts"]      = (resultado["pct_btts"]     * 100).round(1)
    resultado["media_goles"]   = resultado["media_goles"].round(3)
    resultado["media_corners"] = resultado["media_corners"].round(2)
    resultado["media_gl"]      = resultado["media_gl"].round(3)
    resultado["media_gv"]      = resultado["media_gv"].round(3)

    return resultado.sort_values("pct_over_2_5", ascending=False)


def estadisticas_por_equipo(df: pd.DataFrame, min_partidos: int = 20) -> pd.DataFrame:
    """
    Calcula estadísticas ofensivas y defensivas para cada equipo.
    
    Como un equipo puede ser local o visitante, calculamos ambos roles
    por separado y luego los combinamos.
    
    min_partidos = filtro para no mostrar equipos con poca muestra
    """
    if df.empty:
        return pd.DataFrame()

    # ── Como LOCAL ────────────────────────────────────────────────────────
    local = df.groupby("equipo_local").agg(
        partidos_local     = ("id", "count"),
        goles_anotados_l   = ("goles_local", "sum"),       # sum() = suma total
        goles_recibidos_l  = ("goles_visitante", "sum"),
        corners_l          = ("corners_local", "sum"),
        over_2_5_l         = ("over_2_5", "sum"),
        btts_l             = ("ambos_marcan", "sum"),
    ).reset_index().rename(columns={"equipo_local": "equipo"})

    # ── Como VISITANTE ────────────────────────────────────────────────────
    visitante = df.groupby("equipo_visitante").agg(
        partidos_visit     = ("id", "count"),
        goles_anotados_v   = ("goles_visitante", "sum"),
        goles_recibidos_v  = ("goles_local", "sum"),
        corners_v          = ("corners_visitante", "sum"),
        over_2_5_v         = ("over_2_5", "sum"),
        btts_v             = ("ambos_marcan", "sum"),
    ).reset_index().rename(columns={"equipo_visitante": "equipo"})

    # ── Combinar LOCAL + VISITANTE ────────────────────────────────────────
    # merge() une dos DataFrames por una columna en común (como un JOIN en SQL)
    # how="outer" incluye todos los equipos aunque no aparezcan en ambos lados
    merged = pd.merge(local, visitante, on="equipo", how="outer")

    # fillna(0) reemplaza los NaN (valores nulos) con 0
    merged = merged.fillna(0)

    # ── Calcular totales ──────────────────────────────────────────────────
    merged["total_partidos"]    = merged["partidos_local"]   + merged["partidos_visit"]
    merged["total_goles_anot"]  = merged["goles_anotados_l"] + merged["goles_anotados_v"]
    merged["total_goles_rec"]   = merged["goles_recibidos_l"]+ merged["goles_recibidos_v"]
    merged["total_corners"]     = merged["corners_l"]        + merged["corners_v"]
    merged["total_over_2_5"]    = merged["over_2_5_l"]       + merged["over_2_5_v"]
    merged["total_btts"]        = merged["btts_l"]           + merged["btts_v"]

    # ── Calcular promedios por partido ────────────────────────────────────
    n = merged["total_partidos"]  # alias para no repetir
    merged["media_goles_anotados"] = (merged["total_goles_anot"] / n).round(3)
    merged["media_goles_recibidos"]= (merged["total_goles_rec"]  / n).round(3)
    merged["media_corners"]        = (merged["total_corners"]    / n).round(2)
    merged["pct_over_2_5"]         = ((merged["total_over_2_5"] / n) * 100).round(1)
    merged["pct_btts"]             = ((merged["total_btts"]      / n) * 100).round(1)

    # ── Filtrar equipos con suficiente muestra ────────────────────────────
    merged = merged[merged["total_partidos"] >= min_partidos]

    # ── Seleccionar columnas finales ──────────────────────────────────────
    columnas_finales = [
        "equipo", "total_partidos",
        "media_goles_anotados", "media_goles_recibidos",
        "media_corners", "pct_over_2_5", "pct_btts"
    ]

    return merged[columnas_finales].sort_values("media_goles_anotados", ascending=False).reset_index(drop=True)


def imprimir_reporte(df: pd.DataFrame, liga: str = None, temporada: str = None):
    """
    Imprime en pantalla un reporte completo con todas las estadísticas.
    """
    filtro = []
    if liga:      filtro.append(f"Liga: {liga}")
    if temporada: filtro.append(f"Temporada: {temporada}")
    titulo = " | ".join(filtro) if filtro else "TODAS LAS LIGAS Y TEMPORADAS"

    print("\n" + "=" * 65)
    print(f"  📊 REPORTE ESTADÍSTICO — {titulo}")
    print("=" * 65)

    # ── Estadísticas generales ────────────────────────────────────────────
    stats = estadisticas_generales(df)
    if not stats:
        print("❌ No hay datos para mostrar.")
        return

    print(f"\n🌍 MUESTRA")
    print(f"   Partidos analizados : {stats['total_partidos']:,}")
    print(f"   Ligas               : {stats['ligas_distintas']}")
    print(f"   Temporadas          : {stats['temporadas_distintas']}")
    print(f"   Equipos distintos   : {stats['equipos_distintos']}")

    print(f"\n⚽ GOLES")
    print(f"   Media goles/partido : {stats['media_goles_partido']}")
    print(f"   Mediana             : {stats['mediana_goles']}")
    print(f"   Máximo en un partido: {stats['max_goles_partido']}")
    print(f"   Over 0.5 (≥1 gol)  : {stats['pct_over_0_5']}%")
    print(f"   Over 1.5 (≥2 goles): {stats['pct_over_1_5']}%")
    print(f"   Over 2.5 (≥3 goles): {stats['pct_over_2_5']}%")
    print(f"   Over 3.5 (≥4 goles): {stats['pct_over_3_5']}%")
    print(f"   Over 4.5 (≥5 goles): {stats['pct_over_4_5']}%")

    print(f"\n🎯 AMBOS MARCAN (BTTS)")
    print(f"   Sí (ambos marcan)   : {stats['pct_ambos_marcan']}%")
    print(f"   Solo local marca    : {stats['pct_solo_local']}%")
    print(f"   Solo visitante marca: {stats['pct_solo_visitante']}%")
    print(f"   Ninguno marca (0-0) : {stats['pct_ninguno_marca']}%")

    print(f"\n🏠 RESULTADOS")
    print(f"   Victoria local      : {stats['pct_victoria_local']}%")
    print(f"   Empate              : {stats['pct_empate']}%")
    print(f"   Victoria visitante  : {stats['pct_victoria_visit']}%")

    print(f"\n🚩 CORNERS")
    print(f"   Media corners/partido: {stats['media_corners_partido']}")

    # ── Estadísticas por liga ─────────────────────────────────────────────
    df_liga = estadisticas_por_liga(df)
    if not df_liga.empty:
        print(f"\n🌍 COMPARATIVA POR LIGA (ordenado por % Over 2.5):")
        print(df_liga.to_string(index=False))

    # ── Top 10 equipos más atacantes ──────────────────────────────────────
    df_equipos = estadisticas_por_equipo(df, min_partidos=15)
    if not df_equipos.empty:
        print(f"\n⚽ TOP 10 EQUIPOS MÁS ATACANTES (media goles anotados/partido):")
        print(df_equipos.head(10).to_string(index=False))

        print(f"\n🛡️  TOP 10 EQUIPOS MÁS DEFENSIVOS (menos goles recibidos):")
        top_def = df_equipos.sort_values("media_goles_recibidos").head(10)
        print(top_def.to_string(index=False))

        print(f"\n📈 TOP 10 EQUIPOS CON MAYOR % OVER 2.5:")
        top_over = df_equipos.sort_values("pct_over_2_5", ascending=False).head(10)
        print(top_over.to_string(index=False))


def exportar_estadisticas(df: pd.DataFrame):
    """
    Guarda los resultados en archivos CSV para uso externo.
    """
    # Estadísticas por liga
    df_liga = estadisticas_por_liga(df)
    ruta    = os.path.join(CLEAN_DIR, "estadisticas_por_liga.csv")
    df_liga.to_csv(ruta, index=False, encoding="utf-8")
    log.info(f"💾 Guardado: {ruta}")

    # Estadísticas por equipo
    df_eq = estadisticas_por_equipo(df, min_partidos=10)
    ruta  = os.path.join(CLEAN_DIR, "estadisticas_por_equipo.csv")
    df_eq.to_csv(ruta, index=False, encoding="utf-8")
    log.info(f"💾 Guardado: {ruta}")


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":

    print("\n🎯 ¿Qué análisis quieres ver?")
    print("   1. Todas las ligas juntas")
    print("   2. Solo una liga específica")
    print("   Presiona Enter para continuar con todas las ligas...\n")

    # Cargamos todos los datos
    df = cargar_datos()

    if df.empty:
        print("❌ No hay datos en la base de datos.")
        print("   Ejecuta los scripts 01, 02, 03 y 04 primero.")
    else:
        # Reporte general
        imprimir_reporte(df)

        # Exportar a CSV
        exportar_estadisticas(df)

        print("\n✅ Análisis completado.")
        print(f"   Archivos exportados en: {CLEAN_DIR}")

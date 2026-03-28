"""
PASO 3 — Limpiar y Normalizar los Datos
=========================================
Los CSVs de football-data.co.uk tienen nombres de columnas en inglés,
valores faltantes, y formatos inconsistentes.
Este script los convierte a un formato estándar y limpio.

Ejecutar con:
    python scripts/03_limpiar_datos.py

Los archivos limpios se guardan en: data_clean/
"""

import pandas as pd    # La librería principal para trabajar con datos tabulares
import os
import logging
import glob            # Para buscar archivos con patrones (ej: todos los .csv)

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE RUTAS
# ─────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR   = os.path.join(BASE_DIR, "data_raw")
CLEAN_DIR = os.path.join(BASE_DIR, "data_clean")
LOGS_DIR  = os.path.join(BASE_DIR, "logs")

os.makedirs(CLEAN_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE LOGS
# ─────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "limpieza.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# MAPEO DE LIGAS
# El nombre del código de archivo → nombre legible para la base de datos
# ─────────────────────────────────────────────
MAPA_LIGAS = {
    "E0"  : "Premier League",
    "E1"  : "Championship",
    "E2"  : "League One",
    "E3"  : "League Two",
    "EC"  : "Conference",
    "SP1" : "La Liga",
    "SP2" : "Segunda Division",
    "D1"  : "Bundesliga",
    "D2"  : "Bundesliga 2",
    "I1"  : "Serie A",
    "I2"  : "Serie B",
    "F1"  : "Ligue 1",
    "F2"  : "Ligue 2",
    "N1"  : "Eredivisie",
    "P1"  : "Primeira Liga",
    "SC0" : "Scottish Premiership",
    "SC1" : "Scottish Championship",
    "SC2" : "Scottish League One",
    "SC3" : "Scottish League Two",
    "B1"  : "First Division A",
    "T1"  : "Super Lig",
    "G1"  : "Super League Greece",
}

# ─────────────────────────────────────────────
# MAPEO DE COLUMNAS
# football-data.co.uk usa nombres en inglés.
# Este diccionario los traduce a nuestros nombres estándar.
#
# Formato: "nombre_original" : "nuestro_nombre"
# ─────────────────────────────────────────────
MAPA_COLUMNAS = {
    "Date"    : "fecha",
    "HomeTeam": "equipo_local",
    "AwayTeam": "equipo_visitante",
    "FTHG"    : "goles_local",           # Full Time Home Goals
    "FTAG"    : "goles_visitante",        # Full Time Away Goals
    "HC"      : "corners_local",          # Home Corners
    "AC"      : "corners_visitante",      # Away Corners
    "HY"      : "amarillas_local",        # Home Yellow Cards
    "AY"      : "amarillas_visitante",    # Away Yellow Cards
    "HR"      : "rojas_local",            # Home Red Cards
    "AR"      : "rojas_visitante",        # Away Red Cards
    # Algunas temporadas usan nombres alternativos:
    "HG"      : "goles_local",
    "AG"      : "goles_visitante",
    # Cuotas Bet365
    "B365H"   : "b365_local",
    "B365D"   : "b365_empate",
    "B365A"   : "b365_visit",
    # Cuotas Pinnacle (nombre estándar y cierre)
    "PSH"     : "ps_local",
    "PSD"     : "ps_empate",
    "PSA"     : "ps_visit",
    "PSCH"    : "ps_local",
    "PSCD"    : "ps_empate",
    "PSCA"    : "ps_visit",
}

# Columnas mínimas que DEBE tener el CSV para ser válido
COLUMNAS_REQUERIDAS = ["fecha", "equipo_local", "equipo_visitante", "goles_local", "goles_visitante"]


def extraer_codigo_y_temporada(nombre_archivo: str):
    """
    Extrae el código de liga y la temporada del nombre del archivo.
    
    Ejemplo:
        "SP1_2324.csv" → ("SP1", "2324")
    """
    base    = os.path.splitext(nombre_archivo)[0]  # quita .csv → "SP1_2324"
    partes  = base.split("_")                       # divide por _ → ["SP1", "2324"]
    if len(partes) >= 2:
        codigo    = partes[0]   # "SP1"
        temporada = partes[1]   # "2324"
        return codigo, temporada
    return None, None


def temporada_a_formato_largo(temporada_corta: str) -> str:
    """
    Convierte temporada corta a formato largo legible.
    
    Ejemplos:
        "2324" → "2023-24"
        "1920" → "2019-20"
    """
    if len(temporada_corta) == 4:
        inicio = "20" + temporada_corta[:2]   # "20" + "23" = "2023"
        fin    = temporada_corta[2:]           # "24"
        return f"{inicio}-{fin}"              # "2023-24"
    return temporada_corta


def limpiar_fecha(fecha_str) -> str:
    """
    Convierte una fecha al formato estándar YYYY-MM-DD.
    football-data.co.uk usa formatos como "25/08/2023" o "25/08/23".
    
    pd.to_datetime() es muy bueno detectando formatos automáticamente.
    """
    try:
        fecha = pd.to_datetime(fecha_str, dayfirst=True)  # dayfirst=True porque el día va primero
        return fecha.strftime("%Y-%m-%d")                  # formato ISO estándar
    except Exception:
        return None   # Si no puede convertir, devuelve None (valor nulo)


def limpiar_csv(ruta_archivo: str) -> pd.DataFrame | None:
    """
    Carga y limpia un archivo CSV de football-data.co.uk.
    
    Devuelve:
        Un DataFrame de pandas limpio, o None si el archivo es inválido.
    
    DataFrame = es como una tabla de Excel en Python.
    Tiene filas (partidos) y columnas (fecha, goles, etc.)
    """
    nombre = os.path.basename(ruta_archivo)
    log.info(f"\n🔧 Procesando: {nombre}")

    # ── 1. Extraer código y temporada del nombre del archivo ──────────────
    codigo, temporada_corta = extraer_codigo_y_temporada(nombre)
    if not codigo:
        log.warning(f"   ⚠️  No se pudo extraer info del nombre: {nombre}")
        return None

    liga     = MAPA_LIGAS.get(codigo, codigo)        # Si no está en el mapa, usa el código
    temporada = temporada_a_formato_largo(temporada_corta)

    # ── 2. Cargar el CSV ──────────────────────────────────────────────────
    try:
        # pd.read_csv() carga el archivo como una tabla (DataFrame)
        # encoding="latin1" maneja caracteres especiales (ñ, é, ü, etc.)
        # on_bad_lines="skip" salta filas con errores en vez de fallar
        df = pd.read_csv(ruta_archivo, encoding="latin1", on_bad_lines="skip")
    except Exception as e:
        log.error(f"   ❌ No se pudo leer: {e}")
        return None

    # Si el DataFrame está vacío, lo saltamos
    if df.empty:
        log.warning(f"   ⚠️  Archivo vacío")
        return None

    log.info(f"   📊 Filas originales: {len(df)} | Columnas: {list(df.columns[:8])}...")

    # ── 3. Renombrar columnas ─────────────────────────────────────────────
    # Renombramos solo las columnas que existen en el archivo.
    # Para las cuotas PS*, si existen PSH y PSCH a la vez, priorizamos PSH.
    odds_ps_map = {"PSH":"ps_local","PSD":"ps_empate","PSA":"ps_visit"}
    odds_psc_map= {"PSCH":"ps_local","PSCD":"ps_empate","PSCA":"ps_visit"}
    # Si ya existen PSH/PSD/PSA, no necesitamos PSCH/PSCD/PSCA
    psc_needed = not any(k in df.columns for k in odds_ps_map)
    columnas_presentes = {}
    for k, v in MAPA_COLUMNAS.items():
        if k in df.columns:
            if k in odds_psc_map and not psc_needed:
                continue   # PSH ya cubre esto
            columnas_presentes[k] = v
    df = df.rename(columns=columnas_presentes)
    # Eliminar columnas duplicadas que puedan haber quedado tras el rename
    df = df.loc[:, ~df.columns.duplicated(keep='first')]

    # ── 4. Verificar columnas mínimas requeridas ──────────────────────────
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        log.warning(f"   ⚠️  Columnas faltantes: {faltantes} — archivo omitido")
        return None

    # ── 5. Seleccionar solo las columnas que nos interesan ─────────────────
    columnas_disponibles = ["fecha", "equipo_local", "equipo_visitante",
                             "goles_local", "goles_visitante"]
    for col in ["corners_local", "corners_visitante",
                "amarillas_local", "amarillas_visitante",
                "rojas_local", "rojas_visitante",
                "b365_local", "b365_empate", "b365_visit",
                "ps_local", "ps_empate", "ps_visit"]:
        if col in df.columns:
            columnas_disponibles.append(col)

    df = df[columnas_disponibles].copy()

    # ── 6. Limpiar fechas ─────────────────────────────────────────────────
    df["fecha"] = df["fecha"].apply(limpiar_fecha)

    # ── 7. Convertir columnas numéricas ───────────────────────────────────
    for col in ["goles_local", "goles_visitante",
                "corners_local", "corners_visitante",
                "amarillas_local", "amarillas_visitante",
                "rojas_local", "rojas_visitante"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Cuotas: float, se permiten NaN (no todas las temporadas las tienen)
    for col in ["b365_local", "b365_empate", "b365_visit",
                "ps_local", "ps_empate", "ps_visit"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    # ── 8. Eliminar filas con datos faltantes en columnas clave ───────────
    filas_antes = len(df)
    df = df.dropna(subset=["fecha", "equipo_local", "equipo_visitante",
                            "goles_local", "goles_visitante"])
    filas_eliminadas = filas_antes - len(df)
    if filas_eliminadas > 0:
        log.info(f"   🗑️  Filas eliminadas (datos incompletos): {filas_eliminadas}")

    df = df[df["equipo_local"].str.strip() != ""]
    df = df[df["equipo_visitante"].str.strip() != ""]

    # ── 9. Convertir a enteros (ya sin NaN) ───────────────────────────────
    df["goles_local"]     = df["goles_local"].astype(int)
    df["goles_visitante"] = df["goles_visitante"].astype(int)

    for col in ["corners_local", "corners_visitante",
                "amarillas_local", "amarillas_visitante",
                "rojas_local", "rojas_visitante"]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
        else:
            df[col] = 0

    # ── 10. Calcular campos derivados ─────────────────────────────────────
    df["total_goles"]     = df["goles_local"] + df["goles_visitante"]
    df["total_corners"]   = df["corners_local"] + df["corners_visitante"]
    df["total_amarillas"] = df["amarillas_local"] + df["amarillas_visitante"]
    df["total_rojas"]     = df["rojas_local"] + df["rojas_visitante"]
    df["ambos_marcan"]    = ((df["goles_local"] > 0) & (df["goles_visitante"] > 0)).astype(int)
    df["over_2_5"]        = (df["total_goles"] > 2.5).astype(int)

    # ── 11. Agregar metadatos ─────────────────────────────────────────────
    df["liga"]      = liga
    df["temporada"] = temporada

    # ── 12. Reordenar columnas ────────────────────────────────────────────
    orden_base = [
        "fecha", "liga", "temporada",
        "equipo_local", "equipo_visitante",
        "goles_local", "goles_visitante",
        "corners_local", "corners_visitante",
        "amarillas_local", "amarillas_visitante",
        "rojas_local", "rojas_visitante",
        "total_goles", "total_corners",
        "total_amarillas", "total_rojas",
        "ambos_marcan", "over_2_5",
    ]
    orden_odds = [c for c in [
        "b365_local", "b365_empate", "b365_visit",
        "ps_local", "ps_empate", "ps_visit",
    ] if c in df.columns]
    orden_columnas = orden_base + orden_odds
    df = df[orden_columnas]

    # ── 13. Ordenar por fecha ─────────────────────────────────────────────
    df = df.sort_values("fecha").reset_index(drop=True)

    log.info(f"   ✅ Partidos limpios: {len(df)} | Liga: {liga} | Temporada: {temporada}")
    return df


def limpiar_todos():
    """
    Procesa todos los CSV en data_raw/ y guarda los resultados en data_clean/
    """
    # glob.glob busca archivos que coincidan con el patrón
    archivos = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")))

    if not archivos:
        log.error(f"❌ No hay archivos CSV en {RAW_DIR}")
        log.error("   Ejecuta primero: python scripts/02_descargar_datos.py")
        return

    log.info(f"\n🚀 Limpiando {len(archivos)} archivos CSV...")

    total_partidos = 0
    exitosos       = 0
    fallidos       = 0

    for ruta in archivos:
        df_limpio = limpiar_csv(ruta)

        if df_limpio is not None and not df_limpio.empty:
            # Guardar el DataFrame limpio como CSV
            nombre_salida = os.path.basename(ruta)                    # mismo nombre de archivo
            ruta_salida   = os.path.join(CLEAN_DIR, nombre_salida)    # en carpeta data_clean/
            df_limpio.to_csv(ruta_salida, index=False, encoding="utf-8")

            total_partidos += len(df_limpio)
            exitosos += 1
        else:
            fallidos += 1

    log.info("\n" + "=" * 60)
    log.info(f"📊 RESUMEN DE LIMPIEZA:")
    log.info(f"   ✅ Archivos procesados : {exitosos}")
    log.info(f"   ❌ Archivos fallidos   : {fallidos}")
    log.info(f"   ⚽ Total de partidos   : {total_partidos:,}")
    log.info(f"   📁 Carpeta de salida   : {CLEAN_DIR}")
    log.info("=" * 60)


def mostrar_muestra():
    """
    Muestra una muestra de los datos limpios para verificar que están bien.
    """
    archivos = sorted(glob.glob(os.path.join(CLEAN_DIR, "*.csv")))
    if not archivos:
        print("❌ No hay archivos limpios todavía.")
        return

    # Cargamos el primer archivo disponible
    df = pd.read_csv(archivos[0])
    print(f"\n👁️  Muestra de datos limpios ({os.path.basename(archivos[0])}):")
    print(df.head(5).to_string(index=False))  # muestra las primeras 5 filas
    print(f"\n   Columnas: {list(df.columns)}")
    print(f"   Tipos   : \n{df.dtypes}")


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    limpiar_todos()
    mostrar_muestra()
    print("\n🎯 Listo. Continúa con el script 04_insertar_datos.py")

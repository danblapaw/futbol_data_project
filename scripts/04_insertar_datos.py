"""
PASO 4 — Insertar Datos en la Base de Datos (Sin Duplicados)
=============================================================
Lee los CSVs limpios de data_clean/ e inserta los partidos
en la tabla 'partidos' de la base de datos SQLite.

El truco para evitar duplicados es usar:
    INSERT OR IGNORE INTO partidos ...
SQLite ignorará silenciosamente cualquier fila que ya exista
(basándose en la restricción UNIQUE que definimos en el PASO 1).

Ejecutar con:
    python scripts/04_insertar_datos.py
"""

import sqlite3
import pandas as pd
import os
import glob
import logging

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE RUTAS
# ─────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(BASE_DIR, "data_clean")
DB_PATH   = os.path.join(BASE_DIR, "db", "futbol.db")
LOGS_DIR  = os.path.join(BASE_DIR, "logs")

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE LOGS
# ─────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "insercion.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def verificar_base_de_datos():
    """
    Verifica que la base de datos y la tabla existan antes de insertar.
    """
    if not os.path.exists(DB_PATH):
        log.error(f"❌ Base de datos no encontrada: {DB_PATH}")
        log.error("   Ejecuta primero: python scripts/01_crear_base_de_datos.py")
        return False

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Verificamos que la tabla 'partidos' exista
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='partidos'")
        if not cursor.fetchone():
            log.error("❌ La tabla 'partidos' no existe en la base de datos.")
            log.error("   Ejecuta primero: python scripts/01_crear_base_de_datos.py")
            return False
    return True


def contar_partidos_en_db() -> int:
    """
    Devuelve el número total de partidos actualmente en la base de datos.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM partidos")
        return cursor.fetchone()[0]  # fetchone() trae una sola fila; [0] es el primer valor


def insertar_dataframe(df: pd.DataFrame, conn: sqlite3.Connection) -> tuple[int, int]:
    """
    Inserta un DataFrame en la tabla 'partidos'.
    
    Usa INSERT OR IGNORE para saltar duplicados automáticamente.
    
    Devuelve:
        (insertados, duplicados) — cuántos se insertaron vs cuántos eran duplicados
    """
    cursor = conn.cursor()

    # Contamos antes de insertar para calcular cuántos se insertaron
    conteo_antes = contar_partidos_en_db()

    # executemany() inserta múltiples filas de una sola vez (mucho más rápido que un loop)
    # La cadena "?" son marcadores de posición que SQLite reemplaza con los valores reales
    # Esto previene inyección SQL (buena práctica de seguridad)
    sql = """
        INSERT OR IGNORE INTO partidos (
            fecha, liga, temporada,
            equipo_local, equipo_visitante,
            goles_local, goles_visitante,
            corners_local, corners_visitante,
            total_goles, total_corners,
            ambos_marcan, over_2_5
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    # Convertimos el DataFrame a una lista de tuplas para ejecutemany()
    # itertuples() es más rápido que iterrows() para esto
    registros = [
        (
            row.fecha, row.liga, row.temporada,
            row.equipo_local, row.equipo_visitante,
            int(row.goles_local), int(row.goles_visitante),
            int(row.corners_local), int(row.corners_visitante),
            int(row.total_goles), int(row.total_corners),
            int(row.ambos_marcan), int(row.over_2_5)
        )
        for row in df.itertuples(index=False)  # itertuples genera objetos con atributos por columna
    ]

    cursor.executemany(sql, registros)
    conn.commit()  # Guardar cambios en el archivo

    conteo_despues = contar_partidos_en_db()
    insertados     = conteo_despues - conteo_antes
    duplicados     = len(df) - insertados

    return insertados, duplicados


def insertar_todos():
    """
    Lee todos los CSV limpios e inserta los datos en la base de datos.
    """
    if not verificar_base_de_datos():
        return

    archivos = sorted(glob.glob(os.path.join(CLEAN_DIR, "*.csv")))

    if not archivos:
        log.error(f"❌ No hay archivos limpios en {CLEAN_DIR}")
        log.error("   Ejecuta primero: python scripts/03_limpiar_datos.py")
        return

    total_insertados  = 0
    total_duplicados  = 0
    archivos_ok       = 0
    archivos_error    = 0

    log.info(f"\n🚀 Insertando datos de {len(archivos)} archivos...")
    log.info(f"   Base de datos: {DB_PATH}")
    log.info(f"   Partidos antes: {contar_partidos_en_db():,}")

    # Abrimos UNA sola conexión para todo el proceso (más eficiente)
    with sqlite3.connect(DB_PATH) as conn:

        for ruta in archivos:
            nombre = os.path.basename(ruta)

            try:
                # Cargar el CSV limpio
                df = pd.read_csv(ruta, encoding="utf-8")

                if df.empty:
                    log.warning(f"   ⚠️  Vacío: {nombre}")
                    continue

                # Insertar en la base de datos
                insertados, duplicados = insertar_dataframe(df, conn)

                log.info(f"   ✅ {nombre:<25} | +{insertados:>5} nuevos | {duplicados:>5} duplicados")
                total_insertados += insertados
                total_duplicados += duplicados
                archivos_ok      += 1

            except Exception as e:
                log.error(f"   ❌ Error en {nombre}: {e}")
                archivos_error += 1

    # Resumen final
    total_en_db = contar_partidos_en_db()
    log.info("\n" + "=" * 60)
    log.info(f"📊 RESUMEN DE INSERCIÓN:")
    log.info(f"   ✅ Archivos procesados   : {archivos_ok}")
    log.info(f"   ❌ Archivos con error    : {archivos_error}")
    log.info(f"   ⚽ Partidos insertados   : {total_insertados:,}")
    log.info(f"   ⏭️  Duplicados omitidos   : {total_duplicados:,}")
    log.info(f"   🗄️  Total en base de datos: {total_en_db:,}")
    log.info("=" * 60)


def verificar_insercion():
    """
    Consulta la base de datos para confirmar que los datos se insertaron bien.
    Muestra estadísticas por liga y temporada.
    """
    with sqlite3.connect(DB_PATH) as conn:
        # pd.read_sql_query() ejecuta SQL y devuelve directamente un DataFrame
        # Es muy conveniente para consultas de verificación

        print("\n📊 Partidos por liga:")
        df_liga = pd.read_sql_query("""
            SELECT
                liga,
                COUNT(*) as total_partidos,
                MIN(fecha) as primer_partido,
                MAX(fecha) as ultimo_partido
            FROM partidos
            GROUP BY liga
            ORDER BY total_partidos DESC
        """, conn)
        print(df_liga.to_string(index=False))

        print("\n📊 Partidos por temporada:")
        df_temp = pd.read_sql_query("""
            SELECT
                temporada,
                COUNT(*) as total_partidos,
                COUNT(DISTINCT liga) as ligas
            FROM partidos
            GROUP BY temporada
            ORDER BY temporada DESC
        """, conn)
        print(df_temp.to_string(index=False))

        print("\n📊 Muestra de 5 partidos:")
        df_muestra = pd.read_sql_query("""
            SELECT fecha, liga, equipo_local, equipo_visitante,
                   goles_local, goles_visitante, over_2_5, ambos_marcan
            FROM partidos
            ORDER BY RANDOM()
            LIMIT 5
        """, conn)
        print(df_muestra.to_string(index=False))


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    insertar_todos()
    verificar_insercion()
    print("\n🎯 Listo. Continúa con el script 05_estadisticas.py")

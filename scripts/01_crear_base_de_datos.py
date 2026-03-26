"""
PASO 1 — Crear la Base de Datos
================================
Este script crea el archivo SQLite con la tabla principal de partidos.
SQLite es una base de datos que vive en un solo archivo .db en tu computadora.
No necesitas instalar ningún servidor — Python lo maneja todo.

Ejecutar con:
    python scripts/01_crear_base_de_datos.py
"""

import sqlite3   # Librería para trabajar con SQLite (viene incluida en Python)
import os        # Librería para trabajar con carpetas y archivos del sistema

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# Aquí definimos dónde se va a guardar la base de datos.
# os.path.dirname(__file__) = la carpeta donde está este script (scripts/)
# os.path.join(...)          = une rutas de forma segura en cualquier sistema operativo
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # carpeta raíz del proyecto
DB_PATH  = os.path.join(BASE_DIR, "db", "futbol.db")  # ruta completa al archivo de base de datos


def crear_base_de_datos():
    """
    Crea el archivo de base de datos y la tabla 'partidos' si no existen.
    Si ya existen, NO los borra — simplemente no hace nada.
    """
    print(f"📂 Creando base de datos en: {DB_PATH}")

    # sqlite3.connect() abre (o crea) el archivo .db
    # 'with' garantiza que la conexión se cierra automáticamente al terminar
    with sqlite3.connect(DB_PATH) as conn:

        # cursor es el objeto que nos permite ejecutar comandos SQL
        cursor = conn.cursor()

        # ─────────────────────────────────────────────
        # CREAR TABLA PARTIDOS
        # CREATE TABLE IF NOT EXISTS = solo la crea si no existe ya
        # Cada línea define una columna con su nombre y tipo de dato
        # ─────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partidos (

                -- Identificador único, se asigna automáticamente
                id               INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Información del partido
                fecha            TEXT    NOT NULL,   -- Formato: YYYY-MM-DD
                liga             TEXT    NOT NULL,   -- Ej: "Premier League"
                temporada        TEXT    NOT NULL,   -- Ej: "2023-24"
                equipo_local     TEXT    NOT NULL,
                equipo_visitante TEXT    NOT NULL,

                -- Resultado
                goles_local      INTEGER,            -- Goles del equipo local
                goles_visitante  INTEGER,            -- Goles del equipo visitante

                -- Corners
                corners_local      INTEGER,
                corners_visitante  INTEGER,

                -- Campos calculados (los calcularemos al insertar)
                total_goles       INTEGER,           -- goles_local + goles_visitante
                total_corners     INTEGER,           -- corners_local + corners_visitante
                ambos_marcan      INTEGER,           -- 1 = sí, 0 = no
                over_2_5          INTEGER,           -- 1 = más de 2.5 goles, 0 = no

                -- Cuándo se insertó el registro en nuestra base de datos
                fecha_insercion  TEXT DEFAULT (datetime('now')),

                -- Esta restricción UNIQUE evita duplicados:
                -- no puede haber dos partidos con la misma fecha, liga, temporada,
                -- equipo local Y equipo visitante al mismo tiempo.
                UNIQUE (fecha, liga, temporada, equipo_local, equipo_visitante)
            )
        """)

        # Creamos un índice para acelerar las búsquedas por liga y temporada
        # Un índice es como el índice al final de un libro — acelera encontrar cosas
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_liga_temporada
            ON partidos (liga, temporada)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fecha
            ON partidos (fecha)
        """)

        # Guardamos los cambios en el archivo
        conn.commit()

    print("✅ Base de datos creada correctamente.")
    print(f"   Archivo: {DB_PATH}")


def verificar_estructura():
    """
    Muestra la estructura de la tabla para confirmar que se creó bien.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # PRAGMA table_info = comando SQLite que describe las columnas de una tabla
        cursor.execute("PRAGMA table_info(partidos)")
        columnas = cursor.fetchall()  # fetchall() trae todos los resultados

        print("\n📋 Columnas de la tabla 'partidos':")
        print(f"   {'#':<4} {'Nombre':<22} {'Tipo':<12} {'Requerido'}")
        print("   " + "-" * 50)
        for col in columnas:
            requerido = "SÍ" if col[3] else "no"
            print(f"   {col[0]:<4} {col[1]:<22} {col[2]:<12} {requerido}")


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# Este bloque solo se ejecuta cuando corres el script directamente.
# No se ejecuta si otro script importa este archivo como módulo.
# ─────────────────────────────────────────────
if __name__ == "__main__":
    crear_base_de_datos()
    verificar_estructura()
    print("\n🎯 Listo. Continúa con el script 02_descargar_datos.py")

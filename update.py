"""
update.py — Pipeline completo de actualización
================================================
Ejecuta los pasos 02 → 03 → 04 → 07 en orden para descargar datos frescos
de football-data.co.uk y regenerar football_explorer.html desde cero.

Uso:
    python update.py
"""

import subprocess
import sys
import os
import time

# Forzar UTF-8 en la consola de Windows para que los emojis de los scripts no fallen
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PASOS = [
    {
        "numero": 1,
        "script": "scripts/02_descargar_datos.py",
        "titulo": "Descargando CSVs frescos de football-data.co.uk",
        "descripcion": "12 ligas · temporada 2025/26 y anteriores",
    },
    {
        "numero": 2,
        "script": "scripts/03_limpiar_datos.py",
        "titulo": "Limpiando y normalizando los datos",
        "descripcion": "Traduce columnas, normaliza fechas, calcula métricas",
    },
    {
        "numero": 3,
        "script": "scripts/04_insertar_datos.py",
        "titulo": "Insertando datos en la base de datos",
        "descripcion": "SQLite · duplicados ignorados automáticamente",
    },
    {
        "numero": 4,
        "script": "scripts/07_generar_explorador.py",
        "titulo": "Generando football_explorer.html",
        "descripcion": "HTML interactivo con todos los datos",
    },
]

TOTAL = len(PASOS)
SEP   = "-" * 60


def cabecera():
    print()
    print("=" * 60)
    print("  FUTBOL DATA - PIPELINE DE ACTUALIZACION")
    print("=" * 60)
    print(f"  {TOTAL} pasos en total  |  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()


def ejecutar_paso(paso: dict) -> bool:
    """
    Ejecuta un script Python como subproceso.
    Devuelve True si terminó sin errores, False si falló.
    """
    num    = paso["numero"]
    script = os.path.join(BASE_DIR, paso["script"])

    print(SEP)
    print(f"  PASO {num}/{TOTAL} — {paso['titulo']}")
    print(f"  {paso['descripcion']}")
    print(SEP)

    inicio = time.time()

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    resultado = subprocess.run(
        [sys.executable, script],
        cwd=BASE_DIR,
        env=env,
    )

    duracion = time.time() - inicio

    if resultado.returncode == 0:
        print(f"\n  OK - Paso {num} completado en {duracion:.1f}s")
    else:
        print(f"\n  ERROR - Paso {num} fallo (codigo {resultado.returncode})")
        print(f"     Script: {paso['script']}")

    print()
    return resultado.returncode == 0


def main():
    cabecera()

    inicio_total = time.time()
    fallos = []

    for paso in PASOS:
        ok = ejecutar_paso(paso)
        if not ok:
            fallos.append(paso)
            print(f"  STOP - Pipeline interrumpido en paso {paso['numero']}.")
            print(f"     Revisa el error arriba y vuelve a ejecutar.")
            print()
            sys.exit(1)

    duracion_total = time.time() - inicio_total

    print("=" * 60)
    print("  PIPELINE COMPLETADO")
    print("=" * 60)
    print(f"  Tiempo total : {duracion_total:.1f}s")
    print(f"  Resultado    : football_explorer.html")
    print(f"  Ruta         : {os.path.join(BASE_DIR, 'football_explorer.html')}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()

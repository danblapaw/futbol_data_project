"""
PASO 2 — Descargar Datos Históricos de Fútbol
===============================================
Fuente: football-data.co.uk (datos gratuitos, sin API key)
Descarga archivos CSV de múltiples ligas y temporadas automáticamente.

Ejecutar con:
    python scripts/02_descargar_datos.py

Los archivos se guardan en: data_raw/
"""

import requests   # Para hacer peticiones HTTP (descargar archivos de internet)
import os         # Para trabajar con carpetas y archivos
import time       # Para pausar entre descargas (no saturar el servidor)
import logging    # Para guardar un registro de lo que hace el script

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE RUTAS
# ─────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR     = os.path.join(BASE_DIR, "data_raw")
LOGS_DIR    = os.path.join(BASE_DIR, "logs")

# Crear carpetas si no existen
os.makedirs(RAW_DIR,  exist_ok=True)   # exist_ok=True = no da error si ya existe
os.makedirs(LOGS_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE LOGS
# Los logs guardan un historial de todo lo que hace el script.
# Así puedes ver qué descargó, qué falló, y cuándo.
# ─────────────────────────────────────────────
logging.basicConfig(
    level    = logging.INFO,                                    # nivel mínimo de mensajes
    format   = "%(asctime)s | %(levelname)s | %(message)s",    # formato del mensaje
    handlers = [
        logging.FileHandler(os.path.join(LOGS_DIR, "descarga.log"), encoding="utf-8"),  # guarda en archivo
        logging.StreamHandler()                                  # también muestra en pantalla
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# LIGAS DISPONIBLES EN football-data.co.uk
# Cada liga tiene un código corto que forma parte de la URL.
# Formato URL: https://www.football-data.co.uk/mmz4281/{temporada}/{liga}.csv
#
# Ejemplos de temporadas: 2324 = 2023/24 | 2223 = 2022/23 | etc.
# ─────────────────────────────────────────────
LIGAS = {
    # Código  : Nombre legible
    "E0"     : "Premier League (Inglaterra)",
    "E1"     : "Championship (Inglaterra D2)",
    "SP1"    : "La Liga (España)",
    "SP2"    : "Segunda División (España)",
    "D1"     : "Bundesliga (Alemania)",
    "D2"     : "Bundesliga 2 (Alemania)",
    "I1"     : "Serie A (Italia)",
    "I2"     : "Serie B (Italia)",
    "F1"     : "Ligue 1 (Francia)",
    "F2"     : "Ligue 2 (Francia)",
    "N1"     : "Eredivisie (Holanda)",
    "P1"     : "Primeira Liga (Portugal)",
    "SC0"    : "Scottish Premiership (Escocia)",
    "B1"     : "First Division A (Bélgica)",
    "T1"     : "Süper Lig (Turquía)",
    "G1"     : "Super League (Grecia)",
}

# Temporadas que queremos descargar
# Formato: los últimos 2 dígitos de cada año pegados
# Ejemplo: "2324" = temporada 2023/2024
TEMPORADAS = [
    "2526",  # 2025/26 (en curso)
    "2425",  # 2024/25
    "2324",  # 2023/24
    "2223",  # 2022/23
    "2122",  # 2021/22
    "2021",  # 2020/21
    "1920",  # 2019/20
    "1819",  # 2018/19
    "1718",  # 2017/18
    "1617",  # 2016/17
    "1516",  # 2015/16
]

# URL base del sitio
URL_BASE = "https://www.football-data.co.uk/mmz4281"


def construir_url(temporada: str, codigo_liga: str) -> str:
    """
    Construye la URL completa para descargar un CSV.
    
    Ejemplo:
        temporada  = "2324"
        liga       = "SP1"
        resultado  = "https://www.football-data.co.uk/mmz4281/2324/SP1.csv"
    """
    return f"{URL_BASE}/{temporada}/{codigo_liga}.csv"


def construir_nombre_archivo(temporada: str, codigo_liga: str) -> str:
    """
    Construye el nombre local del archivo CSV descargado.
    
    Ejemplo: "SP1_2324.csv"
    """
    return f"{codigo_liga}_{temporada}.csv"


def descargar_archivo(url: str, ruta_destino: str) -> bool:
    """
    Descarga un archivo desde una URL y lo guarda en ruta_destino.
    
    Devuelve:
        True  = descarga exitosa
        False = falló (archivo no existe o error de red)
    """
    try:
        # requests.get() hace una petición GET al servidor
        # timeout=30 = si no responde en 30 segundos, cancela
        respuesta = requests.get(url, timeout=30)

        # status_code 200 = éxito, 404 = no encontrado, etc.
        if respuesta.status_code == 200:

            # Verificamos que el archivo tenga contenido real (no una página de error)
            # Los CSVs válidos empiezan con encabezados de texto, no con "<html"
            contenido = respuesta.content
            if len(contenido) < 100 or b"<html" in contenido[:200]:
                log.warning(f"   ⚠️  Archivo vacío o no válido: {url}")
                return False

            # Escribimos el contenido en el archivo local
            # "wb" = write binary (escribir en modo binario)
            with open(ruta_destino, "wb") as f:
                f.write(contenido)

            # Calculamos el tamaño en KB para mostrarlo
            tamano_kb = len(contenido) / 1024
            log.info(f"   ✅ Descargado ({tamano_kb:.1f} KB): {os.path.basename(ruta_destino)}")
            return True

        else:
            log.warning(f"   ⚠️  HTTP {respuesta.status_code}: {url}")
            return False

    except requests.exceptions.ConnectionError:
        log.error(f"   ❌ Sin conexión a internet para: {url}")
        return False
    except requests.exceptions.Timeout:
        log.error(f"   ❌ Timeout (tardó más de 30s): {url}")
        return False
    except Exception as e:
        log.error(f"   ❌ Error inesperado: {e}")
        return False


def descargar_todo(ligas: dict = None, temporadas: list = None):
    """
    Descarga todos los CSVs para las ligas y temporadas configuradas.
    
    Parámetros opcionales para filtrar:
        ligas      = dict con los códigos de liga que quieres (None = todas)
        temporadas = lista de temporadas (None = todas)
    """
    ligas_a_usar      = ligas      or LIGAS
    temporadas_a_usar = temporadas or TEMPORADAS

    total     = len(ligas_a_usar) * len(temporadas_a_usar)
    exitosos  = 0
    fallidos  = 0
    omitidos  = 0
    contador  = 0

    log.info("=" * 60)
    log.info(f"🚀 Iniciando descarga: {len(ligas_a_usar)} ligas × {len(temporadas_a_usar)} temporadas = {total} archivos")
    log.info("=" * 60)

    for codigo, nombre in ligas_a_usar.items():
        log.info(f"\n📁 Liga: {nombre} ({codigo})")

        for temporada in temporadas_a_usar:
            contador += 1
            nombre_archivo = construir_nombre_archivo(temporada, codigo)
            ruta_destino   = os.path.join(RAW_DIR, nombre_archivo)

            # Si el archivo ya existe y tiene tamaño razonable, lo saltamos
            # Esto evita re-descargar todo si el script se interrumpe
            if os.path.exists(ruta_destino) and os.path.getsize(ruta_destino) > 500:
                log.info(f"   ⏭️  Ya existe, omitiendo: {nombre_archivo}")
                omitidos += 1
                continue

            url = construir_url(temporada, codigo)
            log.info(f"   [{contador}/{total}] Descargando temporada {temporada}...")

            if descargar_archivo(url, ruta_destino):
                exitosos += 1
            else:
                fallidos += 1

            # Pausa de 0.5 segundos entre descargas para no sobrecargar el servidor
            # Es buena práctica ser "educado" con los servidores externos
            time.sleep(0.5)

    # Resumen final
    log.info("\n" + "=" * 60)
    log.info(f"📊 RESUMEN DE DESCARGA:")
    log.info(f"   ✅ Exitosos : {exitosos}")
    log.info(f"   ⏭️  Omitidos : {omitidos} (ya existían)")
    log.info(f"   ❌ Fallidos : {fallidos}")
    log.info(f"   📁 Carpeta  : {RAW_DIR}")
    log.info("=" * 60)

    return exitosos, fallidos, omitidos


def listar_archivos_descargados():
    """
    Muestra todos los archivos CSV que hay en data_raw/
    """
    archivos = [f for f in os.listdir(RAW_DIR) if f.endswith(".csv")]
    archivos.sort()

    print(f"\n📂 Archivos en data_raw/ ({len(archivos)} total):")
    for archivo in archivos:
        ruta    = os.path.join(RAW_DIR, archivo)
        tamano  = os.path.getsize(ruta) / 1024
        print(f"   {archivo:<25} {tamano:>8.1f} KB")


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":

    # 12 ligas principales (primeras divisiones de las grandes ligas europeas)
    # Excluye segundas divisiones (SP2, D2, I2, F2) para centrarse en datos fiables
    LIGAS_12 = {
        "E0"  : "Premier League (Inglaterra)",
        "E1"  : "Championship (Inglaterra D2)",
        "SP1" : "La Liga (España)",
        "D1"  : "Bundesliga (Alemania)",
        "I1"  : "Serie A (Italia)",
        "F1"  : "Ligue 1 (Francia)",
        "N1"  : "Eredivisie (Holanda)",
        "P1"  : "Primeira Liga (Portugal)",
        "SC0" : "Scottish Premiership (Escocia)",
        "B1"  : "First Division A (Bélgica)",
        "T1"  : "Süper Lig (Turquía)",
        "G1"  : "Super League (Grecia)",
    }

    descargar_todo(ligas=LIGAS_12)
    listar_archivos_descargados()

    print("\n🎯 Listo. Continúa con el script 03_limpiar_datos.py")

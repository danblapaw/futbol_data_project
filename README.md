# ⚽ Sistema de Análisis de Datos de Fútbol
## Guía de instalación y uso paso a paso

---

## 📁 Estructura del Proyecto

```
futbol_data_project/
├── data_raw/          ← CSVs descargados de football-data.co.uk
├── data_clean/        ← CSVs limpios y normalizados
├── scripts/           ← Todos los scripts de Python
│   ├── 00_ejecutar_todo.py        → Ejecuta todo de una vez
│   ├── 01_crear_base_de_datos.py  → Crea el archivo futbol.db
│   ├── 02_descargar_datos.py      → Descarga CSVs de internet
│   ├── 03_limpiar_datos.py        → Limpia y normaliza los datos
│   ├── 04_insertar_datos.py       → Inserta en SQLite sin duplicados
│   └── 05_estadisticas.py         → Calcula y muestra estadísticas
├── db/
│   └── futbol.db      ← Base de datos SQLite (se crea automáticamente)
├── logs/              ← Registros de cada ejecución
├── requirements.txt   ← Lista de librerías necesarias
└── README.md          ← Esta guía
```

---

## 🚀 Instalación (Primera Vez)

### Paso 1: Instalar Python
Descarga Python desde https://python.org/downloads
- Versión recomendada: Python 3.10 o superior
- ⚠️ En Windows: marca la casilla "Add Python to PATH" durante la instalación

### Paso 2: Abrir la terminal
- **Windows**: Busca "CMD" o "PowerShell" en el menú inicio
- **Mac**: Busca "Terminal" en Spotlight (Cmd + Espacio)
- **Linux**: Ctrl + Alt + T

### Paso 3: Ir a la carpeta del proyecto
```bash
cd ruta/a/tu/proyecto/futbol_data_project
```

### Paso 4: Instalar las librerías necesarias
```bash
pip install -r requirements.txt
```

Verifica que se instalaron:
```bash
python -c "import pandas, numpy, requests; print('✅ Todo instalado correctamente')"
```

---

## ▶️ Ejecución Paso a Paso

### PASO 1: Crear la base de datos
```bash
python scripts/01_crear_base_de_datos.py
```
✅ Deberías ver: "Base de datos creada correctamente"
✅ Se crea el archivo: `db/futbol.db`

### PASO 2: Descargar datos
```bash
python scripts/02_descargar_datos.py
```
✅ Deberías ver archivos descargándose en `data_raw/`
ℹ️  Descarga ~50 archivos CSV por defecto (5 ligas × 10 temporadas)

### PASO 3: Limpiar datos
```bash
python scripts/03_limpiar_datos.py
```
✅ Deberías ver archivos procesados en `data_clean/`

### PASO 4: Insertar en base de datos
```bash
python scripts/04_insertar_datos.py
```
✅ Deberías ver: "Total en base de datos: XX,XXX partidos"

### PASO 5: Ver estadísticas
```bash
python scripts/05_estadisticas.py
```
✅ Verás tablas con porcentajes de Over 2.5, BTTS, etc.

---

## ⚡ Ejecución Rápida (Todo de Una Vez)

```bash
python scripts/00_ejecutar_todo.py
```

---

## 🔄 Actualizar Datos

Para añadir nuevos partidos sin duplicar los existentes,
simplemente vuelve a ejecutar desde el paso 2:

```bash
python scripts/02_descargar_datos.py
python scripts/03_limpiar_datos.py
python scripts/04_insertar_datos.py
```

El sistema detectará automáticamente qué partidos ya están
en la base de datos y solo insertará los nuevos.

---

## 📊 Campos de la Base de Datos

| Campo              | Tipo    | Descripción                    |
|--------------------|---------|--------------------------------|
| id                 | INTEGER | ID único (automático)          |
| fecha              | TEXT    | Formato: YYYY-MM-DD            |
| liga               | TEXT    | Nombre de la liga              |
| temporada          | TEXT    | Formato: YYYY-YY               |
| equipo_local       | TEXT    | Nombre del equipo local        |
| equipo_visitante   | TEXT    | Nombre del equipo visitante    |
| goles_local        | INTEGER | Goles del local                |
| goles_visitante    | INTEGER | Goles del visitante            |
| corners_local      | INTEGER | Corners del local              |
| corners_visitante  | INTEGER | Corners del visitante          |
| total_goles        | INTEGER | Suma de goles del partido      |
| total_corners      | INTEGER | Suma de corners del partido    |
| ambos_marcan       | INTEGER | 1=sí, 0=no (BTTS)             |
| over_2_5           | INTEGER | 1=sí (≥3 goles), 0=no         |
| fecha_insercion    | TEXT    | Cuándo se insertó el registro  |

---

## 🏟️ Ligas Disponibles

| Código | Liga                        |
|--------|-----------------------------|
| E0     | Premier League (Inglaterra) |
| E1     | Championship (Inglaterra)   |
| SP1    | La Liga (España)            |
| SP2    | Segunda División (España)   |
| D1     | Bundesliga (Alemania)       |
| I1     | Serie A (Italia)            |
| F1     | Ligue 1 (Francia)           |
| N1     | Eredivisie (Holanda)        |
| P1     | Primeira Liga (Portugal)    |

---

## 🐛 Solución de Problemas

**Error: "No module named pandas"**
→ Ejecuta: `pip install -r requirements.txt`

**Error: "No hay archivos CSV en data_raw"**
→ Ejecuta primero: `python scripts/02_descargar_datos.py`

**Error: "Base de datos no encontrada"**
→ Ejecuta primero: `python scripts/01_crear_base_de_datos.py`

**Descarga muy lenta**
→ Normal. Se añade una pausa de 0.5s entre archivos para no saturar el servidor.

---

## 📝 Fuente de Datos

Todos los datos provienen de **football-data.co.uk**
- Gratuitos y sin necesidad de API key
- Actualizados regularmente durante la temporada
- Disponibles desde la temporada 1993/94

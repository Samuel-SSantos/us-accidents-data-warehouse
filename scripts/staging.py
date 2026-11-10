
from pathlib import Path
import duckdb
import time

# ============================================
# CONFIGURAÇÃO
# ============================================

BASE = Path(__file__).resolve().parents[1]

CSV = BASE / "dados" / "bruto" / "US_Accidents_March23.csv"

PASTA_BANCO = BASE / "dados" / "tratado"
PASTA_BANCO.mkdir(parents=True, exist_ok=True)

BANCO = PASTA_BANCO / "us_accidents.duckdb"

if not CSV.exists():
    raise FileNotFoundError(f"CSV não encontrado: {CSV}")

inicio = time.time()

con = duckdb.connect(str(BANCO))
con.execute("SET threads = 4")
con.execute("SET memory_limit = '2GB'")

# Limita o uso de disco temporário ao espaço
# disponível no diretório configurado.
PASTA_TEMP = BASE / "dados" / "temporario"
PASTA_TEMP.mkdir(parents=True, exist_ok=True)

con.execute(
    "SET temp_directory = ?",
    [str(PASTA_TEMP)]
)

caminho = str(CSV).replace("'", "''")

print("=== MARCO 3 — CRIAÇÃO DA STAGING ===")

# ============================================
# 1. EXTRAÇÃO E TRANSFORMAÇÃO
# ============================================

# Criamos uma tabela temporária primeiro.
# A tabela definitiva só será substituída
# depois das validações.

con.execute(f"""
CREATE OR REPLACE TEMP TABLE staging_candidata AS

SELECT
    ID AS Accident_ID,
    Source,

    TRY_CAST(Severity AS INTEGER) AS Severity,

    TRY_CAST(Start_Time AS TIMESTAMP) AS Start_Time,
    TRY_CAST(End_Time AS TIMESTAMP) AS End_Time,

    TRY_CAST(Start_Lat AS DOUBLE) AS Start_Lat,
    TRY_CAST(Start_Lng AS DOUBLE) AS Start_Lng,
    TRY_CAST(End_Lat AS DOUBLE) AS End_Lat,
    TRY_CAST(End_Lng AS DOUBLE) AS End_Lng,

    Country,
    State,
    County,
    City,
    Zipcode,

    Street,
    Description,

    Weather_Condition,
    Wind_Direction,

    TRY_CAST("Temperature(F)" AS DOUBLE)
        AS Temperature_F_Original,

    CASE
        WHEN TRY_CAST("Temperature(F)" AS DOUBLE)
             BETWEEN -100 AND 140
        THEN
            (TRY_CAST("Temperature(F)" AS DOUBLE) - 32)
            * 5.0 / 9.0
        ELSE NULL
    END AS Temperature_C,

    CASE
        WHEN TRY_CAST("Temperature(F)" AS DOUBLE)
             IS NOT NULL
         AND (
            TRY_CAST("Temperature(F)" AS DOUBLE) < -100
            OR TRY_CAST("Temperature(F)" AS DOUBLE) > 140
         )
        THEN TRUE
        ELSE FALSE
    END AS Temperature_Suspect,

    (TRY_CAST("Wind_Chill(F)" AS DOUBLE) - 32)
        * 5.0 / 9.0 AS Wind_Chill_C,

    TRY_CAST("Humidity(%)" AS DOUBLE)
        AS Humidity_Pct,

    TRY_CAST("Pressure(in)" AS DOUBLE)
        * 33.8638866667 AS Pressure_hPa,

    TRY_CAST("Visibility(mi)" AS DOUBLE)
        * 1.609344 AS Visibility_km,

    TRY_CAST("Wind_Speed(mph)" AS DOUBLE)
        * 1.609344 AS Wind_Speed_kmh,

    TRY_CAST("Precipitation(in)" AS DOUBLE)
        * 25.4 AS Precipitation_mm,

    TRY_CAST("Distance(mi)" AS DOUBLE)
        * 1.609344 AS Distance_km,

    date_diff(
        'second',
        TRY_CAST(Start_Time AS TIMESTAMP),
        TRY_CAST(End_Time AS TIMESTAMP)
    ) / 60.0 AS Duration_Minutes,

    CASE
        WHEN date_diff(
            'second',
            TRY_CAST(Start_Time AS TIMESTAMP),
            TRY_CAST(End_Time AS TIMESTAMP)
        ) > 7 * 24 * 60 * 60
        THEN TRUE
        ELSE FALSE
    END AS Duration_Suspect,

    YEAR(TRY_CAST(Start_Time AS TIMESTAMP))
        AS Accident_Year,

    MONTH(TRY_CAST(Start_Time AS TIMESTAMP))
        AS Accident_Month,

    HOUR(TRY_CAST(Start_Time AS TIMESTAMP))
        AS Accident_Hour,

    Amenity,
    Bump,
    Crossing,
    Give_Way,
    Junction,
    No_Exit,
    Railway,
    Roundabout,
    Station,
    Stop,
    Traffic_Calming,
    Traffic_Signal,
    Turning_Loop,

    Sunrise_Sunset,
    Civil_Twilight,
    Nautical_Twilight,
    Astronomical_Twilight

FROM read_csv(
    '{caminho}',
    header = true,
    all_varchar = true,
    delim = ',',
    sample_size = 20000
)
""")

print("Tabela temporária criada.")

# ============================================
# 2. VALIDAÇÃO
# ============================================

total = con.execute("""
    SELECT COUNT(*)
    FROM staging_candidata
""").fetchone()[0]

ids = con.execute("""
    SELECT COUNT(DISTINCT Accident_ID)
    FROM staging_candidata
""").fetchone()[0]

suspeitas = con.execute("""
    SELECT
        COUNT(*) FILTER (WHERE Temperature_Suspect),
        COUNT(*) FILTER (WHERE Duration_Suspect)
    FROM staging_candidata
""").fetchone()

print("\n=== VALIDAÇÃO ===")
print("Registros:", total)
print("IDs únicos:", ids)
print("Temperaturas suspeitas:", suspeitas[0])
print("Durações suspeitas:", suspeitas[1])

# O valor de referência vem do diagnóstico
# já realizado sobre o CSV original.

ESPERADO = 7728394

if total != ESPERADO:
    raise RuntimeError(
        "Falha: quantidade de registros diferente da origem."
    )

if ids != total:
    raise RuntimeError(
        "Falha: identificadores ausentes ou duplicados."
    )

if suspeitas[0] != 22:
    raise RuntimeError(
        "Falha: divergência nas temperaturas suspeitas."
    )

# ============================================
# 3. PUBLICAÇÃO DA STAGING
# ============================================

# Somente publica após os testes básicos.
# A transação protege a tabela definitiva.

con.execute("BEGIN TRANSACTION")

try:
    con.execute("""
        CREATE OR REPLACE TABLE StagingAcidentes AS
        SELECT * FROM staging_candidata
    """)

    con.execute("COMMIT")

except Exception:
    con.execute("ROLLBACK")
    raise

print("\nSTAGING publicada com sucesso.")
print("Banco:", BANCO)
print("Tempo:", round(time.time() - inicio, 2), "segundos")

con.close()

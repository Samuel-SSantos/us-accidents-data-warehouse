
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

con = duckdb.connect(str(BANCO))

print("=== MARCO 3 — DIMCONDICAOCLIMATICA ===")

try:
    # Preservamos os valores originais e os NULLs.
    # Cada combinação distinta recebe uma chave.
    con.execute("""
        CREATE TEMP TABLE DimClima_Candidata AS

        WITH combinacoes AS (
            SELECT DISTINCT
                Weather_Condition,
                Wind_Direction
            FROM StagingAcidentes
        )

        SELECT
            CAST(
                ROW_NUMBER() OVER (
                    ORDER BY
                        Weather_Condition NULLS FIRST,
                        Wind_Direction NULLS FIRST
                ) AS BIGINT
            ) AS ClimaKey,

            Weather_Condition,
            Wind_Direction

        FROM combinacoes
    """)

    total, chaves, nulos = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT ClimaKey),
            COUNT(*) FILTER (WHERE ClimaKey IS NULL)
        FROM DimClima_Candidata
    """).fetchone()

    print("Combinações climáticas:", total)
    print("Chaves únicas:", chaves)
    print("Chaves nulas:", nulos)

    assert total > 0
    assert chaves == total
    assert nulos == 0

    print("\nValidando associação com a STAGING...")

    resultado = con.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(d.ClimaKey) AS associados,
            COUNT(*) FILTER (
                WHERE d.ClimaKey IS NULL
            ) AS sem_correspondencia

        FROM StagingAcidentes s

        LEFT JOIN DimClima_Candidata d
            ON s.Weather_Condition
               IS NOT DISTINCT FROM d.Weather_Condition
           AND s.Wind_Direction
               IS NOT DISTINCT FROM d.Wind_Direction
    """).fetchone()

    print("Total após associação:", resultado[0])
    print("Acidentes associados:", resultado[1])
    print("Sem correspondência:", resultado[2])

    assert resultado[0] == 7728394
    assert resultado[1] == resultado[0]
    assert resultado[2] == 0

    # Publicação somente após aprovação dos testes.
    con.execute("BEGIN TRANSACTION")

    try:
        con.execute("""
            CREATE OR REPLACE TABLE DimCondicaoClimatica AS
            SELECT * FROM DimClima_Candidata
        """)

        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise

    print("\nDimCondicaoClimatica publicada com sucesso.")
    print("Demais tabelas preservadas.")

finally:
    con.close()

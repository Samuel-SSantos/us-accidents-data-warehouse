
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

con = duckdb.connect(str(BANCO))

print("=== MARCO 3 — DIMLUMINOSIDADE ===")

try:
    # Criamos uma dimensão com as combinações
    # distintas dos quatro indicadores.
    # Os valores NULL são preservados.

    con.execute("""
        CREATE TEMP TABLE DimLuminosidade_Candidata AS

        WITH combinacoes AS (
            SELECT DISTINCT
                Sunrise_Sunset,
                Civil_Twilight,
                Nautical_Twilight,
                Astronomical_Twilight
            FROM StagingAcidentes
        )

        SELECT
            CAST(
                ROW_NUMBER() OVER (
                    ORDER BY
                        Sunrise_Sunset NULLS FIRST,
                        Civil_Twilight NULLS FIRST,
                        Nautical_Twilight NULLS FIRST,
                        Astronomical_Twilight NULLS FIRST
                ) AS BIGINT
            ) AS LuminosidadeKey,

            Sunrise_Sunset,
            Civil_Twilight,
            Nautical_Twilight,
            Astronomical_Twilight

        FROM combinacoes
    """)

    total, chaves, nulos = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT LuminosidadeKey),
            COUNT(*) FILTER (
                WHERE LuminosidadeKey IS NULL
            )
        FROM DimLuminosidade_Candidata
    """).fetchone()

    print("Combinações de luminosidade:", total)
    print("Chaves únicas:", chaves)
    print("Chaves nulas:", nulos)

    assert total > 0
    assert chaves == total
    assert nulos == 0

    print("\nValidando associação com a STAGING...")

    resultado = con.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(d.LuminosidadeKey) AS associados,
            COUNT(*) FILTER (
                WHERE d.LuminosidadeKey IS NULL
            ) AS sem_correspondencia

        FROM StagingAcidentes s

        LEFT JOIN DimLuminosidade_Candidata d
            ON s.Sunrise_Sunset
               IS NOT DISTINCT FROM d.Sunrise_Sunset
           AND s.Civil_Twilight
               IS NOT DISTINCT FROM d.Civil_Twilight
           AND s.Nautical_Twilight
               IS NOT DISTINCT FROM d.Nautical_Twilight
           AND s.Astronomical_Twilight
               IS NOT DISTINCT FROM d.Astronomical_Twilight
    """).fetchone()

    print("Total após associação:", resultado[0])
    print("Acidentes associados:", resultado[1])
    print("Sem correspondência:", resultado[2])

    assert resultado[0] == 7728394
    assert resultado[1] == resultado[0]
    assert resultado[2] == 0

    # Publicamos somente depois da validação.
    con.execute("BEGIN TRANSACTION")

    try:
        con.execute("""
            CREATE OR REPLACE TABLE DimLuminosidade AS
            SELECT * FROM DimLuminosidade_Candidata
        """)

        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise

    print("\nDimLuminosidade publicada com sucesso.")
    print("Demais tabelas preservadas.")

finally:
    con.close()

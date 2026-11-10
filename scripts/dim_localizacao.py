
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

con = duckdb.connect(str(BANCO))

print("=== MARCO 3 — DIMLOCALIZACAO ===")

try:
    # Cada combinação distinta recebe uma chave.
    # NULL é preservado como NULL.
    con.execute("""
        CREATE TEMP TABLE DimLocalizacao_Candidata AS

        WITH localizacoes AS (
            SELECT DISTINCT
                Country,
                State,
                County,
                City,
                Zipcode
            FROM StagingAcidentes
        )

        SELECT
            CAST(
                ROW_NUMBER() OVER (
                    ORDER BY
                        Country NULLS FIRST,
                        State NULLS FIRST,
                        County NULLS FIRST,
                        City NULLS FIRST,
                        Zipcode NULLS FIRST
                ) AS BIGINT
            ) AS LocalizacaoKey,

            Country,
            State,
            County,
            City,
            Zipcode

        FROM localizacoes
    """)

    total, chaves, nulos = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT LocalizacaoKey),
            COUNT(*) FILTER (
                WHERE LocalizacaoKey IS NULL
            )
        FROM DimLocalizacao_Candidata
    """).fetchone()

    print("Localizações distintas:", total)
    print("Chaves únicas:", chaves)
    print("Chaves nulas:", nulos)

    assert total > 0
    assert chaves == total
    assert nulos == 0

    # Validação da associação, incluindo
    # igualdade entre valores NULL.
    print("\nValidando associação com a STAGING...")

    resultado = con.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(d.LocalizacaoKey) AS associados,
            COUNT(*) FILTER (
                WHERE d.LocalizacaoKey IS NULL
            ) AS sem_localizacao

        FROM StagingAcidentes s

        LEFT JOIN DimLocalizacao_Candidata d
            ON s.Country IS NOT DISTINCT FROM d.Country
           AND s.State IS NOT DISTINCT FROM d.State
           AND s.County IS NOT DISTINCT FROM d.County
           AND s.City IS NOT DISTINCT FROM d.City
           AND s.Zipcode IS NOT DISTINCT FROM d.Zipcode
    """).fetchone()

    print("Total após associação:", resultado[0])
    print("Acidentes associados:", resultado[1])
    print("Sem localização:", resultado[2])

    assert resultado[0] == 7728394, (
        "Quantidade de registros alterada após o JOIN."
    )

    assert resultado[1] == resultado[0], (
        "Existem acidentes sem localização correspondente."
    )

    assert resultado[2] == 0

    # Publicação após validação.
    con.execute("BEGIN TRANSACTION")

    try:
        con.execute("""
            CREATE OR REPLACE TABLE DimLocalizacao AS
            SELECT * FROM DimLocalizacao_Candidata
        """)

        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise

    print("\nDimLocalizacao publicada com sucesso.")
    print("STAGING, DimData e DimHora preservadas.")

finally:
    con.close()

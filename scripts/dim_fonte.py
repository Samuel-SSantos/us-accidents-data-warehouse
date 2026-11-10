
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

ESPERADO = 7728394

DISTRIBUICAO_ESPERADA = [
    ("Source1", 4325632),
    ("Source2", 3305373),
    ("Source3", 97389)
]

con = duckdb.connect(str(BANCO))

print("=== MARCO 3 — DIMFONTE ===")

try:
    # Cada fonte distinta recebe uma chave.
    # Mantemos o valor original de Source.

    con.execute("""
        CREATE TEMP TABLE DimFonte_Candidata AS

        WITH fontes AS (
            SELECT DISTINCT Source
            FROM StagingAcidentes
        )

        SELECT
            CAST(
                ROW_NUMBER() OVER (
                    ORDER BY Source NULLS FIRST
                ) AS INTEGER
            ) AS FonteKey,

            Source

        FROM fontes
    """)

    total, chaves, nulos = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT FonteKey),
            COUNT(*) FILTER (
                WHERE FonteKey IS NULL
            )
        FROM DimFonte_Candidata
    """).fetchone()

    print("Fontes cadastradas:", total)
    print("Chaves únicas:", chaves)
    print("Chaves nulas:", nulos)

    assert total == 3
    assert chaves == total
    assert nulos == 0

    print("\nValidando associação com STAGING...")

    resultado = con.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(d.FonteKey) AS associados,
            COUNT(*) FILTER (
                WHERE d.FonteKey IS NULL
            ) AS sem_correspondencia

        FROM StagingAcidentes s

        LEFT JOIN DimFonte_Candidata d
            ON s.Source IS NOT DISTINCT FROM d.Source
    """).fetchone()

    print("Total após associação:", resultado[0])
    print("Acidentes associados:", resultado[1])
    print("Sem correspondência:", resultado[2])

    assert resultado[0] == ESPERADO
    assert resultado[1] == ESPERADO
    assert resultado[2] == 0

    # Conferimos a distribuição da origem.
    distribuicao = con.execute("""
        SELECT Source, COUNT(*)
        FROM StagingAcidentes
        GROUP BY Source
        ORDER BY Source
    """).fetchall()

    print("\nDistribuição por fonte:")

    for linha in distribuicao:
        print(linha)

    assert distribuicao == DISTRIBUICAO_ESPERADA, (
        "Distribuição divergente do diagnóstico."
    )

    # Publicação protegida por transação.
    con.execute("BEGIN TRANSACTION")

    try:
        con.execute("""
            CREATE OR REPLACE TABLE DimFonte AS
            SELECT * FROM DimFonte_Candidata
        """)

        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise

    print("\nDimFonte publicada com sucesso.")
    print("Todas as demais tabelas preservadas.")

finally:
    con.close()

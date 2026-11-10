
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

con = duckdb.connect(str(BANCO))

print("=== MARCO 3 — DIMSEVERIDADE ===")

try:
    con.execute("""
        CREATE TEMP TABLE DimSeveridade_Candidata AS

        WITH niveis AS (
            SELECT DISTINCT Severity
            FROM StagingAcidentes
        )

        SELECT
            CAST(
                ROW_NUMBER() OVER (
                    ORDER BY Severity NULLS FIRST
                ) AS INTEGER
            ) AS SeveridadeKey,

            Severity,

            CASE
                WHEN Severity = 1 THEN 'Nivel 1'
                WHEN Severity = 2 THEN 'Nivel 2'
                WHEN Severity = 3 THEN 'Nivel 3'
                WHEN Severity = 4 THEN 'Nivel 4'
                ELSE 'Nao informado'
            END AS DescricaoSeveridade

        FROM niveis
    """)

    total, chaves, nulos = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT SeveridadeKey),
            COUNT(*) FILTER (
                WHERE SeveridadeKey IS NULL
            )
        FROM DimSeveridade_Candidata
    """).fetchone()

    print("Níveis cadastrados:", total)
    print("Chaves únicas:", chaves)
    print("Chaves nulas:", nulos)

    assert total == 4
    assert chaves == total
    assert nulos == 0

    print("\nValidando associação com a STAGING...")

    resultado = con.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(d.SeveridadeKey) AS associados,
            COUNT(*) FILTER (
                WHERE d.SeveridadeKey IS NULL
            ) AS sem_correspondencia

        FROM StagingAcidentes s

        LEFT JOIN DimSeveridade_Candidata d
            ON s.Severity IS NOT DISTINCT FROM d.Severity
    """).fetchone()

    print("Total após associação:", resultado[0])
    print("Acidentes associados:", resultado[1])
    print("Sem correspondência:", resultado[2])

    assert resultado[0] == 7728394
    assert resultado[1] == resultado[0]
    assert resultado[2] == 0

    # Validação da distribuição conhecida.
    distribuicao = con.execute("""
        SELECT Severity, COUNT(*)
        FROM StagingAcidentes
        GROUP BY Severity
        ORDER BY Severity
    """).fetchall()

    esperado = [
        (1, 67366),
        (2, 6156981),
        (3, 1299337),
        (4, 204710)
    ]

    print("\nDistribuição por severidade:")
    for linha in distribuicao:
        print(linha)

    assert distribuicao == esperado, (
        "Distribuição diferente do diagnóstico original."
    )

    con.execute("BEGIN TRANSACTION")

    try:
        con.execute("""
            CREATE OR REPLACE TABLE DimSeveridade AS
            SELECT * FROM DimSeveridade_Candidata
        """)

        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise

    print("\nDimSeveridade publicada com sucesso.")
    print("Demais tabelas preservadas.")

finally:
    con.close()

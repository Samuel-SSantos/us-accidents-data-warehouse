
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

CAMPOS = [
    "Amenity", "Bump", "Crossing", "Give_Way",
    "Junction", "No_Exit", "Railway", "Roundabout",
    "Station", "Stop", "Traffic_Calming",
    "Traffic_Signal", "Turning_Loop"
]

ESPERADO = 7728394

con = duckdb.connect(str(BANCO))

print("=== MARCO 3 — DIMVIA ===")

try:
    # Verificamos se existem valores diferentes
    # de TRUE, FALSE ou NULL antes da conversão.

    print("\n1. Verificando valores dos indicadores...")

    for campo in CAMPOS:
        invalidos = con.execute(f"""
            SELECT COUNT(*)
            FROM StagingAcidentes
            WHERE "{campo}" IS NOT NULL
              AND UPPER(TRIM("{campo}"))
                  NOT IN ('TRUE', 'FALSE')
        """).fetchone()[0]

        print(f"{campo}: {invalidos} valores inválidos")

        assert invalidos == 0, (
            f"Valores inesperados em {campo}"
        )

    # Montamos as expressões de conversão.
    conversoes = [
        f'TRY_CAST("{campo}" AS BOOLEAN) AS "{campo}"'
        for campo in CAMPOS
    ]

    colunas = ",\n".join(conversoes)

    ordenacao = ", ".join(
        f'"{campo}" NULLS FIRST' for campo in CAMPOS
    )

    # Cada combinação distinta das características
    # recebe uma chave substituta.

    con.execute(f"""
        CREATE TEMP TABLE DimVia_Candidata AS

        WITH indicadores AS (
            SELECT
                {colunas}
            FROM StagingAcidentes
        ),

        combinacoes AS (
            SELECT DISTINCT *
            FROM indicadores
        )

        SELECT
            CAST(
                ROW_NUMBER() OVER (
                    ORDER BY {ordenacao}
                ) AS BIGINT
            ) AS ViaKey,

            *

        FROM combinacoes
    """)

    total, chaves, nulos = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT ViaKey),
            COUNT(*) FILTER (WHERE ViaKey IS NULL)
        FROM DimVia_Candidata
    """).fetchone()

    print("\n2. Validação da dimensão")
    print("Combinações distintas:", total)
    print("Chaves únicas:", chaves)
    print("Chaves nulas:", nulos)

    assert total > 0
    assert total == chaves
    assert nulos == 0

    # Associação com todos os registros.
    # NULL é comparado com NULL corretamente.

    condicoes = " AND ".join(
        f'TRY_CAST(s."{campo}" AS BOOLEAN) '
        f'IS NOT DISTINCT FROM d."{campo}"'
        for campo in CAMPOS
    )

    print("\n3. Validando associação com STAGING...")

    resultado = con.execute(f"""
        SELECT
            COUNT(*) AS total,
            COUNT(d.ViaKey) AS associados,
            COUNT(*) FILTER (
                WHERE d.ViaKey IS NULL
            ) AS sem_correspondencia

        FROM StagingAcidentes s

        LEFT JOIN DimVia_Candidata d
            ON {condicoes}
    """).fetchone()

    print("Total após associação:", resultado[0])
    print("Acidentes associados:", resultado[1])
    print("Sem correspondência:", resultado[2])

    assert resultado[0] == ESPERADO
    assert resultado[1] == ESPERADO
    assert resultado[2] == 0

    # Publicamos somente após os testes.

    con.execute("BEGIN TRANSACTION")

    try:
        con.execute("""
            CREATE OR REPLACE TABLE DimVia AS
            SELECT * FROM DimVia_Candidata
        """)

        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise

    print("\nDimVia publicada com sucesso.")
    print("Demais tabelas preservadas.")

finally:
    con.close()

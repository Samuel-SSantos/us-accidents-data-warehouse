
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

con = duckdb.connect(str(BANCO))

print("=== MARCO 3 — DIMHORA ===")

try:
    con.execute("""
        CREATE TEMP TABLE DimHora_Candidata AS

        SELECT
            hora * 100 + minuto AS HoraKey,

            hora AS Hora,
            minuto AS Minuto,

            CASE
                WHEN hora BETWEEN 6 AND 11
                    THEN 'Morning'
                WHEN hora BETWEEN 12 AND 17
                    THEN 'Afternoon'
                WHEN hora BETWEEN 18 AND 23
                    THEN 'Evening'
                ELSE 'Night'
            END AS PeriodoDia

        FROM range(0, 24) AS h(hora)
        CROSS JOIN range(0, 60) AS m(minuto)
    """)

    total, chaves = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT HoraKey)
        FROM DimHora_Candidata
    """).fetchone()

    print("Horários criados:", total)
    print("Chaves únicas:", chaves)

    assert total == 1440
    assert chaves == total

    # Verifica se todos os acidentes encontram
    # um horário na dimensão candidata.
    total_acidentes, associados, sem_hora = con.execute("""
        SELECT
            COUNT(*),
            COUNT(h.HoraKey),
            COUNT(*) FILTER (WHERE h.HoraKey IS NULL)
        FROM StagingAcidentes s
        LEFT JOIN DimHora_Candidata h
            ON (
                HOUR(s.Start_Time) * 100
                + MINUTE(s.Start_Time)
            ) = h.HoraKey
    """).fetchone()

    print("Acidentes:", total_acidentes)
    print("Acidentes associados:", associados)
    print("Sem horário:", sem_hora)

    assert total_acidentes == 7728394
    assert associados == total_acidentes
    assert sem_hora == 0

    con.execute("BEGIN TRANSACTION")

    try:
        con.execute("""
            CREATE OR REPLACE TABLE DimHora AS
            SELECT * FROM DimHora_Candidata
        """)

        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise

    print("\nDimHora publicada com sucesso.")
    print("STAGING e DimData preservadas.")

finally:
    con.close()

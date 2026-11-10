
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

con = duckdb.connect(str(BANCO), read_only=True)

print("=== VALIDAÇÃO STAGING → DIMDATA ===")

resultado = con.execute("""
    SELECT
        COUNT(*) AS total_acidentes,

        COUNT(d.DataKey) AS acidentes_com_data,

        COUNT(*) FILTER (
            WHERE d.DataKey IS NULL
        ) AS acidentes_sem_data,

        COUNT(DISTINCT d.DataKey)
            AS datas_utilizadas

    FROM StagingAcidentes s

    LEFT JOIN DimData d
        ON CAST(s.Start_Time AS DATE) = d.Data
""").fetchone()

print("Total de acidentes:", resultado[0])
print("Acidentes com data:", resultado[1])
print("Acidentes sem data:", resultado[2])
print("Datas utilizadas:", resultado[3])

assert resultado[0] == 7728394, (
    "Quantidade inesperada após o JOIN."
)

assert resultado[1] == resultado[0], (
    "Existem acidentes sem correspondência na DimData."
)

assert resultado[2] == 0, (
    "Foram encontradas datas sem correspondência."
)

print("\nIntegridade entre STAGING e DimData: OK")

print("\n=== ACIDENTES POR ESTAÇÃO ===")

estacoes = con.execute("""
    SELECT
        d.Season,
        COUNT(*) AS acidentes
    FROM StagingAcidentes s
    JOIN DimData d
        ON CAST(s.Start_Time AS DATE) = d.Data
    GROUP BY d.Season
    ORDER BY acidentes DESC
""").fetchall()

for estacao, quantidade in estacoes:
    print(estacao, ":", quantidade)

con.close()

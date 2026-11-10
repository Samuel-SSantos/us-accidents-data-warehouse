
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
ARQUIVO = BASE / "dados/bruto/US_Accidents_March23.csv"
SAIDA = BASE / "resultados"
SAIDA.mkdir(exist_ok=True)

con = duckdb.connect()
con.execute("SET threads = 4")
con.execute("SET memory_limit = '2GB'")

caminho = str(ARQUIVO).replace("'", "''")

con.execute(f"""
CREATE VIEW acidentes AS
SELECT
    ID,
    Source,
    State,
    Severity,
    TRY_CAST(Start_Time AS TIMESTAMP) AS inicio,
    TRY_CAST(End_Time AS TIMESTAMP) AS fim,
    TRY_CAST("Temperature(F)" AS DOUBLE) AS temperatura_f,
    "Weather_Condition" AS clima
FROM read_csv(
    '{caminho}',
    header=true,
    all_varchar=true,
    delim=','
)
""")

print("=== INVESTIGAÇÃO DE ANOMALIAS ===")

# 1. Temperaturas suspeitas
temperaturas = con.execute("""
SELECT ID, State, inicio, temperatura_f, clima
FROM acidentes
WHERE temperatura_f < -100
   OR temperatura_f > 140
ORDER BY temperatura_f
""").df()

print("\nTEMPERATURAS SUSPEITAS")
print(temperaturas.to_string(index=False))

temperaturas.to_csv(
    SAIDA / "temperaturas_suspeitas.csv",
    index=False
)

# 2. Durações muito longas
duracoes = con.execute("""
SELECT
    ID,
    Source,
    State,
    inicio,
    fim,
    ROUND(
        date_diff('minute', inicio, fim) / 60.0,
        2
    ) AS duracao_horas
FROM acidentes
WHERE date_diff('hour', inicio, fim) > 168
ORDER BY duracao_horas DESC
LIMIT 30
""").df()

print("\n30 MAIORES DURAÇÕES")
print(duracoes.to_string(index=False))

duracoes.to_csv(
    SAIDA / "duracoes_suspeitas.csv",
    index=False
)

# 3. Distribuição anual e por fonte
distribuicao = con.execute("""
SELECT
    YEAR(inicio) AS ano,
    Source,
    COUNT(*) AS registros
FROM acidentes
GROUP BY ano, Source
ORDER BY ano, Source
""").df()

print("\nDISTRIBUIÇÃO ANUAL POR FONTE")
print(distribuicao.to_string(index=False))

distribuicao.to_csv(
    SAIDA / "distribuicao_anual_fontes.csv",
    index=False
)

con.close()
print("\nInvestigação concluída.")

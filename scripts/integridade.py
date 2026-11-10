
from pathlib import Path
import duckdb
import json
import time

BASE = Path(__file__).resolve().parents[1]
PASTA_DADOS = BASE / "dados" / "bruto"
SAIDA = BASE / "resultados"
SAIDA.mkdir(exist_ok=True)

ARQUIVO = PASTA_DADOS / "US_Accidents_March23.csv"
if not ARQUIVO.exists():
    raise FileNotFoundError(ARQUIVO)

inicio = time.time()

con = duckdb.connect()
con.execute("SET threads = 4")
con.execute("SET memory_limit = '2GB'")

# Escape seguro do caminho para a consulta SQL
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
    TRY_CAST(Start_Lat AS DOUBLE) AS latitude,
    TRY_CAST(Start_Lng AS DOUBLE) AS longitude,
    TRY_CAST("Temperature(F)" AS DOUBLE) AS temperatura,
    TRY_CAST("Humidity(%)" AS DOUBLE) AS umidade,
    TRY_CAST("Visibility(mi)" AS DOUBLE) AS visibilidade,
    TRY_CAST("Distance(mi)" AS DOUBLE) AS distancia
FROM read_csv(
    '{caminho}',
    header=true,
    all_varchar=true,
    delim=',',
    sample_size=20000
)
""")

print("=== AUDITORIA DE INTEGRIDADE ===")

# 1. Período
periodo = con.execute("""
SELECT
    MIN(inicio),
    MAX(inicio),
    COUNT(*) FILTER (WHERE inicio IS NULL),
    COUNT(*) FILTER (WHERE fim IS NULL)
FROM acidentes
""").fetchone()

print("\n1. PERÍODO")
print("Primeiro registro:", periodo[0])
print("Último registro:", periodo[1])
print("Datas iniciais inválidas:", periodo[2])
print("Datas finais inválidas:", periodo[3])

# 2. Durações
duracoes = con.execute("""
SELECT
    COUNT(*) FILTER (
        WHERE fim < inicio
    ),
    COUNT(*) FILTER (
        WHERE date_diff('hour', inicio, fim) > 168
    ),
    COUNT(*) FILTER (
        WHERE fim = inicio
    )
FROM acidentes
""").fetchone()

print("\n2. DURAÇÃO")
print("Negativas:", duracoes[0])
print("Superiores a 7 dias:", duracoes[1])
print("Iguais a zero:", duracoes[2])

# 3. Validação de valores
validacao = con.execute("""
SELECT
    COUNT(*) FILTER (
        WHERE temperatura < -100 OR temperatura > 140
    ),
    COUNT(*) FILTER (
        WHERE umidade < 0 OR umidade > 100
    ),
    COUNT(*) FILTER (
        WHERE latitude NOT BETWEEN -90 AND 90
           OR longitude NOT BETWEEN -180 AND 180
    ),
    COUNT(*) FILTER (
        WHERE visibilidade < 0
    ),
    COUNT(*) FILTER (
        WHERE distancia < 0
    )
FROM acidentes
""").fetchone()

print("\n3. VALORES SUSPEITOS")
nomes = [
    "Temperaturas fora dos limites de triagem",
    "Umidade fora de 0 a 100%",
    "Coordenadas geográficas inválidas",
    "Visibilidade negativa",
    "Distância negativa"
]

for nome, valor in zip(nomes, validacao):
    print(f"{nome}: {valor}")

# 4. Estados
estados = con.execute("""
SELECT State, COUNT(*) AS total
FROM acidentes
GROUP BY State
ORDER BY total DESC
LIMIT 10
""").fetchall()

print("\n4. TOP 10 ESTADOS")
for estado, total in estados:
    print(estado, total)

# 5. Fontes
fontes = con.execute("""
SELECT Source, COUNT(*) AS total
FROM acidentes
GROUP BY Source
ORDER BY total DESC
""").fetchall()

print("\n5. FONTES DOS REGISTROS")
for fonte, total in fontes:
    print(fonte, total)

# Salvar relatório
relatorio = {
    "periodo": [str(periodo[0]), str(periodo[1])],
    "datas_invalidas": {
        "inicio": periodo[2],
        "fim": periodo[3]
    },
    "duracoes": {
        "negativas": duracoes[0],
        "maiores_7_dias": duracoes[1],
        "zero": duracoes[2]
    },
    "valores_suspeitos": dict(zip(nomes, validacao)),
    "top_10_estados": estados,
    "fontes": fontes
}

with (SAIDA / "integridade.json").open(
    "w", encoding="utf-8"
) as arquivo:
    json.dump(
        relatorio,
        arquivo,
        indent=2,
        ensure_ascii=False
    )

print("\nAuditoria concluída!")
print("Tempo:", round(time.time() - inicio, 2), "segundos")
print("Relatório: resultados/integridade.json")

con.close()

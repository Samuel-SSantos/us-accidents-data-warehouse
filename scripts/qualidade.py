
from pathlib import Path
import duckdb
import json
import time

BASE = Path(__file__).resolve().parents[1]
ARQUIVO = BASE / "dados" / "bruto" / "US_Accidents_March23.csv"
SAIDA = BASE / "resultados"
SAIDA.mkdir(exist_ok=True)

# Localiza automaticamente o único CSV da pasta,
# caso o arquivo não se chame dataset.csv.
if not ARQUIVO.exists():
    arquivos = list((BASE / "dados" / "bruto").glob("*.csv"))
    if len(arquivos) != 1:
        raise RuntimeError(
            "Informe o nome do CSV ou mantenha apenas um CSV na pasta bruto."
        )
    ARQUIVO = arquivos[0]

inicio = time.time()
con = duckdb.connect()
con.execute("SET threads = 4")
con.execute("SET memory_limit = '2GB'")

print("=== DIAGNÓSTICO DE QUALIDADE ===")
print("Arquivo:", ARQUIVO.name)

# Lê o CSV preservando inicialmente os valores como texto.
# Isso evita inferências de tipo prematuras.
caminho = str(ARQUIVO).replace("'", "''")

con.execute(f"""
    CREATE VIEW acidentes AS
    SELECT *
    FROM read_csv(
        '{caminho}',
        header = true,
        all_varchar = true,
        delim = ',',
        sample_size = 20000
    )
""")

print("\n1. CONTAGEM DE REGISTROS")
total = con.execute(
    "SELECT COUNT(*) FROM acidentes"
).fetchone()[0]
print("Total:", f"{total:,}")

print("\n2. IDENTIFICADORES")
ids = con.execute("""
    SELECT
        COUNT(DISTINCT ID) AS distintos,
        COUNT(*) FILTER (
            WHERE ID IS NULL OR TRIM(ID) = ''
        ) AS ids_ausentes
    FROM acidentes
""").fetchone()

print("IDs distintos:", ids[0])
print("IDs ausentes:", ids[1])
print("IDs repetidos além da primeira ocorrência:",
      total - ids[0] - ids[1])

print("\n3. VALORES AUSENTES POR COLUNA")

colunas = [
    linha[0]
    for linha in con.execute(
        "DESCRIBE acidentes"
    ).fetchall()
]

expressoes = []
for coluna in colunas:
    nome = '"' + coluna.replace('"', '""') + '"'
    expressoes.append(
        f"COUNT(*) FILTER (WHERE {nome} IS NULL "
        f"OR TRIM({nome}) = '')"
    )

consulta = "SELECT " + ", ".join(expressoes) + " FROM acidentes"
valores = con.execute(consulta).fetchone()

ausentes = []
for coluna, quantidade in zip(colunas, valores):
    percentual = round(quantidade * 100 / total, 2) if total else 0
    ausentes.append({
        "coluna": coluna,
        "ausentes": quantidade,
        "percentual": percentual
    })

ausentes.sort(
    key=lambda item: item["percentual"],
    reverse=True
)

for item in ausentes:
    print(
        f"{item['coluna']}: "
        f"{item['percentual']:.2f}% ausentes"
    )

print("\n4. DISTRIBUIÇÃO DA GRAVIDADE")
gravidade = con.execute("""
    SELECT Severity, COUNT(*) AS quantidade
    FROM acidentes
    GROUP BY Severity
    ORDER BY Severity
""").fetchall()

for nivel, quantidade in gravidade:
    print(nivel, quantidade)

relatorio = {
    "total_registros": total,
    "ids_distintos": ids[0],
    "ids_ausentes": ids[1],
    "ausentes_por_coluna": ausentes,
    "gravidade": gravidade,
    "tempo_segundos": round(time.time() - inicio, 2)
}

with (SAIDA / "qualidade.json").open(
    "w", encoding="utf-8"
) as f:
    json.dump(relatorio, f, indent=2, ensure_ascii=False)

print("\nRelatório salvo em resultados/qualidade.json")
print("Tempo total:", round(time.time() - inicio, 2), "segundos")
con.close()

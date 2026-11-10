
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== VALIDAÇÃO DA STAGING ===")

# 1. Estrutura da tabela
print("\n1. TIPOS DAS COLUNAS")

estrutura = con.execute("""
    DESCRIBE StagingAcidentes
""").fetchall()

for coluna in estrutura:
    print(coluna[0], "->", coluna[1])

# 2. Integridade
print("\n2. INTEGRIDADE DOS REGISTROS")

integridade = con.execute("""
SELECT
    COUNT(*) AS total,
    COUNT(DISTINCT Accident_ID) AS ids_unicos,
    COUNT(*) FILTER (
        WHERE Accident_ID IS NULL
    ) AS ids_nulos,
    COUNT(*) FILTER (
        WHERE Start_Time IS NULL
    ) AS datas_nulas,
    COUNT(*) FILTER (
        WHERE Duration_Minutes < 0
    ) AS duracoes_negativas
FROM StagingAcidentes
""").fetchone()

print("Total:", integridade[0])
print("IDs únicos:", integridade[1])
print("IDs nulos:", integridade[2])
print("Datas nulas:", integridade[3])
print("Durações negativas:", integridade[4])

# 3. Conversões
print("\n3. EXEMPLOS DE CONVERSÕES")

amostra = con.execute("""
SELECT
    Accident_ID,
    ROUND(Temperature_F_Original, 2) AS temp_f,
    ROUND(Temperature_C, 2) AS temp_c,
    ROUND(Distance_km, 3) AS distancia_km,
    ROUND(Precipitation_mm, 3) AS chuva_mm,
    ROUND(Duration_Minutes, 2) AS duracao_min
FROM StagingAcidentes
WHERE Temperature_C IS NOT NULL
LIMIT 10
""").fetchall()

for linha in amostra:
    print(linha)

# 4. Qualidade
print("\n4. INDICADORES DE QUALIDADE")

qualidade = con.execute("""
SELECT
    COUNT(*) FILTER (
        WHERE Temperature_Suspect
    ) AS temperaturas_suspeitas,
    COUNT(*) FILTER (
        WHERE Duration_Suspect
    ) AS duracoes_suspeitas,
    COUNT(*) FILTER (
        WHERE Temperature_C IS NULL
    ) AS temperaturas_nulas,
    COUNT(*) FILTER (
        WHERE Precipitation_mm IS NULL
    ) AS precipitacoes_nulas,
    COUNT(*) FILTER (
        WHERE End_Lat IS NULL
    ) AS coordenadas_finais_nulas
FROM StagingAcidentes
""").fetchone()

nomes = [
    "Temperaturas suspeitas",
    "Durações suspeitas",
    "Temperaturas nulas após tratamento",
    "Precipitações nulas",
    "Coordenadas finais nulas"
]

for nome, valor in zip(nomes, qualidade):
    print(f"{nome}: {valor}")

# 5. Testes obrigatórios
print("\n5. TESTES AUTOMÁTICOS")

assert integridade[0] == 7728394, "Total incorreto"
assert integridade[1] == integridade[0], "IDs duplicados"
assert integridade[2] == 0, "IDs nulos"
assert integridade[3] == 0, "Datas iniciais nulas"
assert integridade[4] == 0, "Durações negativas"
assert qualidade[0] == 22, "Temperaturas suspeitas divergentes"
assert qualidade[1] == 6824, "Durações suspeitas divergentes"

print("Todos os testes básicos passaram!")

con.close()

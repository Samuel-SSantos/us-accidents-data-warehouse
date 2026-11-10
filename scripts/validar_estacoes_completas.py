
from pathlib import Path
import csv
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"
SAIDA = BASE / "resultados" / "estacoes_completas.csv"

ESPERADO = 7728394

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

SAIDA.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — VALIDACAO SAZONAL ===")

try:
    # Primeiro, identificamos os intervalos
    # de cada estacao no calendario DimData.
    calendario = con.execute("""
        SELECT
            Season_Year,
            Season,
            MIN(DataKey) AS Primeira_Data,
            MAX(DataKey) AS Ultima_Data,
            COUNT(*) AS Dias_Calendario

        FROM DimData

        GROUP BY Season_Year, Season

        ORDER BY Primeira_Data
    """).fetchall()

    inicio_base, fim_base = con.execute("""
        SELECT MIN(DataKey), MAX(DataKey)
        FROM DimData
    """).fetchone()

    # A primeira e a ultima estacao do
    # calendario podem estar incompletas.
    estacoes = {}

    for ano, estacao, inicio, fim, dias in calendario:
        completa = (
            inicio > inicio_base
            and fim < fim_base
        )

        estacoes[(ano, estacao)] = {
            "inicio": inicio,
            "fim": fim,
            "dias": dias,
            "completa": completa
        }

    # Contagem dos acidentes por estacao
    # e por fonte, usando o ano da estacao.
    linhas = con.execute("""
        SELECT
            d.Season_Year,
            d.Season,
            fo.Source,
            SUM(f.Accident_Count) AS Acidentes

        FROM FatoAcidente f

        JOIN DimData d
            ON f.DataKey = d.DataKey

        JOIN DimFonte fo
            ON f.FonteKey = fo.FonteKey

        GROUP BY
            d.Season_Year,
            d.Season,
            fo.Source

        ORDER BY
            d.Season_Year,
            d.Season,
            fo.Source
    """).fetchall()

    total = sum(linha[3] for linha in linhas)
    assert total == ESPERADO

    totais_estacao = {}

    for ano, estacao, fonte, quantidade in linhas:
        chave = (ano, estacao)
        totais_estacao[chave] = (
            totais_estacao.get(chave, 0) + quantidade
        )

    print("\n1. COBERTURA DAS ESTACOES")
    print("-" * 85)

    for chave, dados in estacoes.items():
        ano, estacao = chave
        quantidade = totais_estacao.get(chave, 0)

        status = (
            "CALENDARIO COMPLETO"
            if dados["completa"]
            else "PERIODO PARCIAL"
        )

        print(
            f"{ano} | {estacao:7} | "
            f"{dados['dias']:3} dias | "
            f"{quantidade:9,} acidentes | {status}"
        )

    print("\n2. VALIDACAO")
    print("Acidentes preservados:", total)
    print("Estacoes identificadas:", len(estacoes))

    # Exportacao com a informacao da fonte.
    with SAIDA.open(
        "w", newline="", encoding="utf-8-sig"
    ) as arquivo:

        escritor = csv.writer(arquivo)

        escritor.writerow([
            "Ano_Estacao",
            "Estacao",
            "Fonte",
            "Inicio_Calendario",
            "Fim_Calendario",
            "Dias_Calendario",
            "Calendario_Completo",
            "Total_Acidentes"
        ])

        for ano, estacao, fonte, quantidade in linhas:
            dados = estacoes[(ano, estacao)]

            escritor.writerow([
                ano,
                estacao,
                fonte,
                dados["inicio"],
                dados["fim"],
                dados["dias"],
                dados["completa"],
                quantidade
            ])

    print("\nArquivo gerado:", SAIDA)
    print("\nVALIDACAO SAZONAL CONCLUIDA.")
    print("Nenhuma tabela foi modificada.")

finally:
    con.close()

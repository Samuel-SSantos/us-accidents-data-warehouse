
from pathlib import Path
import csv
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"
SAIDA = BASE / "resultados" / "fontes_ano_severidade.csv"

ESPERADO = 7728394

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

SAIDA.parent.mkdir(parents=True, exist_ok=True)

# Consulta somente de leitura.
con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — ANALISE DAS FONTES ===")

try:
    consulta = """
        SELECT
            d.Ano,
            fo.Source AS Fonte,
            sv.Severity AS Severidade,
            SUM(f.Accident_Count) AS Total_Acidentes

        FROM FatoAcidente f

        JOIN DimData d
            ON f.DataKey = d.DataKey

        JOIN DimFonte fo
            ON f.FonteKey = fo.FonteKey

        JOIN DimSeveridade sv
            ON f.SeveridadeKey = sv.SeveridadeKey

        GROUP BY
            d.Ano,
            fo.Source,
            sv.Severity

        ORDER BY
            d.Ano,
            fo.Source,
            sv.Severity
    """

    linhas = con.execute(consulta).fetchall()

    total = sum(linha[3] for linha in linhas)

    print("\nTotal de acidentes:", total)
    assert total == ESPERADO

    # Consolida a participação de cada fonte por ano.
    totais_ano = {}
    totais_fonte = {}

    for ano, fonte, severidade, quantidade in linhas:
        totais_ano[ano] = (
            totais_ano.get(ano, 0) + quantidade
        )

        chave = (ano, fonte)
        totais_fonte[chave] = (
            totais_fonte.get(chave, 0) + quantidade
        )

    print("\n1. Participação das fontes por ano")
    print("-" * 55)

    for ano, fonte in sorted(totais_fonte):
        quantidade = totais_fonte[(ano, fonte)]
        percentual = (
            quantidade / totais_ano[ano] * 100
        )

        print(
            f"{ano} | {fonte} | "
            f"{quantidade:,} | {percentual:.2f}%"
        )

    print("\n2. Severidades presentes por ano e fonte")
    print("-" * 55)

    for ano, fonte, severidade, quantidade in linhas:
        print(
            f"{ano} | {fonte} | "
            f"Severidade {severidade} | {quantidade:,}"
        )

    # Exportação para posterior análise no Power BI.
    with SAIDA.open(
        "w", newline="", encoding="utf-8-sig"
    ) as arquivo:
        escritor = csv.writer(arquivo)

        escritor.writerow([
            "Ano",
            "Fonte",
            "Severidade",
            "Total_Acidentes",
            "Total_Ano_Fonte",
            "Participacao_Fonte_Pct"
        ])

        for ano, fonte, severidade, quantidade in linhas:
            total_fonte = totais_fonte[(ano, fonte)]

            participacao = (
                total_fonte / totais_ano[ano] * 100
            )

            escritor.writerow([
                ano,
                fonte,
                severidade,
                quantidade,
                total_fonte,
                round(participacao, 4)
            ])

    print("\n3. Validação final")
    print("Total preservado:", total)
    print("Anos encontrados:", len(totais_ano))
    print("Combinações encontradas:", len(linhas))

    assert len(totais_ano) == 8

    print("\nArquivo gerado:")
    print(SAIDA)

    print("\nANALISE DAS FONTES CONCLUIDA.")
    print("Nenhuma tabela foi modificada.")

finally:
    con.close()

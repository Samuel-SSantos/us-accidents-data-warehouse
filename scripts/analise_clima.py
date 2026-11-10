
from pathlib import Path
from collections import defaultdict
import csv
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"
SAIDA = BASE / "resultados" / "clima_ano_fonte_severidade.csv"

ESPERADO = 7728394

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

SAIDA.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — ANALISE CLIMATICA ===")

try:
    consulta = """
        SELECT
            d.Ano,
            c.Weather_Condition AS Condicao_Climatica,
            fo.Source AS Fonte,
            sv.Severity AS Severidade,
            SUM(f.Accident_Count) AS Total_Acidentes

        FROM FatoAcidente f

        JOIN DimData d
            ON f.DataKey = d.DataKey

        JOIN DimCondicaoClimatica c
            ON f.ClimaKey = c.ClimaKey

        JOIN DimFonte fo
            ON f.FonteKey = fo.FonteKey

        JOIN DimSeveridade sv
            ON f.SeveridadeKey = sv.SeveridadeKey

        GROUP BY
            d.Ano,
            c.Weather_Condition,
            fo.Source,
            sv.Severity

        ORDER BY
            d.Ano,
            c.Weather_Condition,
            fo.Source,
            sv.Severity
    """

    linhas = con.execute(consulta).fetchall()

    total = sum(linha[4] for linha in linhas)

    assert total == ESPERADO

    por_clima = defaultdict(int)
    severidade_4 = defaultdict(int)
    por_ano = defaultdict(int)
    por_fonte = defaultdict(int)

    for ano, clima, fonte, severidade, quantidade in linhas:
        por_clima[clima] += quantidade
        por_ano[ano] += quantidade
        por_fonte[fonte] += quantidade

        if severidade == 4:
            severidade_4[clima] += quantidade

    ranking = sorted(
        por_clima.items(),
        key=lambda item: item[1],
        reverse=True
    )

    print("\n1. TOP 15 CONDICOES CLIMATICAS")
    print("-" * 75)

    for posicao, (clima, quantidade) in enumerate(
        ranking[:15], start=1
    ):
        graves = severidade_4[clima]
        percentual = graves / quantidade * 100

        nome = clima if clima is not None else "Nao informado"

        print(
            f"{posicao:2}. {nome} | "
            f"Total: {quantidade:,} | "
            f"Sev. 4: {graves:,} ({percentual:.2f}%)"
        )

    print("\n2. REGISTROS SEM CONDICAO CLIMATICA")
    print("-" * 55)

    sem_clima = por_clima.get(None, 0)

    print("Sem informacao:", f"{sem_clima:,}")
    print("Percentual:", f"{sem_clima / total * 100:.2f}%")

    print("\n3. TOTAL POR FONTE")
    print("-" * 45)

    for fonte, quantidade in sorted(por_fonte.items()):
        print(f"{fonte}: {quantidade:,}")

    # Exportação detalhada para o Power BI.
    # O CSV mantém os valores nulos como células vazias.
    with SAIDA.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as arquivo:

        escritor = csv.writer(arquivo)

        escritor.writerow([
            "Ano",
            "Condicao_Climatica",
            "Fonte",
            "Severidade",
            "Total_Acidentes"
        ])

        escritor.writerows(linhas)

    print("\n4. VALIDACAO FINAL")
    print("Total preservado:", total)
    print("Anos encontrados:", len(por_ano))
    print("Fontes encontradas:", len(por_fonte))
    print("Condicoes distintas:", len(por_clima))
    print("Combinacoes detalhadas:", len(linhas))

    assert len(por_ano) == 8
    assert len(por_fonte) == 3
    assert sum(por_clima.values()) == ESPERADO

    print("\nArquivo gerado:")
    print(SAIDA)

    print("\nANALISE CLIMATICA CONCLUIDA.")
    print("Nenhuma tabela foi modificada.")

finally:
    con.close()


from pathlib import Path
import csv
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"
SAIDA = BASE / "resultados" / "estados_ano_fonte_severidade.csv"

ESPERADO = 7728394

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

SAIDA.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — ANALISE POR ESTADOS ===")

try:
    consulta = """
        SELECT
            d.Ano,
            l.State AS Estado,
            fo.Source AS Fonte,
            sv.Severity AS Severidade,
            SUM(f.Accident_Count) AS Total_Acidentes

        FROM FatoAcidente f

        JOIN DimData d
            ON f.DataKey = d.DataKey

        JOIN DimLocalizacao l
            ON f.LocalizacaoKey = l.LocalizacaoKey

        JOIN DimFonte fo
            ON f.FonteKey = fo.FonteKey

        JOIN DimSeveridade sv
            ON f.SeveridadeKey = sv.SeveridadeKey

        GROUP BY
            d.Ano,
            l.State,
            fo.Source,
            sv.Severity

        ORDER BY
            d.Ano,
            l.State,
            fo.Source,
            sv.Severity
    """

    linhas = con.execute(consulta).fetchall()

    total = sum(linha[4] for linha in linhas)

    print("\nTotal de acidentes:", total)
    assert total == ESPERADO

    por_estado = {}
    severidade_4 = {}
    por_ano = {}

    for ano, estado, fonte, severidade, quantidade in linhas:
        por_estado[estado] = (
            por_estado.get(estado, 0) + quantidade
        )

        por_ano[ano] = (
            por_ano.get(ano, 0) + quantidade
        )

        if severidade == 4:
            severidade_4[estado] = (
                severidade_4.get(estado, 0) + quantidade
            )

    ranking = sorted(
        por_estado.items(),
        key=lambda item: item[1],
        reverse=True
    )

    print("\n1. TOP 10 ESTADOS POR ACIDENTES")
    print("-" * 65)

    for posicao, (estado, quantidade) in enumerate(
        ranking[:10], start=1
    ):
        graves = severidade_4.get(estado, 0)
        percentual = graves / quantidade * 100

        print(
            f"{posicao:2}. {estado or 'Nao informado'} | "
            f"Total: {quantidade:,} | "
            f"Sev. 4: {graves:,} ({percentual:.2f}%)"
        )

    print("\n2. TOTAL POR ANO")
    print("-" * 40)

    for ano, quantidade in sorted(por_ano.items()):
        print(f"{ano}: {quantidade:,}")

    # Exportação detalhada para Power BI.
    with SAIDA.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as arquivo:

        escritor = csv.writer(arquivo)

        escritor.writerow([
            "Ano",
            "Estado",
            "Fonte",
            "Severidade",
            "Total_Acidentes"
        ])

        escritor.writerows(linhas)

    print("\n3. VALIDACAO FINAL")

    print("Total preservado:", total)
    print("Estados distintos:", len(por_estado))
    print("Anos encontrados:", len(por_ano))
    print("Combinações detalhadas:", len(linhas))

    assert len(por_ano) == 8
    assert sum(por_estado.values()) == ESPERADO

    print("\nArquivo gerado:")
    print(SAIDA)

    print("\nANALISE DOS ESTADOS CONCLUIDA.")
    print("Nenhuma tabela foi modificada.")

finally:
    con.close()

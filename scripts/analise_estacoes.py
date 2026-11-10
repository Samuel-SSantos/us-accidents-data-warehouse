
from pathlib import Path
import csv
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"
SAIDA = BASE / "resultados" / "estacoes_ano_fonte_severidade.csv"

ESPERADO = 7728394

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

SAIDA.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — ANALISE DAS ESTACOES ===")

try:
    consulta = """
        SELECT
            d.Ano,
            d.Season AS Estacao,
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
            d.Season,
            fo.Source,
            sv.Severity

        ORDER BY
            d.Ano,
            d.Season,
            fo.Source,
            sv.Severity
    """

    linhas = con.execute(consulta).fetchall()

    total = sum(linha[4] for linha in linhas)

    print("\nTotal de acidentes:", total)
    assert total == ESPERADO

    # Consolidação por estação.
    por_estacao = {}

    # Consolidação por ano e estação.
    por_ano_estacao = {}

    # Total por ano, estação e fonte.
    por_grupo = {}

    # Acidentes de severidade 4 por grupo.
    graves_grupo = {}

    for ano, estacao, fonte, severidade, quantidade in linhas:

        por_estacao[estacao] = (
            por_estacao.get(estacao, 0) + quantidade
        )

        chave_ano = (ano, estacao)
        por_ano_estacao[chave_ano] = (
            por_ano_estacao.get(chave_ano, 0) + quantidade
        )

        chave = (ano, estacao, fonte)
        por_grupo[chave] = (
            por_grupo.get(chave, 0) + quantidade
        )

        if severidade == 4:
            graves_grupo[chave] = (
                graves_grupo.get(chave, 0) + quantidade
            )

    print("\n1. Total por estação")
    print("-" * 45)

    for estacao, quantidade in sorted(por_estacao.items()):
        percentual = quantidade / total * 100

        print(
            f"{estacao}: {quantidade:,} "
            f"({percentual:.2f}%)"
        )

    print("\n2. Total por ano e estação")
    print("-" * 45)

    for (ano, estacao), quantidade in sorted(
        por_ano_estacao.items()
    ):
        print(f"{ano} | {estacao} | {quantidade:,}")

    print("\n3. Severidade 4 por ano, estação e fonte")
    print("-" * 65)

    for chave in sorted(por_grupo):
        ano, estacao, fonte = chave
        quantidade = por_grupo[chave]
        graves = graves_grupo.get(chave, 0)
        percentual = graves / quantidade * 100

        print(
            f"{ano} | {estacao} | {fonte} | "
            f"Total: {quantidade:,} | "
            f"Sev. 4: {graves:,} ({percentual:.2f}%)"
        )

    # Exportação das contagens detalhadas.
    with SAIDA.open(
        "w", newline="", encoding="utf-8-sig"
    ) as arquivo:

        escritor = csv.writer(arquivo)

        escritor.writerow([
            "Ano",
            "Estacao",
            "Fonte",
            "Severidade",
            "Total_Acidentes"
        ])

        escritor.writerows(linhas)

    print("\n4. Validação final")
    print("Total preservado:", total)
    print("Estações identificadas:", len(por_estacao))
    print("Combinações detalhadas:", len(linhas))

    assert len(por_estacao) == 4

    print("\nArquivo gerado:")
    print(SAIDA)

    print("\nANALISE DAS ESTACOES CONCLUIDA.")
    print("Nenhuma tabela foi modificada.")

finally:
    con.close()


from pathlib import Path
import csv
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"
SAIDA = BASE / "resultados" / "cobertura_temporal.csv"

ESPERADO = 7728394

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

SAIDA.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — AUDITORIA DE COBERTURA TEMPORAL ===")

try:
    # Uma linha por dia, estação e fonte.
    # Dias sem registros continuam aparecendo.
    consulta = """
        WITH fontes AS (
            SELECT FonteKey, Source
            FROM DimFonte
        ),

        registros_diarios AS (
            SELECT
                DataKey,
                FonteKey,
                SUM(Accident_Count) AS Acidentes
            FROM FatoAcidente
            GROUP BY DataKey, FonteKey
        ),

        calendario_fontes AS (
            SELECT
                d.DataKey,
                d.Season_Year,
                d.Season,
                fo.Source,
                COALESCE(r.Acidentes, 0) AS Acidentes

            FROM DimData d
            CROSS JOIN fontes fo

            LEFT JOIN registros_diarios r
                ON d.DataKey = r.DataKey
               AND fo.FonteKey = r.FonteKey
        )

        SELECT
            Season_Year,
            Season,
            Source,
            COUNT(*) AS Dias_Calendario,
            COUNT(*) FILTER (
                WHERE Acidentes > 0
            ) AS Dias_Com_Registros,
            COUNT(*) FILTER (
                WHERE Acidentes = 0
            ) AS Dias_Sem_Registros,
            SUM(Acidentes) AS Total_Acidentes

        FROM calendario_fontes

        GROUP BY
            Season_Year,
            Season,
            Source

        ORDER BY
            Season_Year,
            Season,
            Source
    """

    linhas = con.execute(consulta).fetchall()

    total = sum(linha[6] for linha in linhas)

    assert total == ESPERADO, (
        "Falha: contagem total divergente."
    )

    print("\n1. COBERTURA POR ESTACAO E FONTE")
    print("-" * 95)

    for (
        ano, estacao, fonte, dias,
        dias_com, dias_sem, acidentes
    ) in linhas:

        cobertura = dias_com / dias * 100

        print(
            f"{ano} | {estacao:7} | {fonte:7} | "
            f"Dias: {dias:3} | "
            f"Com registros: {dias_com:3} | "
            f"Sem registros: {dias_sem:3} | "
            f"{cobertura:6.2f}%"
        )

    print("\n2. COBERTURA GERAL POR FONTE")
    print("-" * 65)

    for fonte in sorted(set(linha[2] for linha in linhas)):
        grupos = [l for l in linhas if l[2] == fonte]

        dias = sum(l[3] for l in grupos)
        dias_com = sum(l[4] for l in grupos)
        acidentes = sum(l[6] for l in grupos)

        print(
            f"{fonte}: {dias_com}/{dias} dias "
            f"({dias_com / dias * 100:.2f}%) | "
            f"{acidentes:,} acidentes"
        )

    with SAIDA.open(
        "w", newline="", encoding="utf-8-sig"
    ) as arquivo:

        escritor = csv.writer(arquivo)

        escritor.writerow([
            "Ano_Estacao",
            "Estacao",
            "Fonte",
            "Dias_Calendario",
            "Dias_Com_Registros",
            "Dias_Sem_Registros",
            "Total_Acidentes",
            "Cobertura_Dias_Pct"
        ])

        for linha in linhas:
            dias = linha[3]
            dias_com = linha[4]

            escritor.writerow([
                *linha,
                round(dias_com / dias * 100, 2)
            ])

    print("\n3. VALIDACAO FINAL")
    print("Acidentes preservados:", total)
    print("Combinacoes estacao/fonte:", len(linhas))

    assert len(linhas) == 90, (
        "Esperadas 30 estacoes x 3 fontes."
    )

    print("\nArquivo gerado:", SAIDA)
    print("\nAUDITORIA CONCLUIDA.")
    print("Nenhuma tabela foi modificada.")

finally:
    con.close()

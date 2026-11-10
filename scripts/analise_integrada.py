
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"
SAIDA = BASE / "resultados" / "analise_integrada.csv"

ESPERADO = 7728394

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

SAIDA.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — ANALISE INTEGRADA ===")

try:
    # Mantemos o ano civil e o ano de inicio
    # da estacao, sem misturar suas definicoes.
    consulta = """
        SELECT
            d.Ano AS Ano,
            d.Season_Year AS Ano_Estacao,
            d.Season AS Estacao,
            l.State AS Estado,
            c.Weather_Condition AS Condicao_Climatica,
            fo.Source AS Fonte,
            sv.Severity AS Severidade,
            SUM(f.Accident_Count) AS Total_Acidentes

        FROM FatoAcidente f

        JOIN DimData d
            ON f.DataKey = d.DataKey

        JOIN DimLocalizacao l
            ON f.LocalizacaoKey = l.LocalizacaoKey

        JOIN DimCondicaoClimatica c
            ON f.ClimaKey = c.ClimaKey

        JOIN DimFonte fo
            ON f.FonteKey = fo.FonteKey

        JOIN DimSeveridade sv
            ON f.SeveridadeKey = sv.SeveridadeKey

        GROUP BY
            d.Ano,
            d.Season_Year,
            d.Season,
            l.State,
            c.Weather_Condition,
            fo.Source,
            sv.Severity
    """

    total, combinacoes = con.execute(f"""
        SELECT
            SUM(Total_Acidentes),
            COUNT(*)
        FROM ({consulta}) t
    """).fetchone()

    print("\n1. VALIDACAO")
    print("Acidentes contabilizados:", total)
    print("Combinacoes analiticas:", combinacoes)

    assert total == ESPERADO, (
        "A analise nao preservou todos os acidentes."
    )

    # Exemplo exploratorio: maiores volumes de
    # severidade 4, separados por fonte.
    # Nao e um ranking de risco.
    print("\n2. TOP 15 COMBINACOES — SEVERIDADE 4")
    print("-" * 85)

    ranking = con.execute(f"""
        SELECT
            Estado,
            Estacao,
            Condicao_Climatica,
            Fonte,
            SUM(Total_Acidentes) AS Total_Sev4

        FROM ({consulta}) t

        WHERE Severidade = 4

        GROUP BY
            Estado,
            Estacao,
            Condicao_Climatica,
            Fonte

        ORDER BY Total_Sev4 DESC
        LIMIT 15
    """).fetchall()

    for estado, estacao, clima, fonte, quantidade in ranking:
        print(
            f"{estado} | {estacao} | "
            f"{clima or 'Nao informado'} | "
            f"{fonte} | {quantidade:,}"
        )

    # Exportamos todas as combinacoes.
    # O banco permanece inalterado.
    caminho = SAIDA.as_posix().replace("'", "''")

    con.execute(f"""
        COPY (
            SELECT *
            FROM ({consulta}) t
            ORDER BY
                Ano,
                Ano_Estacao,
                Estacao,
                Estado,
                Fonte,
                Severidade
        )
        TO '{caminho}'
        (HEADER, DELIMITER ',')
    """)

    print("\n3. EXPORTACAO")
    print("Arquivo:", SAIDA)
    print("Tamanho (MB):", round(
        SAIDA.stat().st_size / (1024 * 1024), 2
    ))

    print("\nANALISE INTEGRADA CONCLUIDA.")
    print("Nenhuma tabela do banco foi modificada.")

finally:
    con.close()

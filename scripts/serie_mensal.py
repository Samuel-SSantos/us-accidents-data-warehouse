
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"
SAIDA = BASE / "resultados" / "serie_mensal.csv"

ESPERADO = 7728394

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

SAIDA.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — SERIE MENSAL ===")

try:
    # Criamos uma grade de todos os meses,
    # fontes e niveis de severidade.
    # Assim, combinacoes sem acidentes
    # aparecem com contagem zero.
    consulta = """
        WITH calendario AS (
            SELECT
                CAST(DataKey / 100 AS INTEGER) AS Mes_Chave,
                COUNT(*) AS Dias_Calendario
            FROM DimData
            GROUP BY 1
        ),

        diarios AS (
            SELECT
                CAST(f.DataKey / 100 AS INTEGER) AS Mes_Chave,
                f.DataKey,
                f.FonteKey,
                f.SeveridadeKey,
                SUM(f.Accident_Count) AS Acidentes
            FROM FatoAcidente f
            GROUP BY 1, 2, 3, 4
        ),

        mensais AS (
            SELECT
                Mes_Chave,
                FonteKey,
                SeveridadeKey,
                SUM(Acidentes) AS Total_Acidentes
            FROM diarios
            GROUP BY 1, 2, 3
        ),

        dias_fonte AS (
            SELECT
                Mes_Chave,
                FonteKey,
                COUNT(DISTINCT DataKey) AS Dias_Com_Registros
            FROM diarios
            GROUP BY 1, 2
        )

        SELECT
            c.Mes_Chave,
            fo.Source AS Fonte,
            sv.Severity AS Severidade,
            c.Dias_Calendario,
            COALESCE(df.Dias_Com_Registros, 0)
                AS Dias_Com_Registros,
            COALESCE(m.Total_Acidentes, 0)
                AS Total_Acidentes

        FROM calendario c
        CROSS JOIN DimFonte fo
        CROSS JOIN DimSeveridade sv

        LEFT JOIN mensais m
            ON c.Mes_Chave = m.Mes_Chave
           AND fo.FonteKey = m.FonteKey
           AND sv.SeveridadeKey = m.SeveridadeKey

        LEFT JOIN dias_fonte df
            ON c.Mes_Chave = df.Mes_Chave
           AND fo.FonteKey = df.FonteKey

        ORDER BY
            c.Mes_Chave,
            fo.Source,
            sv.Severity
    """

    # Corrigimos a chave YYYYMM usando
    # divisao inteira para evitar arredondamento.
    consulta = consulta.replace(
        "CAST(DataKey / 100 AS INTEGER)",
        "DataKey // 100"
    ).replace(
        "CAST(f.DataKey / 100 AS INTEGER)",
        "f.DataKey // 100"
    )

    total, linhas, meses = con.execute(f"""
        SELECT
            SUM(Total_Acidentes),
            COUNT(*),
            COUNT(DISTINCT Mes_Chave)
        FROM ({consulta}) t
    """).fetchone()

    print("Acidentes preservados:", total)
    print("Meses:", meses)
    print("Linhas:", linhas)

    assert total == ESPERADO
    assert meses == 87
    assert linhas == meses * 3 * 4

    caminho = SAIDA.as_posix().replace("'", "''")

    con.execute(f"""
        COPY ({consulta})
        TO '{caminho}'
        (HEADER, DELIMITER ',')
    """)

    print("\nArquivo gerado:", SAIDA)
    print("SERIE MENSAL CONCLUIDA.")
    print("Nenhuma tabela modificada.")

finally:
    con.close()

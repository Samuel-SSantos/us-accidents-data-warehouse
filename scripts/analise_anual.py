
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"
SAIDA = BASE / "resultados" / "acidentes_por_ano.csv"

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

SAIDA.parent.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — ANALISE ANUAL ===")

try:
    # A dimensão de data fornece o ano.
    # A dimensão de severidade fornece o nível.
    # A tabela fato fornece a contagem.

    consulta = """
        SELECT
            d.Ano AS Ano,
            sv.Severity AS Severidade,
            SUM(f.Accident_Count) AS Total_Acidentes

        FROM FatoAcidente f

        JOIN DimData d
            ON f.DataKey = d.DataKey

        JOIN DimSeveridade sv
            ON f.SeveridadeKey = sv.SeveridadeKey

        GROUP BY
            d.Ano,
            sv.Severity

        ORDER BY
            d.Ano,
            sv.Severity
    """

    # Verifica o nome da coluna de ano
    # antes de executar a consulta principal.
    colunas_data = [
        linha[1]
        for linha in con.execute(
            "PRAGMA table_info('DimData')"
        ).fetchall()
    ]

    if "Ano" not in colunas_data:
        print("Colunas disponíveis em DimData:")
        print(colunas_data)
        raise ValueError(
            "A coluna Ano não foi encontrada. "
            "Confirme o nome antes de continuar."
        )

    resultado = con.execute(consulta).fetchall()

    print("\nAno | Severidade | Total de acidentes")
    print("-" * 45)

    for ano, severidade, total in resultado:
        print(f"{ano} | {severidade} | {total}")

    total_geral = sum(linha[2] for linha in resultado)

    print("\nTotal geral:", total_geral)

    assert total_geral == 7728394, (
        "A consulta não preservou o total de acidentes."
    )

    # Exporta o resultado para uso posterior
    # no Power BI, sem alterar o banco.
    con.execute(
        f"COPY ({consulta}) TO '{SAIDA.as_posix()}' "
        "(HEADER, DELIMITER ',')"
    )

    print("\nArquivo gerado:")
    print(SAIDA)
    print("\nANALISE ANUAL CONCLUIDA.")

finally:
    con.close()

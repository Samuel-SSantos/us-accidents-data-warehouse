
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

ESPERADO = 7728394

DIMENSOES = {
    "DimData": "DataKey",
    "DimHora": "HoraKey",
    "DimLocalizacao": "LocalizacaoKey",
    "DimCondicaoClimatica": "ClimaKey",
    "DimLuminosidade": "LuminosidadeKey",
    "DimSeveridade": "SeveridadeKey",
    "DimVia": "ViaKey",
    "DimFonte": "FonteKey",
}

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

# Somente leitura: este script não modifica o banco.
con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — VALIDACAO DAS 8 DIMENSOES ===")

try:
    total_staging, ids_unicos = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT Accident_ID)
        FROM StagingAcidentes
    """).fetchone()

    print("\nSTAGING")
    print("Total de acidentes:", total_staging)
    print("IDs únicos:", ids_unicos)

    assert total_staging == ESPERADO
    assert ids_unicos == ESPERADO

    print("\nDIMENSOES")

    for tabela, chave in DIMENSOES.items():
        total, unicas, nulas = con.execute(f"""
            SELECT
                COUNT(*),
                COUNT(DISTINCT "{chave}"),
                COUNT(*) FILTER (
                    WHERE "{chave}" IS NULL
                )
            FROM "{tabela}"
        """).fetchone()

        print(
            f"{tabela}: "
            f"{total} registros | "
            f"{unicas} chaves únicas | "
            f"{nulas} chaves nulas"
        )

        assert total > 0
        assert unicas == total, (
            f"Chaves duplicadas em {tabela}"
        )
        assert nulas == 0, (
            f"Chaves nulas em {tabela}"
        )

    print("\nRESULTADO")
    print("8 dimensões verificadas.")
    print("Todas as chaves primárias são únicas.")
    print("Nenhuma chave primária é nula.")
    print("STAGING preservada.")
    print("\nVALIDACAO CONCLUIDA COM SUCESSO.")

finally:
    con.close()

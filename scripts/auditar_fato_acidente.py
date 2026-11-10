
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1]
BANCO = BASE / "dados" / "tratado" / "us_accidents.duckdb"

ESPERADO = 7728394

DIMENSOES = {
    "DataKey": ("DimData", "DataKey"),
    "HoraKey": ("DimHora", "HoraKey"),
    "LocalizacaoKey": (
        "DimLocalizacao", "LocalizacaoKey"
    ),
    "ClimaKey": (
        "DimCondicaoClimatica", "ClimaKey"
    ),
    "LuminosidadeKey": (
        "DimLuminosidade", "LuminosidadeKey"
    ),
    "SeveridadeKey": (
        "DimSeveridade", "SeveridadeKey"
    ),
    "ViaKey": ("DimVia", "ViaKey"),
    "FonteKey": ("DimFonte", "FonteKey")
}

MEDIDAS = [
    "Duration_Minutes",
    "Distance_km",
    "Temperature_C",
    "Wind_Chill_C",
    "Humidity_Pct",
    "Pressure_hPa",
    "Visibility_km",
    "Wind_Speed_kmh",
    "Precipitation_mm",
    "Duration_Suspect",
    "Temperature_Suspect"
]

if not BANCO.exists():
    raise FileNotFoundError(BANCO)

con = duckdb.connect(str(BANCO), read_only=True)

print("=== MARCO 3 — AUDITORIA FATOACIDENTE ===")

try:
    print("\n1. Verificando quantidade e unicidade...")

    total, unicos, nulos, soma = con.execute("""
        SELECT
            COUNT(*),
            COUNT(DISTINCT Accident_ID),
            COUNT(*) FILTER (
                WHERE Accident_ID IS NULL
            ),
            SUM(Accident_Count)
        FROM FatoAcidente
    """).fetchone()

    print("Registros:", total)
    print("IDs únicos:", unicos)
    print("IDs nulos:", nulos)
    print("Soma Accident_Count:", soma)

    assert total == ESPERADO
    assert unicos == ESPERADO
    assert nulos == 0
    assert soma == ESPERADO

    print("\n2. Verificando integridade referencial...")

    for chave, (tabela, chave_dim) in DIMENSOES.items():
        faltantes = con.execute(f"""
            SELECT COUNT(*)
            FROM FatoAcidente f
            LEFT JOIN "{tabela}" d
                ON f."{chave}" = d."{chave_dim}"
            WHERE d."{chave_dim}" IS NULL
        """).fetchone()[0]

        print(f"{tabela}: {faltantes} referências inválidas")

        assert faltantes == 0, (
            f"Falha de integridade em {tabela}"
        )

    print("\n3. Comparando medidas com STAGING...")

    comparacoes = ",\n".join(
        f"""
        COUNT(*) FILTER (
            WHERE NOT (
                f."{campo}"
                IS NOT DISTINCT FROM s."{campo}"
            )
        ) AS "{campo}"
        """
        for campo in MEDIDAS
    )

    resultado = con.execute(f"""
        SELECT
            COUNT(*) AS total_associado,
            COUNT(*) FILTER (
                WHERE s.Accident_ID IS NULL
            ) AS sem_staging,
            {comparacoes}

        FROM FatoAcidente f

        LEFT JOIN StagingAcidentes s
            ON f.Accident_ID = s.Accident_ID
    """).fetchone()

    print("Linhas após associação:", resultado[0])
    print("Acidentes sem STAGING:", resultado[1])

    assert resultado[0] == ESPERADO
    assert resultado[1] == 0

    for campo, divergencias in zip(
        MEDIDAS, resultado[2:]
    ):
        print(f"{campo}: {divergencias} divergências")

        assert divergencias == 0, (
            f"Medida divergente: {campo}"
        )

    print("\n4. Conferindo preservação dos IDs...")

    ausentes = con.execute("""
        SELECT COUNT(*)
        FROM StagingAcidentes s
        LEFT JOIN FatoAcidente f
            ON s.Accident_ID = f.Accident_ID
        WHERE f.Accident_ID IS NULL
    """).fetchone()[0]

    print("IDs da STAGING ausentes na Fato:", ausentes)

    assert ausentes == 0

    print("\n====================================")
    print("AUDITORIA CONCLUÍDA COM SUCESSO")
    print("Integridade referencial aprovada.")
    print("Medidas preservadas.")
    print("Nenhum acidente perdido.")
    print("Nenhuma tabela foi modificada.")
    print("====================================")

finally:
    con.close()
